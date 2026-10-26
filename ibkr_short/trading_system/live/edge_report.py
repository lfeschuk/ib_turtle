"""End-of-day report: live results against the backtest and against the expected edge.

Every signal the bot acts on gets a backtest twin: the same short entered at the official close with the
backtest's fills and costs, then managed by the backtest's stop, target and day-3 rules on real daily bars.

  actual    what the account made on the shorts (real fills, commissions, estimated borrow)
  backtest  what the backtest would have made on the same shorts
  expected  what the edge model expects on average for those shorts

Actual minus backtest is the cost of execution (fills, slippage, fees, borrow). Backtest minus expected is market
luck, or a fading edge when it keeps drifting down. One day says little; the edge check needs many trades.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ..models import BarSnapshot, EngineConfig, OpenPosition
from ..strategy_core import compute_entry_and_brackets, evaluate_position_bar_exit

UNIFORM_SD = math.sqrt(1.0 / 12.0)   # spread of one trade's rank when the backtest is right
SIGMA_FALLBACK = 0.30
MIN_EDGE_TRADES = 10
MIN_EXEC_TRADES = 3
FADE_ALARM = 3.0                      # about 20:1 evidence for "no edge" over "edge as backtested" in recent trades
EXEC_OK = -0.005                      # fills may cost up to 0.5% per trade more than the backtest assumes
EXEC_BAD = -0.015                     # beyond 1.5% per trade, execution eats most of the edge
VIRTUAL_KINDS = ("taken", "shadow")   # rows that make up the book compared with the backtest


def _finite(x) -> bool:
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


# ------------------------------------------------------------------------------------------- twin mechanics
def model_entry(close: float, high: float, cfg: EngineConfig) -> dict:
    """The backtest's entry: sell at the official close less slippage, stop and target from the close and high."""
    entry, stop, target = compute_entry_and_brackets(close, high, cfg)
    return {"m_close": close, "m_entry": entry, "m_stop": stop, "m_target": target, "m_mark": close, "m_borrow": 0.0}


def model_step(row: dict, day: str, bar, k: int, nights: int, cfg: EngineConfig) -> dict:
    """One day of the backtest's position management: borrow for the nights held, then stop, target or day-3 exit."""
    shares = row["shares"]
    upd = {"m_borrow": (row["m_borrow"] or 0.0) + nights * shares * row["m_mark"] * cfg.borrow_annual / 252.0,
           "m_last_day": day}
    pos = OpenPosition(ticker=row["symbol"], ticker_idx=0, entry_date=pd.Timestamp(row["day"]), entry_day_idx=0,
                       setups="", notional_0=shares * row["m_entry"], equity_at_entry=1.0,
                       entry_fill_price=row["m_entry"], raw_mark_price=row["m_mark"], stop_price=row["m_stop"],
                       target_price=row["m_target"], locate_fee_paid=0.0, borrow_rate_annual=cfg.borrow_annual)
    snap = BarSnapshot(date=pd.Timestamp(day), day_idx=k, ticker=row["symbol"], ticker_idx=0, open=bar.open,
                       high=bar.high, low=bar.low, close=bar.close, volume=0.0, raw_close=bar.close, dollar_vol=0.0)
    fill, reason = evaluate_position_bar_exit(pos, snap, cfg)
    if fill is not None:
        upd.update(m_exit=fill, m_exit_day=day, m_reason=reason, status="closed")
    else:
        upd["m_mark"] = bar.close
    return upd


def notional(row: dict) -> float:
    return (row["shares"] or 0.0) * (row["m_entry"] or 0.0)


def model_pnl(row: dict) -> float:
    """Backtest P&L of the twin: realized after the exit, marked to the last close before it."""
    shares, entry = row["shares"] or 0.0, row["m_entry"] or 0.0
    last = row["m_exit"] if row["status"] == "closed" else row["m_mark"]
    return shares * (entry - (last if _finite(last) else entry)) - (row["m_borrow"] or 0.0)


def model_ret(row: dict) -> float:
    n = notional(row)
    return model_pnl(row) / n if n > 0 else math.nan


