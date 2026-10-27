"""Research-only position sizing for the small-cap gap-short system: static fraction of equity
vs. walk-forward (causal) Kelly sizing.

Nothing here is used by `LiveIBKRTradingBot`; production sizing stays at `EngineConfig.pos_pct`
until a policy is explicitly adopted.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .engine import TradingEngine
from .models import EngineConfig, SignalCandidate


# ---------------------------------------------------------------------------
# Broker margin rules (regulatory floor; IBKR house rules can be stricter)
# ---------------------------------------------------------------------------
def short_maintenance_per_share(price: float) -> float:
    """FINRA 4210 maintenance requirement per short share: under $5 the greater of $2.50 or
    100% of the price, otherwise the greater of $5.00 or 30% of the price."""
    if not math.isfinite(price) or price <= 0.0:
        return float("inf")
    if price < 5.0:
        return max(2.50, price)
    return max(5.00, 0.30 * price)


def short_initial_per_share(price: float) -> float:
    """Reg T initial requirement for a new short (50% of value on top of the proceeds),
    never below the maintenance requirement."""
    return max(0.50 * price, short_maintenance_per_share(price))


# ---------------------------------------------------------------------------
# Kelly estimation
# ---------------------------------------------------------------------------
def kelly_fraction(x, f_cap: float = 5.0) -> float:
    """Growth-optimal fraction argmax_f sum(log(1 + f * x)) for a sample of per-$1 returns x.

    The objective is concave, so the root of its derivative is found by bisection. A worst loss
    of L in the sample keeps the answer below 1/L (a bigger bet would have wiped out the account).
    """
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x) & (x != 0.0)]
    if x.size == 0 or x.sum() <= 0.0:
        return 0.0
    x_min = float(x.min())
    hi = min(f_cap, (-1.0 / x_min) * (1.0 - 1e-9)) if x_min < 0.0 else f_cap
    lo = 0.0
    if np.sum(x / (1.0 + hi * x)) > 0.0:
        return hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if np.sum(x / (1.0 + mid * x)) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def classic_kelly_formula(r) -> float:
    """Trader's rule of thumb f = W - (1 - W) / R, with win rate W and payoff ratio
    R = average win / average loss."""
    r = np.asarray(r, dtype=np.float64)
    wins, losses = r[r > 0], r[r < 0]
    if wins.size == 0 or losses.size == 0:
        return 0.0
    w = wins.size / r.size
    payoff = wins.mean() / (-losses.mean())
    return max(0.0, w - (1.0 - w) / payoff)


# ---------------------------------------------------------------------------
# Per-trade daily P&L (per $1 of notional), rebuilt exactly as the engine books it
# ---------------------------------------------------------------------------
def position_day_rows(adapter, trades_df: pd.DataFrame) -> pd.DataFrame:
    """One row per (trade, day) with the day's P&L per $1 of notional.

    Columns: trade_id, day_idx, kind ('entry' on the entry day, 'held' afterwards), u,
    req (margin per $1 of notional at the start of that day: Reg T initial on the entry day,
    FINRA maintenance afterwards), dv (entry-day dollar volume), net_return_pct.
    Summing `u` over a trade reproduces its `net_return_pct`.
    """
    C = adapter.C
    rows: list[tuple] = []
    for tid, tr in enumerate(trades_df.itertuples(index=False)):
        j, t0, t1 = int(tr.ticker_idx), int(tr.entry_day_idx), int(tr.exit_day_idx)
        e, x = float(tr.entry_fill_price), float(tr.exit_fill_price)
        c0 = float(C[t0, j])
        dv = float(adapter.DV[t0, j])
        locate = float(tr.locate_fee_dollars) / float(tr.notional_0)
        borrow_total = float(tr.borrow_fee_dollars) / float(tr.notional_0)

        # Mark path at the start of each held day (the engine marks to the close, skipping halted days)
        prev_marks: list[float] = []
        marks_after: list[float] = []
        prev = c0
        for d in range(t0 + 1, t1 + 1):
            prev_marks.append(prev)
            if d == t1:
                m = x
            else:
                c = float(C[d, j])
                m = c if math.isfinite(c) else prev
            marks_after.append(m)
            prev = m
        # Borrow accrues on the start-of-day mark; infer the annual rate from the booked total
        mark_sum = sum(prev_marks) / e
        daily_rate = borrow_total / mark_sum if mark_sum > 0 else 0.0

        rows.append((tid, t0, "entry", -(locate + (c0 / e - 1.0)), short_initial_per_share(c0) / e, dv,
                     float(tr.net_return_pct)))
        for k, d in enumerate(range(t0 + 1, t1 + 1)):
            pm, m = prev_marks[k], marks_after[k]
            u = (pm - m) / e - (pm / e) * daily_rate
            rows.append((tid, d, "held", u, short_maintenance_per_share(pm) / e, dv, float(tr.net_return_pct)))

    out = pd.DataFrame(rows, columns=["trade_id", "day_idx", "kind", "u", "req", "dv", "net_return_pct"])
    check = out.groupby("trade_id").agg(u=("u", "sum"), r=("net_return_pct", "first"))
    max_err = float((check["u"] - check["r"]).abs().max()) if len(check) else 0.0
    if max_err > 1e-9:
        raise AssertionError(f"daily P&L rebuild does not match trade returns (max err {max_err:.3e})")
    return out


def daily_unit_stream(rows: pd.DataFrame, t_lo: int, t_hi: int) -> np.ndarray:
    """Portfolio P&L per unit of per-position fraction for each day in [t_lo, t_hi)."""
    u = np.zeros(t_hi - t_lo, dtype=np.float64)
    sub = rows[(rows["day_idx"] >= t_lo) & (rows["day_idx"] < t_hi)]
    np.add.at(u, sub["day_idx"].to_numpy() - t_lo, sub["u"].to_numpy())
    return u


def walk_forward_kelly(
    T: int,
    t_lo: int,
    t_hi: int,
    seed_trade_returns: np.ndarray,
    seed_daily_u: np.ndarray,
    trades_df: pd.DataFrame,
    daily_u: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Causal Kelly estimates for every day t in [t_lo, t_hi), using only data known before t.

    Returns (f_trade, f_portfolio), each of length T (NaN outside the window):
      - f_trade: per-trade Kelly on all trades closed before t (seed trades + earlier OOS trades).
      - f_portfolio: Kelly on the daily unit-return stream before t, which accounts for concurrent
        positions, their correlation and gap risk.
    """
    f_trade = np.full(T, np.nan)
    f_port = np.full(T, np.nan)
    seed_r = np.asarray(seed_trade_returns, dtype=np.float64)
    seed_u = np.asarray(seed_daily_u, dtype=np.float64)
    seed_u = seed_u[seed_u != 0.0]

    exits = trades_df[["exit_day_idx", "net_return_pct"]].sort_values("exit_day_idx").to_numpy()
    k_exit = 0
    closed: list[float] = []
    last_trade_f = kelly_fraction(seed_r)
    last_port_f = kelly_fraction(seed_u)
    nz_u: list[float] = []

    for t in range(t_lo, t_hi):
        changed_trade = False
        while k_exit < len(exits) and exits[k_exit, 0] < t:
            closed.append(float(exits[k_exit, 1]))
            k_exit += 1
            changed_trade = True
        if changed_trade:
            last_trade_f = kelly_fraction(np.concatenate([seed_r, np.asarray(closed)]))
        if t > t_lo and daily_u[t - 1 - t_lo] != 0.0:
            nz_u.append(float(daily_u[t - 1 - t_lo]))
            last_port_f = kelly_fraction(np.concatenate([seed_u, np.asarray(nz_u)]))
        f_trade[t] = last_trade_f
        f_port[t] = last_port_f
    return f_trade, f_port


