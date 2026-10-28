"""Tests for the live service and phone app (run: python tests/test_live_app.py).

1. Demo mode (service + simulated broker) reproduces the backtest engine trade for trade on 2026 YTD.
2. End-of-day report: the backtest twin matches the account exactly in demo mode, shadow mode's virtual book makes
   exactly the backtest's trades, and worse fills show up as execution cost (entry, exit) of the right size.
3. API security: login, CSRF, sessions, rate limits, password checks, headers, methods.
4. Calendar, auth helpers, partial fills in the journal, and the edge check statistics.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_system.live import edge_report  # noqa: E402
from trading_system.live import market_calendar as mc  # noqa: E402
from trading_system.live.auth import (CSRF_COOKIE, SESSION_COOKIE, LoginLimiter, csrf_ok, hash_password,  # noqa: E402
                                      verify_password)
from trading_system.live.broker import AccountInfo, SimBroker  # noqa: E402
from trading_system.live.config import LiveConfig  # noqa: E402
from trading_system.live.journal import Journal  # noqa: E402
from trading_system.live.live_strategy import PerBetModel  # noqa: E402
from trading_system.live.notify import Notifier  # noqa: E402
from trading_system.live.service import PACKAGED_MODEL, BotService  # noqa: E402

PASSWORD = "correct horse battery staple"


def test_calendar() -> None:
    assert not mc.is_trading_day(date(2026, 7, 3))           # Independence Day observed
    assert not mc.is_trading_day(date(2026, 10, 24))         # Saturday
    assert mc.is_trading_day(date(2026, 10, 23))
    assert mc.close_time(date(2026, 11, 27)).hour == 13      # day after Thanksgiving
    assert mc.close_time(date(2026, 11, 30)).hour == 16
    assert mc.trading_days_between(date(2026, 10, 16), date(2026, 10, 21)) == 3
    print("calendar ok")


def test_auth_helpers() -> None:
    h = hash_password(PASSWORD)
    assert verify_password(PASSWORD, h) and not verify_password("wrong password!", h)
    assert not verify_password(PASSWORD, "garbage")
    assert csrf_ok("abc", "abc") and not csrf_ok("abc", "abd") and not csrf_ok(None, "abc") and not csrf_ok("abc", "")
    lim = LoginLimiter(max_failures=3, window_s=60)
    for _ in range(3):
        assert not lim.blocked()
        lim.failure()
    assert lim.blocked()
    lim.success()
    assert not lim.blocked()
    print("auth helpers ok")


def test_journal_partial_fills() -> None:
    with tempfile.TemporaryDirectory() as d:
        j = Journal(Path(d) / "j.db")
        tid, total, new = j.record_entry_fill("ABC", "2026-10-20", 4.00, 300, {"notional": 2000.0})
        tid2, total, new2 = j.record_entry_fill("ABC", "2026-10-20", 4.10, 200, {})
        assert tid == tid2 and new and not new2 and total == 500
        t = j.open_trades()[0]
        assert abs(t["entry_price"] - 4.04) < 1e-9                     # VWAP of the two sells
        r = j.record_exit_fill("ABC", "2026-10-23", 3.00, 200, "time exit")
        assert r and not r["closed"] and j.open_trades()
        r = j.record_exit_fill("ABC", "2026-10-23", 3.20, 300, "time exit")
        assert r["closed"] and not j.open_trades()
        t = j.recent_trades(1)[0]
        assert abs(t["exit_price"] - 3.12) < 1e-9 and abs(t["pnl"] - (500 * 4.04 - 200 * 3.00 - 300 * 3.20)) < 1e-6
        assert t["exit_date"] == "2026-10-23" and j.last_exit_date("ABC") == "2026-10-23"
        assert j.record_exit_fill("ABC", "2026-10-23", 3.20, 10, "manual") is None   # nothing left to cover
    print("journal partial fills ok")


def _fake_rows(rets: np.ndarray, scores: np.ndarray, model: PerBetModel) -> list[dict]:
    """Closed shadow twins with the given net returns (1 share at $1, so P&L = return)."""
    return [{"id": i, "status": "closed", "kind": "shadow", "m_entry": 1.0, "m_exit": 1.0 - r, "m_mark": 1.0,
             "m_borrow": 0.0, "shares": 1.0, "score": float(s), "exp_ret": model.expected(s),
             "m_exit_day": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}"} for i, (r, s) in enumerate(zip(rets, scores))]


def test_edge_stats_synthetic() -> None:
    model = PerBetModel(PACKAGED_MODEL)
    rng = np.random.default_rng(7)
    scores = rng.choice([0.4, 0.8, 2.3, 2.9, 3.4], size=300)
    noise = rng.choice(model.residuals, size=300)
    on_track = edge_report.edge_stats(_fake_rows(np.array([model.expected(s) for s in scores]) + noise, scores, model),
                                      model)
    gone = edge_report.edge_stats(_fake_rows(noise, scores, model), model)              # same luck, zero edge
    worse = edge_report.edge_stats(_fake_rows(noise - 0.05, scores, model), model)
    assert on_track["verdict"] in ("ok", "watch") and abs(on_track["z_rank"]) < 3, on_track
    assert gone["verdict"] == "bad" and gone["fade"] >= edge_report.FADE_ALARM, gone
    assert worse["verdict"] == "bad" and worse["rank"] < gone["rank"] < on_track["rank"]
    assert edge_report.edge_stats(_fake_rows(noise[:5], scores[:5], model), model)["verdict"] == "early"
    print(f"edge stats ok: on track rank {on_track['rank']:.3f} ({on_track['verdict']}), "
          f"no edge rank {gone['rank']:.3f} ({gone['verdict']}), alarm after about {on_track['needed']} trades")


def test_perbet_sizing() -> None:
    """Plain per-bet Kelly: bet = kelly_mult x the setup's Kelly size, the same in a drawdown, then the hard caps."""
    from types import SimpleNamespace

    from trading_system.live.live_strategy import size_bet

    model = PerBetModel(PACKAGED_MODEL)
    cfg = LiveConfig()
    cfg.sizing.mode, cfg.sizing.model_path = "perbet", str(PACKAGED_MODEL)
    cfg.validate()
    acct = AccountInfo("U0", 100_000.0, 100_000.0, 0.0, float("inf"))

    def bet(score: float, dollar_vol: float = 1e9, peak_adj: float | None = None):
        sig = SimpleNamespace(score=score, dollar_vol=dollar_vol, ref_close=5.0)
        return size_bet(cfg, sig, 5.0, acct, peak_adj=peak_adj, realized_ytd=0.0, model=model)

    sizes = []
    for score in (0.5, 1.5, 3.4):
        d = bet(score)
        assert abs(d.fraction - model.fraction(score) / 6) < 1e-12 and d.capped_by == "none", (score, d)
        assert abs(bet(score, peak_adj=100_000 / 0.7).fraction - d.fraction) < 1e-12   # no brake: 30% down, same bet
        sizes.append(d.fraction)
    assert sizes[0] < sizes[1] < sizes[2]   # stronger setups get more
    cfg.sizing.kelly_mult = 1.0
    d = bet(3.4)
    assert d.capped_by == "max per short" and abs(d.fraction - cfg.sizing.max_position_pct) < 1e-12
    d = bet(1.5, dollar_vol=200_000)
    assert d.capped_by == "liquidity" and abs(d.notional - 2_000) < 1e-6
    for bad in ({"mode": "perbet", "model_path": ""}, {"mode": "perbet", "model_path": "m.json", "kelly_mult": 0.0},
                {"mode": "kelly"}):
        c = LiveConfig()
        for k, v in bad.items():
            setattr(c.sizing, k, v)
        try:
            c.validate()
        except ValueError:
            continue
        raise AssertionError(f"config should be rejected: {bad}")
    print("per-bet sizing ok: 1/6 Kelly = " + ", ".join(f"{f:.1%}" for f in sizes) + " for weak / typical / strong")