def actual_pnl(row: dict, trade: dict, commission: float) -> float:
    """Account P&L of a taken short: realized on the shares bought back, marked to the close on the rest."""
    realized = trade["pnl"] or 0.0
    open_shares = (trade["shares"] or 0.0) - (trade["exit_shares"] or 0.0)
    mark = row["a_mark"] if _finite(row["a_mark"]) else trade["entry_price"]
    unrealized = open_shares * (trade["entry_price"] - mark) if trade["status"] == "open" else 0.0
    return realized + unrealized - commission - (row["a_borrow"] or 0.0)


def accrued_fraction(row: dict, days_held: int, hold_days: int) -> float:
    """Share of a trade's expected edge counted so far: all of it once closed, spread over the holding days before."""
    if row["status"] == "closed":
        return 1.0
    return min(1.0, max(0.0, days_held / max(hold_days, 1)))


# ------------------------------------------------------------------------------------------- daily snapshot
def snapshot(rows: list[dict], trades: dict[int, dict], commissions: dict[int, float], days_held, hold_days: int,
             sigma: float) -> dict:
    """Cumulative dollars since the start: actual, backtest, expected (with its variance) and missed signals."""
    actual = theory = expected = var = missed = 0.0
    any_taken = False
    n_open = n_closed = 0
    for r in rows:
        if r["status"] not in ("open", "closed") or not _finite(r["m_entry"]):
            continue
        if r["kind"] == "missed":
            missed += model_pnl(r)
            continue
        if r["kind"] not in VIRTUAL_KINDS:
            continue
        theory += model_pnl(r)
        n = notional(r)
        f = accrued_fraction(r, days_held(r["day"]), hold_days)
        if _finite(r["exp_ret"]):
            expected += r["exp_ret"] * n * f
        var += (sigma * n) ** 2 * f
        n_closed += r["status"] == "closed"
        n_open += r["status"] == "open"
        if r["kind"] == "taken" and r["trade_id"] in trades:
            any_taken = True
            actual += actual_pnl(r, trades[r["trade_id"]], commissions.get(r["trade_id"], 0.0))
    return {"actual": actual if any_taken else None, "theory": theory, "expected": expected, "var": var,
            "missed": missed, "n_open": n_open, "n_closed": n_closed}