# ---------------------------------------------------------------------------
# Per-bet Kelly: each bet's own expected edge, the strategy's real risk shape
# ---------------------------------------------------------------------------
def fit_edge_model(scores: np.ndarray, returns: np.ndarray) -> tuple[float, float, np.ndarray]:
    """Least-squares line of trade return on the strategy's ranking score.

    Returns (intercept, slope, residuals). The residuals carry the risk shape of real trades,
    including overnight gaps through the stop.
    """
    s = np.asarray(scores, dtype=np.float64)
    r = np.asarray(returns, dtype=np.float64)
    x = np.column_stack([np.ones_like(s), s])
    coef, *_ = np.linalg.lstsq(x, r, rcond=None)
    return float(coef[0]), float(coef[1]), r - x @ coef


class PerBetKellyModel:
    """Walk-forward per-bet Kelly.

    A new bet with score s is treated as a draw of (a + b*s) + residual, where the line and the
    residuals come only from trades closed before the bet's entry day. Its Kelly fraction is the
    growth-optimal size for that distribution: zero when the expected edge is gone, largest for
    the best setups, and always small enough that the worst past loss could not wipe out the account.
    """

    def __init__(self, T: int, t_lo: int, t_hi: int, seed_scores: np.ndarray, seed_returns: np.ndarray,
                 trades_df: pd.DataFrame):
        self.version_of_day = np.full(T, -1, dtype=np.int64)
        self.models: list[tuple[float, float, np.ndarray]] = []
        self._cache: dict[tuple[int, float], float] = {}
        seed_s = np.asarray(seed_scores, dtype=np.float64)
        seed_r = np.asarray(seed_returns, dtype=np.float64)
        closed = trades_df[["exit_day_idx", "score", "net_return_pct"]].sort_values("exit_day_idx").to_numpy()
        k = 0
        n_used = -1
        for t in range(t_lo, t_hi):
            while k < len(closed) and closed[k, 0] < t:
                k += 1
            if k != n_used:
                s = np.concatenate([seed_s, closed[:k, 1]])
                r = np.concatenate([seed_r, closed[:k, 2]])
                self.models.append(fit_edge_model(s, r))
                n_used = k
            self.version_of_day[t] = len(self.models) - 1

    def expected_edge(self, day_idx: int, score: float) -> float:
        a, b, _ = self.models[self.version_of_day[day_idx]]
        return a + b * score

    def fraction(self, day_idx: int, score: float) -> float:
        v = int(self.version_of_day[day_idx])
        key = (v, round(float(score), 6))
        if key not in self._cache:
            a, b, resid = self.models[v]
            self._cache[key] = kelly_fraction(a + b * score + resid)
        return self._cache[key]