def test_house_sizing(tmp: Path) -> None:
    """House money: the year's starting money at 1/6 Kelly, this year's profit (net of tax owed) at 1/3 Kelly."""
    from types import SimpleNamespace

    from trading_system.live import main as cli
    from trading_system.live.live_strategy import size_bet

    model = PerBetModel(PACKAGED_MODEL)
    cfg = LiveConfig(data_dir=str(tmp))
    cfg.sizing.mode, cfg.sizing.model_path = "perbet_house", str(PACKAGED_MODEL)
    cfg.validate()
    k = model.fraction(1.5)
    sig = SimpleNamespace(score=1.5, dollar_vol=1e9, ref_close=5.0)

    def frac(nlv: float, start: float | None, realized: float = 0.0) -> float:
        acct = AccountInfo("U0", nlv, nlv, 0.0, float("inf"))
        return size_bet(cfg, sig, 5.0, acct, None, realized, model, year_start_adj=start).fraction

    assert abs(frac(150_000, 150_000) - k / 6) < 1e-12                                  # no profit yet: 1/6
    assert abs(frac(150_000, None) - k / 6) < 1e-12                                     # no start recorded yet
    assert abs(frac(150_000, 100_000) - k * (1 / 6 + (1 / 6) * 50_000 / 150_000)) < 1e-12  # up 50%: 0.222 Kelly
    assert abs(frac(150_000, 100_000, 40_000) - k * (1 / 6 + (1 / 6) * 40_000 / 150_000)) < 1e-12  # $10k tax owed
    assert abs(frac(150_000, 200_000) - k / 6) < 1e-12                                  # below the start: still 1/6
    assert frac(400_000, 100_000) < cfg.sizing.max_position_pct + 1e-12                 # 10% cap still applies

    # the year's starting point: first equity of the year, unless reset by hand within the same year
    journal = Journal(tmp / f"gapshort-{cfg.mode}.db")
    for day, adj in (("2025-12-31", 90_000.0), ("2026-01-02", 100_000.0), ("2026-01-05", 110_000.0)):
        journal.record_equity(day, adj, adj)
    stub = SimpleNamespace(journal=journal)
    assert BotService._year_start_adj(stub, "2026-06-01") == 100_000.0
    assert BotService._year_start_adj(stub, "2027-01-02") is None
    assert cli.cmd_reset_year_start(cfg) == 0                                            # uses the last record
    assert BotService._year_start_adj(stub, "2026-06-01") == 110_000.0
    assert BotService._year_start_adj(stub, "2027-03-01") is None                       # a reset only lasts its year
    bad = LiveConfig()
    bad.sizing.mode, bad.sizing.model_path, bad.sizing.profit_kelly_mult = "perbet_house", "m.json", 0.1
    try:
        bad.validate()
        raise AssertionError("profit_kelly_mult below kelly_mult should be rejected")
    except ValueError:
        pass
    print(f"house-money sizing ok: typical setup {k / 6:.1%} flat, {frac(150_000, 100_000):.1%} when up 50% this year")