# ------------------------------------------------------------------------------------------- statistics
def edge_stats(rows: list[dict], model, last: dict | None = None) -> dict:
    """Do live outcomes still look like the backtest? Uses every closed twin (taken, shadow and missed signals).

    Each trade is ranked against the backtest's outcomes for its score (0.5 = typical). Ranks are robust to the
    rare -100% gap-throughs that swamp plain averages. A running test (Page's CUSUM) weighs recent trades as
    evidence for "no edge" against "edge as backtested" and raises the alarm near 20:1, which keeps false
    alarms to about one in several years of trading while catching a vanished edge within a few months.
    The dollar result (`last`, the latest daily snapshot) is checked against its normal range as well, because
    a short strategy can also lose its edge through more frequent large losses.
    """
    closed = [r for r in rows if r["status"] == "closed" and r["kind"] in ("taken", "shadow", "missed")
              and _finite(r["m_entry"]) and _finite(r["exp_ret"])]
    closed.sort(key=lambda r: (r["m_exit_day"] or "", r["id"]))
    n = len(closed)
    sigma = model.sigma if model is not None else SIGMA_FALLBACK
    out: dict = {"n": n, "verdict": "early"}
    mus = np.array([r["exp_ret"] for r in closed], dtype=float)
    mean_mu = float(mus.mean()) if n else (model.expected(1.5) if model is not None else math.nan)
    if model is not None and _finite(mean_mu) and mean_mu > 0:
        d = model.rank_drop_without_edge(mean_mu) / UNIFORM_SD
        out["needed"] = int(math.ceil(FADE_ALARM / (d * d / 2))) if d > 0 else None
    if n == 0:
        out["text"] = "No closed trades yet."
        return out
    rets = np.array([model_ret(r) for r in closed], dtype=float)
    sd = float(rets.std(ddof=1)) if n >= 20 else sigma
    out.update(live_mean=float(rets.mean()), expected_mean=mean_mu,
               ci=[float(rets.mean() - 1.96 * sd / math.sqrt(n)), float(rets.mean() + 1.96 * sd / math.sqrt(n))],
               z_mean=float((rets - mus).sum() / (sigma * math.sqrt(n))))
    z = out["z_mean"]
    fade = evidence = 0.0
    if model is not None:
        ranks = np.array([model.rank(r["score"], ret) for r, ret in zip(closed, rets)], dtype=float)
        half = 2 * UNIFORM_SD / math.sqrt(n)
        z = float((ranks.mean() - 0.5) / (UNIFORM_SD / math.sqrt(n)))
        out.update(rank=float(ranks.mean()), rank_lo=0.5 - half, rank_hi=0.5 + half, z_rank=z)
        s = (ranks - 0.5) / UNIFORM_SD
        deltas = np.array([model.rank_drop_without_edge(mu) / UNIFORM_SD if mu > 0 else 0.0 for mu in mus])
        llr = deltas * s + deltas ** 2 / 2  # log evidence for "edge as backtested" over "no edge", per trade
        for x in llr:
            fade = max(0.0, fade - x)
        evidence = float(llr.sum())
        out.update(fade=fade, evidence=evidence)
    dollar_z = None
    if last is not None and last.get("var", 0) > 0:
        dollar_z = (last["theory"] - last["expected"]) / math.sqrt(last["var"])
        out["dollar_z"] = dollar_z
    below_band = dollar_z is not None and dollar_z < -2.0
    ranks_low = z < -1.0 or fade >= FADE_ALARM / 2
    if n < MIN_EDGE_TRADES:
        out["text"] = f"Too early to judge after {n} trades."
    elif fade >= FADE_ALARM:
        out["verdict"], out["text"] = "bad", ("Recent trades look more like no edge than like the backtest. "
                                              "Consider pausing: signals are still tracked while paused, and this "
                                              "clears once results recover.")
    elif ranks_low and below_band:
        out["verdict"], out["text"] = "watch", ("Below the backtest, in dollars beyond the normal range. Not yet "
                                                "enough evidence that the edge is gone.")
    elif ranks_low:
        out["verdict"], out["text"] = "watch", "Below the backtest, but still within what bad luck can explain."
    elif below_band:
        out["verdict"], out["text"] = "watch", ("Dollars are below the normal range because of a few large losses; "
                                                "the typical trade is still in line with the backtest.")
    else:
        out["verdict"], out["text"] = "ok", "On track: trades land where the backtest says they should."
    if n >= MIN_EDGE_TRADES and evidence >= FADE_ALARM:
        out["text"] += " Live results alone now confirm an edge."
    return out


def execution_rows(rows: list[dict], trades: dict[int, dict], commissions: dict[int, float]) -> list[dict]:
    """Per finished trade: actual minus backtest, split into entry, exit, borrow and fees (fractions of the position)."""
    out = []
    for r in rows:
        t = trades.get(r["trade_id"]) if r["kind"] == "taken" else None
        if t is None or t["status"] != "closed" or r["status"] != "closed" or not _finite(r["m_entry"]):
            continue
        n = notional(r)
        if n <= 0:
            continue
        comm = commissions.get(r["trade_id"], 0.0)
        shares = r["shares"]
        a, m = actual_pnl(r, t, comm), model_pnl(r)
        out.append({"symbol": r["symbol"], "day": r["day"], "exit_day": t["exit_date"],
                    "gap": (a - m) / n, "gap_usd": a - m, "actual_ret": a / (t["shares"] * t["entry_price"]),
                    "backtest_ret": m / n,
                    "entry": shares * (t["entry_price"] - r["m_entry"]) / n,
                    "exit": shares * (r["m_exit"] - t["exit_price"]) / n,
                    "borrow": ((r["m_borrow"] or 0.0) - (r["a_borrow"] or 0.0)) / n, "fees": -comm / n})
    return out