# ---------------------------------------------------------------------------
# Sizing policies and the engine that applies them
# ---------------------------------------------------------------------------
@dataclass
class SizingPolicy:
    """Fraction of current equity to put into each new short, plus optional broker caps."""
    name: str
    static_pct: float | None = None
    kelly_series: np.ndarray | None = None   # walk-forward Kelly estimate (or portfolio multiplier) by day_idx
    kelly_mult: float = 1.0                  # 1.0 = full Kelly, 0.5 = half Kelly, ...
    bet_model: PerBetKellyModel | None = None  # per-bet Kelly fraction from each bet's own score
    dd_limit: float | None = None            # drawdown control: scale bets by the cushion above (1 - dd_limit) x peak
    dd_reset_yearly: bool = False            # restart the drawdown peak at each new calendar year
    margin_cap: bool = False                 # keep total short margin within account equity
    liquidity_cap_pct: float | None = None   # max notional as a fraction of the entry day's dollar volume

    def target_fraction(self, day_idx: int, sig: SignalCandidate | None = None) -> float:
        if self.static_pct is not None:
            return self.static_pct
        assert self.kelly_series is not None
        level = float(self.kelly_series[day_idx])
        if not math.isfinite(level):
            return 0.0
        if self.bet_model is not None:
            assert sig is not None
            return self.kelly_mult * level * self.bet_model.fraction(day_idx, sig.score)
        return self.kelly_mult * level