def build_demo_service(tmp: Path):
    from trading_system.live.broker import SimBroker
    from trading_system.live.service import BotService

    cfg = LiveConfig(mode="demo", data_dir=str(tmp), secrets_path=str(tmp / "secrets.json"), demo_start="2026-01-01",
                     demo_seconds_per_day=0)
    cfg.validate()
    sim = SimBroker(cfg)
    journal = Journal(tmp / "demo.db")
    return cfg, sim, journal, BotService(cfg, sim, journal, Notifier(cfg, {}))


def test_demo_matches_backtest(cfg, sim, service) -> None:
    asyncio.run(service.run_demo(seconds_per_day=0, loop=False))
    live = sim.mock.summarize_performance()
    ref = sim.adp.run_replay(sim.engine_cfg, start_date=cfg.demo_start).summarize_performance()
    cols = ["ticker_idx", "entry_day_idx", "exit_day_idx", "exit_reason"]
    a = live["trades_df"].sort_values(["entry_day_idx", "ticker_idx"]).reset_index(drop=True)
    b = ref["trades_df"].sort_values(["entry_day_idx", "ticker_idx"]).reset_index(drop=True)
    assert len(a) == len(b) > 100, (len(a), len(b))
    assert (a[cols].values == b[cols].values).all()
    assert float(np.max(np.abs(a["net_return_pct"].to_numpy() - b["net_return_pct"].to_numpy()))) < 1e-9
    eq_diff = float(np.max(np.abs(live["equity_series"].to_numpy() - ref["equity_series"].to_numpy())))
    assert eq_diff < 1e-6, eq_diff
    jt = pd.DataFrame(service.journal.recent_trades(10_000))
    assert int((jt["status"] == "closed").sum()) == len(a)
    print(f"demo parity ok: {len(a)} trades, max equity diff ${eq_diff:.2e}, "
          f"after-tax CAGR {live['cagr']:.2%} vs {ref['cagr']:.2%}")


def test_report_in_demo(service) -> None:
    """Demo fills are the backtest's fills, so the twin must match the account to the cent."""
    j = service.journal
    rows = j.twin_rows()
    trades, comm = j.trades_by_id(), j.commissions_by_trade()
    closed = [t for t in trades.values() if t["status"] == "closed"]
    taken = [r for r in rows if r["kind"] == "taken"]
    assert len(taken) == len(trades) and all(r["status"] in ("open", "closed") for r in taken)
    ex = edge_report.execution_rows(rows, trades, comm)
    assert len(ex) == len(closed) > 100
    assert max(abs(e["gap"]) for e in ex) < 1e-9
    by_id = {r["trade_id"]: r for r in taken}
    for t in closed:
        r = by_id[t["id"]]
        assert r["m_exit_day"] == t["exit_date"] and {"time": "time exit"}.get(r["m_reason"], r["m_reason"]) == t["exit_reason"]
    series = j.edge_series(1000)
    assert max(abs(s["actual"] - s["theory"]) for s in series) < 1e-6
    rep = service.report_view()
    assert rep["execution"]["verdict"] == "ok" and abs(rep["execution"]["gap"]) < 1e-9
    assert rep["edge"]["n"] == len(ex) and rep["edge"]["verdict"] in ("ok", "watch", "bad")
    assert rep["day"] == series[-1]["day"] and rep["today"]["gap"] == 0.0 and rep["series"] and rep["daily"]
    print(f"report in demo ok: {len(ex)} trades, backtest twin = account (max gap {max(abs(e['gap']) for e in ex):.1e}), "
          f"edge check '{rep['edge']['verdict']}' (rank {rep['edge']['rank']:.3f})")


class BigSim(SimBroker):
    """A large account, so whole-share rounding never drops a trade (split-adjusted demo prices can be huge)."""

    async def account(self) -> AccountInfo:
        return AccountInfo(self.account_id, 1e9, 1e9, 0.0, 1e9)


class SlipSim(SimBroker):
    """Fills 1% worse than the backtest on both sides: sells 1% lower, buys back 1% higher."""

    async def fills_today(self):
        out = await super().fills_today()
        for f in out:
            f.price *= 0.99 if f.side == "SLD" else 1.01
        return out


async def _drive(service, sim) -> None:
    while not sim.finished:
        sim.begin_day()
        await service.decision_cycle(allow_entries=sim.days_left() >= 2)
        sim.end_day()
        await service.reconcile()


def test_shadow_book_matches_backtest(tmp: Path) -> None:
    cfg = LiveConfig(mode="shadow", data_dir=str(tmp), secrets_path=str(tmp / "s.json"), demo_start="2026-01-01",
                     demo_seconds_per_day=0)
    cfg.validate()
    sim = BigSim(cfg)
    service = BotService(cfg, sim, Journal(tmp / "shadow.db"), Notifier(cfg, {}))
    asyncio.run(_drive(service, sim))
    rows = [r for r in service.journal.twin_rows(kinds=("shadow",)) if r["status"] == "closed"]
    got = sorted((r["symbol"], r["day"], r["m_exit_day"], r["m_reason"], round(edge_report.model_ret(r), 9))
                 for r in rows)
    ref = sim.adp.run_replay(sim.engine_cfg, start_date=cfg.demo_start).summarize_performance()["trades_df"]
    exp = sorted((t.ticker, str(t.entry_date.date()), str(t.exit_date.date()), t.exit_reason,
                  round(t.net_return_pct, 9)) for t in ref.itertuples())
    assert got == exp, (len(got), len(exp), sorted(set(exp) ^ set(got))[:4])
    assert not sim.mock.positions() and not sim.mock.all_executions                     # nothing was ever sent
    print(f"shadow book ok: {len(got)} virtual trades = the backtest's trades, no orders sent")