def execution_stats(rows: list[dict], trades: dict[int, dict], commissions: dict[int, float]) -> dict:
    ex = execution_rows(rows, trades, commissions)
    n = len(ex)
    out: dict = {"n": n, "verdict": "early"}
    if n == 0:
        out["text"] = "Shows up once real shorts have closed."
        return out
    for key in ("gap", "entry", "exit", "borrow", "fees", "actual_ret", "backtest_ret"):
        out[key] = float(np.mean([e[key] for e in ex]))
    out["gap_usd"] = float(sum(e["gap_usd"] for e in ex))
    g = out["gap"]
    if n < MIN_EXEC_TRADES:
        out["text"] = f"Too early to judge after {n} trades."
    elif g >= EXEC_OK:
        out["verdict"] = "ok"
        out["text"] = ("Fills are better than the backtest assumes." if g >= 0.002 else
                       "Fills are about as good as the backtest assumes.")
    elif g >= EXEC_BAD:
        out["verdict"] = "watch"
        out["text"] = f"Fills cost {-g:.1%} per trade more than the backtest assumes."
    else:
        out["verdict"] = "bad"
        out["text"] = (f"Fills cost {-g:.1%} per trade more than the backtest assumes, most of the edge. "
                       "Check order types, timing and borrow.")
    return out


def missed_stats(rows: list[dict]) -> dict:
    missed = [r for r in rows if r["kind"] == "missed"]
    reasons: dict[str, int] = {}
    for r in missed:
        key = (r["note"] or "other").split(" (")[0]
        reasons[key] = reasons.get(key, 0) + 1
    priced = [r for r in missed if r["status"] in ("open", "closed") and _finite(r["m_entry"])]
    closed = [r for r in priced if r["status"] == "closed"]
    return {"n": len(missed), "reasons": reasons, "theory_usd": float(sum(model_pnl(r) for r in priced)),
            "closed": len(closed),
            "mean_ret": float(np.mean([model_ret(r) for r in closed])) if closed else None}


# ------------------------------------------------------------------------------------------- report for the app
def day_events(rows: list[dict], trades: dict[int, dict], commissions: dict[int, float], day: str) -> list[dict]:
    events = []
    for r in rows:
        t = trades.get(r["trade_id"]) if r["kind"] == "taken" else None
        base = {"symbol": r["symbol"], "setups": r["setups"] or "", "exp_ret": r["exp_ret"]}
        if r["day"] == day:
            if r["kind"] == "missed":
                events.append({**base, "type": "missed", "note": r["note"] or ""})
            elif r["kind"] in VIRTUAL_KINDS:
                e = {**base, "type": "new", "virtual": r["kind"] == "shadow", "shares": r["shares"],
                     "close": r["m_close"]}
                if t is not None:
                    e["fill"] = t["entry_price"]
                    if _finite(r["m_close"]) and r["m_close"] > 0:
                        e["vs_close"] = t["entry_price"] / r["m_close"] - 1.0
                events.append(e)
        if t is not None and t["status"] == "closed" and t["exit_date"] == day:
            comm = commissions.get(r["trade_id"], 0.0)
            e = {**base, "type": "exit", "virtual": False, "reason": t["exit_reason"], "fill": t["exit_price"],
                 "pnl": actual_pnl(r, t, comm), "model_open": r["status"] != "closed"}
            if r["status"] == "closed":
                e.update(model_fill=r["m_exit"], model_reason=r["m_reason"], gap=actual_pnl(r, t, comm) - model_pnl(r))
            events.append(e)
        elif r["kind"] == "shadow" and r["status"] == "closed" and r["m_exit_day"] == day:
            events.append({**base, "type": "exit", "virtual": True, "reason": r["m_reason"], "fill": r["m_exit"],
                           "pnl": model_pnl(r), "ret": model_ret(r)})
        if t is not None and t["status"] == "open" and r["status"] == "closed" and r["m_exit_day"] == day:
            events.append({**base, "type": "diverged", "reason": r["m_reason"]})
    order = {"exit": 0, "diverged": 1, "new": 2, "missed": 3}
    events.sort(key=lambda e: order.get(e["type"], 9))
    return events