class SizedTradingEngine(TradingEngine):
    """`TradingEngine` with a pluggable sizing policy and margin / exposure logging.

    A fully capped entry keeps its slot at negligible size, so every policy trades exactly the
    same list of signals and only the position sizes differ.
    """

    MIN_NOTIONAL_FRAC = 1e-6

    def __init__(self, cfg: EngineConfig, policy: SizingPolicy, stacked_core: bool = False):
        super().__init__(cfg, stacked_core=stacked_core)
        self.policy = policy
        self.entry_log: list[dict] = []
        self.daily_log: list[dict] = []
        self.peak_equity = self.current_equity()
        self._peak_year: int | None = None

    def margin_used(self) -> float:
        return sum(
            short_maintenance_per_share(p.raw_mark_price) * p.notional_0 / p.entry_fill_price
            for p in self.open_positions.values()
        )

    def tax_liability(self) -> float:
        """Tax owed so far this year; paying it in January is not a trading loss."""
        base = self.realized_ytd + self.loss_carryforward
        return self.cfg.tax_rate * base if base > 0 else 0.0

    def gross_short(self) -> float:
        return sum(p.notional_0 * p.raw_mark_price / p.entry_fill_price for p in self.open_positions.values())

    def position_notional(self, sig: SignalCandidate, day_idx: int, cur_eq: float) -> float:
        f_target = max(0.0, self.policy.target_fraction(day_idx, sig))
        if self.policy.dd_limit is not None:
            # Growth-optimal sizing under a max-drawdown limit: bet Kelly times the share of equity
            # still above the floor, so bets shrink to zero as the account nears the floor.
            # Equity is measured net of the tax owed, so the yearly tax payment is not a drawdown.
            adj = cur_eq - self.tax_liability()
            peak = max(self.peak_equity, adj)
            floor = (1.0 - self.policy.dd_limit) * peak
            f_target *= max(0.0, adj - floor) / cur_eq
        notional = f_target * cur_eq
        capped_by = "none"
        if self.policy.liquidity_cap_pct is not None and math.isfinite(sig.dollar_vol):
            cap = self.policy.liquidity_cap_pct * sig.dollar_vol
            if notional > cap:
                notional, capped_by = cap, "liquidity"
        if self.policy.margin_cap:
            entry_fill = sig.ref_close * (1.0 - self.cfg.slip_per_side)
            req_per_dollar = short_initial_per_share(sig.ref_close) / entry_fill
            room = max(0.0, cur_eq - self.margin_used())
            cap = room / req_per_dollar
            if notional > cap:
                notional, capped_by = cap, "margin"
        notional = max(notional, self.MIN_NOTIONAL_FRAC * cur_eq)
        self.entry_log.append(
            dict(
                day_idx=day_idx,
                ticker=sig.ticker,
                price=sig.ref_close,
                dollar_vol=sig.dollar_vol,
                equity=cur_eq,
                f_target=f_target,
                f_used=notional / cur_eq,
                notional=notional,
                capped_by=capped_by,
            )
        )
        return notional

    def on_market_day(self, *args, **kwargs):
        snap = super().on_market_day(*args, **kwargs)
        eq = snap.total_equity
        adj = eq - self.tax_liability()
        if self.policy.dd_reset_yearly and self._peak_year is not None and snap.date.year != self._peak_year:
            self.peak_equity = adj
        else:
            self.peak_equity = max(self.peak_equity, adj)
        self._peak_year = snap.date.year
        margin = self.margin_used()
        self.daily_log.append(
            dict(
                day_idx=snap.day_idx,
                equity=eq,
                n_open=len(self.open_positions),
                gross_short=self.gross_short() / eq if eq > 0 else float("nan"),
                margin_util=margin / eq if eq > 0 else (float("inf") if margin > 0 else 0.0),
            )
        )
        return snap