def test_execution_attribution(tmp: Path) -> None:
    cfg = LiveConfig(mode="demo", data_dir=str(tmp), secrets_path=str(tmp / "s.json"), demo_start="2026-07-01",
                     demo_seconds_per_day=0)
    cfg.validate()
    sim = SlipSim(cfg)
    service = BotService(cfg, sim, Journal(tmp / "slip.db"), Notifier(cfg, {}))
    asyncio.run(service.run_demo(seconds_per_day=0, loop=False))
    ex = service.report_view()["execution"]
    assert ex["n"] > 50 and abs(ex["entry"] + 0.01) < 1e-9, ex                         # sold 1% below the backtest
    assert -0.0135 < ex["exit"] < -0.0065 and abs(ex["borrow"]) < 1e-12 and ex["fees"] == 0.0, ex
    assert abs(ex["gap"] - (ex["entry"] + ex["exit"])) < 1e-12 and ex["verdict"] == "bad", ex
    print(f"execution attribution ok: {ex['n']} trades, entry {ex['entry']:+.2%}, exit {ex['exit']:+.2%}, "
          f"total {ex['gap']:+.2%} per trade -> '{ex['verdict']}'")


def test_api(cfg, service, journal) -> None:
    from fastapi.testclient import TestClient

    from trading_system.live.auth import AuthStore
    from trading_system.live.web_server import create_app

    app = create_app(service, cfg, AuthStore(journal, hash_password(PASSWORD)))

    def client() -> TestClient:
        return TestClient(app, base_url="https://testserver")

    c = client()
    r = c.get("/")
    assert r.status_code == 200
    for header in ("content-security-policy", "x-frame-options", "x-content-type-options", "referrer-policy",
                   "permissions-policy"):
        assert header in r.headers, header
    assert "unsafe-inline" not in r.headers["content-security-policy"]
    set_cookie = r.headers.get("set-cookie", "")
    assert CSRF_COOKIE in set_cookie and "Secure" in set_cookie and "SameSite=strict" in set_cookie
    csrf = c.cookies.get(CSRF_COOKIE)

    assert c.get("/api/status").status_code == 401
    assert c.get("/api/positions").status_code == 401
    assert c.get("/api/report").status_code == 401
    assert c.post("/api/login", json={"password": PASSWORD}).status_code == 403          # no CSRF header
    assert c.post("/api/pause", headers={"X-CSRF-Token": csrf}).status_code == 401       # no session
    assert c.put("/api/status").status_code == 405
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404
    big = c.post("/api/login", content=b"x" * 5000, headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"})
    assert big.status_code == 413

    r = c.post("/api/login", json={"password": PASSWORD}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200, r.text
    sc = r.headers.get("set-cookie", "")
    assert SESSION_COOKIE in sc and "HttpOnly" in sc and "Secure" in sc and "SameSite=strict" in sc
    assert "Domain" not in sc
    csrf = c.cookies.get(CSRF_COOKIE)                                                     # rotated at login
    s = c.get("/api/status")
    assert s.status_code == 200 and s.json()["mode"] == "demo"
    assert s.headers["cache-control"] == "no-store"
    for path in ("/api/positions", "/api/orders", "/api/signals", "/api/trades", "/api/equity", "/api/events",
                 "/api/report"):
        assert c.get(path).status_code == 200, path
    rep = c.get("/api/report").json()
    assert {"day", "today", "events", "series", "daily", "edge", "execution", "missed", "trades"} <= set(rep)

    assert c.post("/api/pause").status_code == 403                                        # session but no CSRF
    assert c.post("/api/pause", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert c.post("/api/pause", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert journal.get("paused") == "1"
    assert c.post("/api/resume", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert journal.get("paused") == "0"

    assert c.post("/api/close", json={"symbol": "../x", "password": PASSWORD},
                  headers={"X-CSRF-Token": csrf}).status_code == 422
    assert c.post("/api/close", json={"symbol": "ZZZZ", "password": PASSWORD},
                  headers={"X-CSRF-Token": csrf}).status_code == 404
    assert c.post("/api/flatten", json={"password": "not the password"},
                  headers={"X-CSRF-Token": csrf}).status_code == 401
    assert c.get("/api/status").status_code == 200                                        # still signed in
    r = c.post("/api/flatten", json={"password": PASSWORD}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200 and journal.get("paused") == "1"

    assert c.post("/api/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert c.get("/api/status").status_code == 401

    # brute force: 5 wrong passwords, then even the right one is refused for a while
    c2 = client()
    c2.get("/")
    csrf2 = c2.cookies.get(CSRF_COOKIE)
    codes = [c2.post("/api/login", json={"password": f"wrong-{i}-xxxxxxxx"},
                     headers={"X-CSRF-Token": csrf2}).status_code for i in range(5)]
    assert codes == [401] * 5, codes
    r = c2.post("/api/login", json={"password": PASSWORD}, headers={"X-CSRF-Token": csrf2})
    assert r.status_code == 429 and "retry-after" in r.headers
    print("api security ok")


def test_bwb_demo_and_dual_strategy_api(tmp: Path, gs_service, gs_journal) -> None:
    from fastapi.testclient import TestClient

    from trading_system.live.auth import AuthStore
    from trading_system.live.bwb_broker import SimBwbBroker, load_clean_bwb_panel
    from trading_system.live.bwb_service import BwbBotService
    from trading_system.live.bwb_strategy import BwbMarketSnapshot, build_bwb_plan, settle_bwb
    from trading_system.live.web_server import create_app

    cfg = LiveConfig(mode="demo", data_dir=str(tmp), secrets_path=str(tmp / "s.json"),
                     demo_start="2018-01-02", demo_seconds_per_day=0.0, initial_capital=100_000.0)
    cfg.bwb.initial_capital = 100_000.0
    cfg.bwb.sizing_mode = "earned_ramp"
    cfg.validate()

    bwb_broker = SimBwbBroker(cfg, start_date="2018-01-02")
    bwb_journal = Journal(tmp / "bwb-demo.db")
    bwb_service = BwbBotService(cfg, bwb_broker, bwb_journal, Notifier(cfg, {}))
    asyncio.run(bwb_service.run_demo(seconds_per_day=0.0, loop=False))

    eq_rows = bwb_journal.equity(limit=5000)
    bot_eq = np.array([r["nlv"] for r in eq_rows])
    df = load_clean_bwb_panel()
    sub = df.loc[df.index >= pd.Timestamp("2018-01-02")]
    assert len(bot_eq) == len(sub) > 2000

    w = 100_000.0
    ref_eq = np.empty(len(sub))
    for i in range(len(sub)):
        row = sub.iloc[i]
        f_t = ((0.05 + 0.025 * np.clip((w / 100000.0 - 0.85) / 0.15, 0.0, 1.0))
               if w <= 100_000.0 else min(0.20, (0.075 * 100_000.0 + 0.50 * (w - 100_000.0)) / w))
        sn = BwbMarketSnapshot(
            day=str(sub.index[i].date()), spot_open=float(row["S_clean"]), spot_close=float(row["C_clean"]),
            spot_mark=float(row["C_clean"]), iv1d=float(row["iv1d_clean"]), vix_open=float(row["vix_o_clean"]),
            vix_prev_close=float(row["vix_prev_clean"]), vix1d_prev_close=float(row["vix1d_prev_clean"]),
            iv1d_morning_pct=float(row["iv1d_clean_pct"]), rf_annual=float(row["rf_ann"]),
            rf_daily=float(row["rf_daily"]), f1_pass=bool(row["f1_clean"]), f1_reason=""
        )
        pl = build_bwb_plan(sn, cfg.bwb, equity=w)
        st = settle_bwb(pl, float(row["C_clean"]), 1.0)
        f_eff = f_t if bool(row["f1_clean"]) else 0.0
        w = w * (1.0 + float(row["rf_daily"]) + f_eff * st.ret_on_risk)
        ref_eq[i] = w

    max_diff = float(np.max(np.abs(bot_eq - ref_eq)))
    assert max_diff < 1e-6, max_diff
    rep = bwb_service.report_view()
    assert rep["edge"]["n"] > 1500 and rep["edge"]["verdict"] == "ok" and rep["execution"]["verdict"] == "ok"
    au0 = rep["bwb_audit"]
    assert au0["n_filled"] == rep["edge"]["n"] and au0["verdict"] == "ok"
    assert abs(au0["model_error_pct"]) < 1e-12 and abs(au0["extra_slip_pct"]) < 1e-12

    # Verify Dual-Strategy API (/api/overview + ?strategy=gapshort vs ?strategy=bwb)
    gs_journal.set("paused", "0")
    bwb_journal.set("paused", "0")
    app = create_app(gs_service, cfg, AuthStore(gs_journal, hash_password(PASSWORD)), bwb_service=bwb_service)
    c = TestClient(app, base_url="https://testserver")
    c.get("/")
    csrf = c.cookies.get(CSRF_COOKIE)
    assert c.post("/api/login", json={"password": PASSWORD}, headers={"X-CSRF-Token": csrf}).status_code == 200
    csrf = c.cookies.get(CSRF_COOKIE)

    ov = c.get("/api/overview").json()
    assert ov["combined"]["initial_capital"] == 200_000.0
    assert "gapshort" in ov["strategies"] and "bwb" in ov["strategies"]
    assert ov["strategies"]["gapshort"]["status"]["initial_capital"] == 100_000.0
    assert ov["strategies"]["bwb"]["status"]["initial_capital"] == 100_000.0
    assert ov["strategies"]["bwb"]["status"]["net_liquidation"] > 2_000_000.0
    assert "bwb_audit" in c.get("/api/report?strategy=bwb").json()
    assert "bwb_audit" not in c.get("/api/report?strategy=gapshort").json()

    # Independent strategy pause/resume controls
    assert c.post("/api/pause?strategy=bwb", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert bwb_journal.get("paused") == "1" and gs_journal.get("paused") == "0"
    assert c.post("/api/resume?strategy=bwb", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert bwb_journal.get("paused") == "0"
    assert c.get("/api/status?strategy=invalid").status_code == 422

    # Verify Yearly House-Money ("yearly_house") Jan-1 principal lock & Shared-Capital 95% margin guard
    from trading_system.live.bwb_strategy import compute_earned_kelly_fraction, size_bwb_bet
    from trading_system.live.config import BwbSettings

    cfg_yh = BwbSettings(sizing_mode="yearly_house", isolated_capital=False, max_combined_margin_pct=0.95)
    # At the start of a new year ($400k equity == $400k Jan-1 anchor), yearly_house resets to 7.5% base
    f_jan1 = compute_earned_kelly_fraction(400_000.0, 100_000.0, 400_000.0, cfg_yh, year_start_equity=400_000.0)
    assert abs(f_jan1 - 0.075) < 1e-9, f_jan1
    # Once up +42.5% above the $400k Jan-1 anchor ($570k), yearly_house reaches the 20.0% cap
    f_up = compute_earned_kelly_fraction(570_000.0, 100_000.0, 570_000.0, cfg_yh, year_start_equity=400_000.0)
    assert abs(f_up - 0.200) < 1e-9, f_up
    # When Gap Short is using 85% FINRA 4210 margin, the 95% shared-margin guard clips BWB from 20.0% to 10.0%
    sz_guarded = size_bwb_bet(570_000.0, 570_000.0, pl, cfg_yh, discrete_contracts=False,
                              year_start_equity=400_000.0, other_margin_used_pct=0.85)
    assert abs(sz_guarded.collat_fraction - 0.100) < 1e-9 and "95% shared-margin guard" in sz_guarded.note, sz_guarded

    # Verify /api/overview in Shared Capital mode (isolated_capital = False on both strategies)
    cfg.isolated_capital = False
    cfg.bwb.isolated_capital = False
    cfg.bwb.sizing_mode = "yearly_house"
    bwb_service.peer_service = gs_service
    ov_shared = c.get("/api/overview").json()
    assert ov_shared["combined"]["shared_capital"] is True
    assert ov_shared["combined"]["initial_capital"] == 100_000.0

    print(f"bwb demo, yearly_house & shared-capital api ok: {len(bot_eq)} days, {rep['edge']['n']} BWB trades, "
          f"max diff ${max_diff:.2e}, final $100k -> ${bot_eq[-1]:,.2f}")


def test_bwb_live_premium_audit_and_guards(tmp: Path) -> None:
    """Verifies Model Error vs Extra Slippage decomposition, min-credit gate, 10:30 cancel guard, and shadow quotes."""
    from types import ModuleType, SimpleNamespace

    from trading_system.live.bwb_broker import IBKRBwbBroker, SimBwbBroker
    from trading_system.live.bwb_service import BwbBotService
    from trading_system.live.bwb_strategy import BwbMarketSnapshot, build_bwb_plan

    async def _run_bwb_slice(svc: BwbBotService, sim_b: SimBwbBroker) -> None:
        while not sim_b.finished:
            sim_b.begin_day()
            await svc.decision_cycle(allow_entries=True)
            sim_b.end_day()
            await svc.reconcile()

    # 1. Decomposed Haircut: -40 bps Wrong Model + -25 bps Extra Slippage = -65 bps total haircut
    cfg1 = LiveConfig(mode="demo", data_dir=str(tmp), secrets_path=str(tmp / "s.json"),
                      demo_start="2026-01-02", demo_seconds_per_day=0.0)
    cfg1.validate()
    sim1 = SimBwbBroker(cfg1, start_date="2026-01-02", end_date="2026-06-30")
    sim1.quote_haircut_pct_of_risk = -0.0040   # live 10:30 mid is 40 bps of W_risk below model mid
    sim1.extra_slip_pct_of_risk = 0.0025       # fills 25 bps of W_risk worse than live quote est_net
    j1 = Journal(tmp / "bwb-haircut.db")
    svc1 = BwbBotService(cfg1, sim1, j1, Notifier(cfg1, {}))
    asyncio.run(_run_bwb_slice(svc1, sim1))

    rep1 = svc1.report_view()
    au1 = rep1["bwb_audit"]
    assert au1["n_filled"] > 50 and not au1["using_shadow_quotes"], au1
    assert abs(au1["model_error_pct"] - (-0.0040)) < 1e-9, au1
    assert abs(au1["extra_slip_pct"] - (-0.0025)) < 1e-9, au1
    assert abs(au1["total_haircut_pct"] - (-0.0065)) < 1e-9, au1
    assert abs(au1["true_edge_pct"] - (au1["actual_net_pct"] + au1["hist_payoff_cons_pct"])) < 1e-12
    assert au1["verdict"] == "watch" and 0.05 < au1["recommended_max_collat_pct"] < cfg1.bwb.max_collat_pct, au1
    assert abs(rep1["execution"]["gap"] - (-0.0065)) < 1e-6, rep1["execution"]

    # 2. Pre-trade minimum net credit gate blocks negative/zero-edge entries (skipped_low_credit)
    cfg2 = LiveConfig(mode="demo", data_dir=str(tmp), secrets_path=str(tmp / "s.json"),
                      demo_start="2026-01-02", demo_seconds_per_day=0.0)
    cfg2.bwb.min_net_credit_pct = 0.0185
    cfg2.validate()
    sim2 = SimBwbBroker(cfg2, start_date="2026-01-02", end_date="2026-04-30")
    sim2.quote_haircut_pct_of_risk = -0.0170   # pushes est_net below 1.85% floor and <= 1.50% break-even
    j2 = Journal(tmp / "bwb-floor-block.db")
    svc2 = BwbBotService(cfg2, sim2, j2, Notifier(cfg2, {}))
    asyncio.run(_run_bwb_slice(svc2, sim2))
    au2 = svc2.report_view()["bwb_audit"]
    assert au2["n_filled"] == 0 and au2["skipped_low_credit"] > 20, au2
    assert len(j2.recent_trades(100)) == 0

    # If the floor is disabled (0.001) and those sub-breakeven fills go through, audit immediately flags 'bad'
    cfg2b = LiveConfig(mode="demo", data_dir=str(tmp), secrets_path=str(tmp / "s.json"),
                       demo_start="2026-01-02", demo_seconds_per_day=0.0)
    cfg2b.bwb.min_net_credit_pct = 0.001
    cfg2b.validate()
    sim2b = SimBwbBroker(cfg2b, start_date="2026-01-02", end_date="2026-04-30")
    sim2b.quote_haircut_pct_of_risk = -0.0170
    svc2b = BwbBotService(cfg2b, sim2b, Journal(tmp / "bwb-bad-edge.db"), Notifier(cfg2b, {}))
    asyncio.run(_run_bwb_slice(svc2b, sim2b))
    au2b = svc2b.report_view()["bwb_audit"]
    assert au2b["verdict"] == "bad" and au2b["true_edge_pct"] <= 0.0 and au2b["recommended_max_collat_pct"] == 0.0, au2b

    # 3. Unfilled 10:30 AM timeout cancellation guard (never leaves hanging limit orders open)
    cfg3 = LiveConfig(mode="demo", data_dir=str(tmp), secrets_path=str(tmp / "s.json"),
                      demo_start="2026-01-02", demo_seconds_per_day=0.0)
    cfg3.validate()
    sim3 = SimBwbBroker(cfg3, start_date="2026-01-02", end_date="2026-03-31")
    sim3.simulate_timeout_unfilled = True
    j3 = Journal(tmp / "bwb-timeout.db")
    svc3 = BwbBotService(cfg3, sim3, j3, Notifier(cfg3, {}))
    asyncio.run(_run_bwb_slice(svc3, sim3))
    au3 = svc3.report_view()["bwb_audit"]
    assert au3["n_filled"] == 0 and au3["unfilled_cancelled"] > 20 and len(j3.recent_trades(100)) == 0, au3

    # 4. Shadow mode logs live 10:30 AM option quotes without sending any orders
    cfg4 = LiveConfig(mode="shadow", data_dir=str(tmp), secrets_path=str(tmp / "s.json"),
                      demo_start="2026-01-02", demo_seconds_per_day=0.0)
    cfg4.validate()
    sim4 = SimBwbBroker(cfg4, start_date="2026-01-02", end_date="2026-04-30")
    sim4.quote_haircut_pct_of_risk = -0.0030
    svc4 = BwbBotService(cfg4, sim4, Journal(tmp / "bwb-shadow.db"), Notifier(cfg4, {}))
    asyncio.run(_run_bwb_slice(svc4, sim4))
    au4 = svc4.report_view()["bwb_audit"]
    assert au4["using_shadow_quotes"] is True and au4["n_filled"] == 0 and au4["n_quoted"] > 20, au4
    assert abs(au4["model_error_pct"] - (-0.0030)) < 1e-9, au4

    # 5. IBKRBwbBroker unit check: live NBBO quote extraction, 2-step limit + timeout cancel, and leg cashflow math
    had_ib_async = "ib_async" in sys.modules
    if not had_ib_async:
        fake_mod = ModuleType("ib_async")
        fake_mod.Option = lambda *a, **kw: SimpleNamespace(args=a, kwargs=kw, conId=int(a[2]))
        fake_mod.ComboLeg = lambda **kw: SimpleNamespace(**kw)
        fake_mod.Contract = lambda **kw: SimpleNamespace(**kw)
        fake_mod.Order = lambda **kw: SimpleNamespace(orderId=99, **kw)
        sys.modules["ib_async"] = fake_mod
    try:
        cfg_ib = LiveConfig(mode="paper", data_dir=str(tmp), secrets_path=str(tmp / "s.json"))
        cfg_ib.bwb.entry_timeout_sec = 5
        cfg_ib.validate()
        ib_brk = IBKRBwbBroker(cfg_ib, readonly=False)
        ib_brk.account_id = "DU123456"

        snap = BwbMarketSnapshot(
            day="2026-10-26", spot_open=5800.0, spot_close=None, spot_mark=5800.0,
            iv1d=0.115, vix_open=15.0, vix_prev_close=15.5, vix1d_prev_close=11.0,
            iv1d_morning_pct=11.5, rf_annual=0.045, rf_daily=0.045 / 252.0,
            f1_pass=True, f1_reason="F1 pass",
        )
        plan = build_bwb_plan(snap, cfg_ib.bwb, equity=100_000.0)

        class _FakeIB:
            def __init__(self, fill_mode: str):
                self.fill_mode = fill_mode
                self.cancelled = 0
                self.placed_limits: list[float] = []

            def isConnected(self) -> bool:
                return True

            async def qualifyContractsAsync(self, *contracts):
                for idx, c in enumerate(contracts):
                    c.conId = 1001 + idx

            async def reqTickersAsync(self, *_contracts):
                # K_hi: 9.90/10.10 (mid 10.0), K_mid: 6.45/6.55 (mid 6.5), K_lo: 1.45/1.55 (mid 1.5)
                # Combo live mid = 2*(6.5) - 10.0 - 1.5 = +1.50 pts
                return [
                    SimpleNamespace(bid=9.90, ask=10.10),
                    SimpleNamespace(bid=6.45, ask=6.55),
                    SimpleNamespace(bid=1.45, ask=1.55),
                ]

            def placeOrder(self, _bag, order):
                self.placed_limits.append(float(order.lmtPrice))
                if self.fill_mode == "timeout":
                    return SimpleNamespace(
                        isDone=lambda: self.cancelled > 0,
                        orderStatus=SimpleNamespace(filled=0.0, avgFillPrice=0.0, status="Cancelled"),
                        fills=[],
                    )
                fills = [
                    SimpleNamespace(
                        contract=SimpleNamespace(secType="OPT"),
                        execution=SimpleNamespace(shares=2.0, price=10.02, side="BOT"),
                        commissionReport=SimpleNamespace(commission=2.70),
                    ),
                    SimpleNamespace(
                        contract=SimpleNamespace(secType="OPT"),
                        execution=SimpleNamespace(shares=4.0, price=6.48, side="SLD"),
                        commissionReport=SimpleNamespace(commission=5.40),
                    ),
                    SimpleNamespace(
                        contract=SimpleNamespace(secType="OPT"),
                        execution=SimpleNamespace(shares=2.0, price=1.50, side="BOT"),
                        commissionReport=SimpleNamespace(commission=2.70),
                    ),
                ]
                return SimpleNamespace(
                    isDone=lambda: True,
                    orderStatus=SimpleNamespace(filled=2.0, avgFillPrice=-1.44, status="Filled"),
                    fills=fills,
                )

            def cancelOrder(self, _order):
                self.cancelled += 1

        ib_brk.ib = _FakeIB("filled")
        q_ib = asyncio.run(ib_brk.quote_bwb_spread(plan))
        assert q_ib.source == "ibkr_nbbo" and abs(q_ib.live_mid_credit_pts - 1.50) < 1e-9, q_ib
        res_fill = asyncio.run(ib_brk.place_bwb_spread(plan, 2.0, "SPXW test", quote=q_ib, min_credit_pts=0.80))
        # Gross = (4*6.48 - 2*10.02 - 2*1.50) / 2 = (25.92 - 20.04 - 3.00) / 2 = 1.44 pts; comm = $10.80 => 0.054 pts
        assert res_fill.filled and abs(res_fill.gross_credit_pts - 1.44) < 1e-9, res_fill
        assert abs(res_fill.net_credit_pts - (1.44 - 0.054)) < 1e-9, res_fill

        # Timeout test (speed up asyncio.sleep inside test)
        ib_brk.ib = _FakeIB("timeout")
        ib_brk.cfg.bwb.entry_timeout_sec = 5
        orig_sleep = asyncio.sleep
        clock = [0.0]

        async def _fast_sleep(dt: float):
            clock[0] += dt
            await orig_sleep(0)

        loop = asyncio.new_event_loop()
        orig_time = loop.time
        loop.time = lambda: clock[0]
        asyncio.sleep = _fast_sleep
        try:
            res_to = loop.run_until_complete(
                ib_brk.place_bwb_spread(plan, 2.0, "SPXW test", quote=q_ib, min_credit_pts=0.80)
            )
        finally:
            asyncio.sleep = orig_sleep
            loop.time = orig_time
            loop.close()
        assert not res_to.filled and ib_brk.ib.cancelled == 1 and len(ib_brk.ib.placed_limits) == 2, (
            res_to, ib_brk.ib.placed_limits
        )
    finally:
        if not had_ib_async:
            sys.modules.pop("ib_async", None)

    print(
        f"bwb live premium audit & guards ok: model_err {au1['model_error_pct']:+.2%}, "
        f"extra_slip {au1['extra_slip_pct']:+.2%}, true_edge {au1['true_edge_pct']:+.2%} "
        f"(kelly cap -> {au1['recommended_max_collat_pct']:.1%}), floor skips {au2['skipped_low_credit']}, "
        f"timeout cancels {au3['unfilled_cancelled']}"
    )


def main() -> None:
    test_calendar()
    test_auth_helpers()
    test_journal_partial_fills()
    test_edge_stats_synthetic()
    test_perbet_sizing()
    with tempfile.TemporaryDirectory() as d:
        test_house_sizing(Path(d))
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cfg, sim, journal, service = build_demo_service(tmp)
        test_demo_matches_backtest(cfg, sim, service)
        test_report_in_demo(service)
        test_api(cfg, service, journal)
        test_bwb_demo_and_dual_strategy_api(tmp, service, journal)
    with tempfile.TemporaryDirectory() as d:
        test_bwb_live_premium_audit_and_guards(Path(d))
    with tempfile.TemporaryDirectory() as d:
        test_shadow_book_matches_backtest(Path(d))
    with tempfile.TemporaryDirectory() as d:
        test_execution_attribution(Path(d))
    print("all tests passed")


if __name__ == "__main__":
    main()