def trade_list(rows: list[dict], trades: dict[int, dict], commissions: dict[int, float], limit: int = 20) -> list[dict]:
    out = []
    for r in rows:
        if r["kind"] not in VIRTUAL_KINDS or r["status"] != "closed" or not _finite(r["m_entry"]):
            continue
        item = {"symbol": r["symbol"], "setups": r["setups"] or "", "day": r["day"], "exit_day": r["m_exit_day"],
                "backtest": model_ret(r), "backtest_reason": r["m_reason"], "expected": r["exp_ret"],
                "virtual": r["kind"] == "shadow"}
        t = trades.get(r["trade_id"]) if r["kind"] == "taken" else None
        if t is not None and t["status"] == "closed":
            n = notional(r)
            a = actual_pnl(r, t, commissions.get(r["trade_id"], 0.0))
            item.update(actual=a / (t["shares"] * t["entry_price"]) if t["shares"] and t["entry_price"] else None,
                        actual_reason=t["exit_reason"], gap=(a - model_pnl(r)) / n if n > 0 else None,
                        exit_day=t["exit_date"])
        out.append(item)
    out.sort(key=lambda x: (x["exit_day"] or "", x["day"]), reverse=True)
    return out[:limit]


def build_report(journal, model, mode: str) -> dict:
    series = journal.edge_series(400)
    out: dict = {"mode": mode, "day": series[-1]["day"] if series else None}
    rows = journal.twin_rows()
    trades = journal.trades_by_id()
    comm = journal.commissions_by_trade()
    out["edge"] = edge_stats(rows, model, series[-1] if series else None)
    out["execution"] = execution_stats(rows, trades, comm)
    out["missed"] = missed_stats(rows)
    out["trades"] = trade_list(rows, trades, comm)
    decided = [r for r in rows if r["kind"] in VIRTUAL_KINDS and r["close_ok"] is not None]
    out["timing"] = {"n": len(decided), "not_at_close": sum(1 for r in decided if r["close_ok"] == 0)}
    if not series:
        out.update(today=None, events=[], series=[], daily=[])
        return out
    last = series[-1]
    prev = series[-2] if len(series) > 1 else {"actual": 0.0, "theory": 0.0, "expected": 0.0, "missed": 0.0}

    def delta(cur: dict, before: dict, key: str) -> float | None:
        if cur[key] is None:
            return None
        return cur[key] - (before[key] or 0.0)

    today = {k: delta(last, prev, k) for k in ("actual", "theory", "expected", "missed")}
    today["gap"] = today["actual"] - today["theory"] if today["actual"] is not None else None
    out["today"] = today
    out["events"] = day_events(rows, trades, comm, last["day"])
    out["series"] = [{"day": s["day"], "actual": s["actual"], "theory": s["theory"], "expected": s["expected"],
                      "sd": math.sqrt(max(s["var"], 0.0))} for s in series]
    daily = []
    for before, cur in zip([{"actual": 0.0, "theory": 0.0, "expected": 0.0, "missed": 0.0}] + series[:-1], series):
        daily.append({"day": cur["day"], "actual": delta(cur, before, "actual"),
                      "theory": delta(cur, before, "theory"), "expected": delta(cur, before, "expected")})
    out["daily"] = daily[-20:]
    return out


def summary_line(journal, mode: str) -> str:
    """One line for the daily push message."""
    series = journal.edge_series(2)
    if not series:
        return ""
    last = series[-1]
    prev = series[-2] if len(series) > 1 else {"actual": 0.0, "theory": 0.0, "expected": 0.0}
    th = last["theory"] - (prev["theory"] or 0.0)
    ex = last["expected"] - (prev["expected"] or 0.0)
    if last["actual"] is None or mode == "shadow":
        return f"Shadow book today ${th:+,.0f} (expected ${ex:+,.0f})"
    ac = last["actual"] - (prev["actual"] or 0.0)
    return f"Shorts today ${ac:+,.0f} vs backtest ${th:+,.0f} (fills ${ac - th:+,.0f}), expected ${ex:+,.0f}"
