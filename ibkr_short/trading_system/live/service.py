"""The trading service: daily decision at the close, reconciliation, phone actions, and the views the app shows."""
from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from datetime import timedelta
from pathlib import Path

from ..models import BorrowQuote, EngineConfig
from ..strategy_core import compute_entry_and_brackets, evaluate_candidate
from . import edge_report
from . import market_calendar as mc
from .broker import ReadOnlyError
from .config import LiveConfig
from .journal import Journal
from .live_strategy import PerBetModel, build_inputs, size_bet
from .notify import Notifier

log = logging.getLogger(__name__)

LOC_LIMIT_BELOW_LAST = 0.03   # sell-on-close limit: no fill if the stock collapses >3% into the bell
HEARTBEAT_EVERY_S = 300
FETCH_CONCURRENCY = 6         # parallel history requests, so the scan ends well before the close-order cutoffs
PACKAGED_MODEL = Path(__file__).with_name("model_perbet.json")


def mask_account(account_id: str) -> str:
    if len(account_id) <= 5:
        return "****"
    return f"{account_id[:2]}****{account_id[-3:]}"


def _packaged_model() -> PerBetModel | None:
    try:
        return PerBetModel(PACKAGED_MODEL)
    except (OSError, ValueError, KeyError) as exc:
        log.warning("edge model not loaded: %s", type(exc).__name__)
        return None


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


class BotService:
    def __init__(self, cfg: LiveConfig, broker, journal: Journal, notifier: Notifier,
                 model: PerBetModel | None = None):
        self.cfg = cfg
        self.broker = broker
        self.journal = journal
        self.notifier = notifier
        self.model = model
        self.edge = model if model is not None else _packaged_model()  # expected edge for the end-of-day report
        self.engine_cfg = EngineConfig(
            pos_pct=cfg.sizing.static_pct, locate_fee_pct=0.0, borrow_annual=cfg.borrow_annual,
            max_borrow_annual=cfg.max_borrow_annual, use_live_borrow_rate=False, slip_per_side=cfg.slip_per_side,
            tax_rate=0.25, enforce_clean_data=True, enforce_whale_gate=False, max_positions=cfg.max_positions,
            hold_days=cfg.hold_days, cooldown_days=cfg.cooldown_days)
        self._default_quote = BorrowQuote(ticker="DEFAULT", fee_rate_annual=cfg.borrow_annual)
        self.lock = asyncio.Lock()
        self.state = "starting"
        self.problem = ""
        self.last_decision: dict = {}
        self._last_heartbeat = 0.0
        self._stop = asyncio.Event()

    # ----------------------------------------------------------------- settings
    @property
    def read_only(self) -> bool:
        return self.cfg.mode == "shadow"

    @property
    def paused(self) -> bool:
        return self.journal.get("paused", "0") == "1"

    def stop(self) -> None:
        self._stop.set()

    def _log(self, level: str, kind: str, message: str) -> None:
        getattr(log, "warning" if level == "warn" else level if level in ("info", "error") else "info")(message)
        self.journal.event(level, kind, message)

    # ----------------------------------------------------------------- fills -> journal
    async def _sync_fills(self) -> None:
        for f in await self.broker.fills_today():
            if self.journal.fill_seen(f.exec_id):
                if f.commission:
                    self.journal.set_fill_commission(f.exec_id, f.commission)
                continue
            trade_id = None
            if f.role == "entry" and f.side in ("SLD", "SELL"):
                plan = json.loads(self.journal.get(f"plan:{f.symbol}", "{}") or "{}")
                trade_id, total, new = self.journal.record_entry_fill(f.symbol, f.day, f.price, f.shares, plan)
                self.journal.twin_link_fill(f.day, f.symbol, trade_id, total)
                self.journal.record_fill(f.exec_id, f.symbol, f.side, f.shares, f.price, f.day, f.role, f.commission,
                                         trade_id)
                self._log("info", "fill", f"Shorted {f.shares:,.0f} {f.symbol} at {f.price:.4g}")
                if new:
                    await self.notifier.send(f"Shorted {f.symbol}", f"{f.shares:,.0f} shares at {f.price:.4g}")
            elif f.side in ("BOT", "BUY"):
                reason = {"stop": "stop", "target": "target", "exit": "time exit", "manual": "manual"}.get(
                    f.role, f.role)
                res = self.journal.record_exit_fill(f.symbol, f.day, f.price, f.shares, reason)
                trade_id = res["id"] if res else None
                self.journal.record_fill(f.exec_id, f.symbol, f.side, f.shares, f.price, f.day, f.role, f.commission,
                                         trade_id)
                if res and res["closed"]:
                    pnl = res["pnl"] if res["pnl"] is not None else math.nan
                    self._log("info", "fill", f"Covered {f.symbol} at {f.price:.4g} ({reason}), P&L ${pnl:,.0f}")
                    priority = "high" if reason == "stop" else "default"
                    await self.notifier.send(f"Covered {f.symbol} ({reason})",
                                             f"{res['shares']:,.0f} shares, last at {f.price:.4g}, P&L ${pnl:,.0f}",
                                             priority)
                elif res:
                    self._log("info", "fill", f"Bought back {res['covered']:,.0f} of {res['shares']:,.0f} {f.symbol} "
                                              f"so far, last at {f.price:.4g} ({reason})")
                else:
                    self._log("warn", "fill", f"Buy of {f.shares:,.0f} {f.symbol} matches no open short")
            else:
                self.journal.record_fill(f.exec_id, f.symbol, f.side, f.shares, f.price, f.day, f.role, f.commission)

    # ----------------------------------------------------------------- exits
    async def _cover(self, symbol: str, shares: float, how: str, why: str) -> None:
        if self.read_only:
            self._log("info", "shadow", f"Would cover {abs(shares):,.0f} {symbol} ({why})")
            return
        await self.broker.cancel_brackets(symbol)
        await self.broker.cover(symbol, shares, how)
        self._log("info", "order", f"Cover {abs(shares):,.0f} {symbol} sent as {how} ({why})")

    def _manual_cover_type(self) -> str:
        if self.cfg.mode == "demo":
            return "MKT"
        now = self.broker.now()
        d = now.date()
        if mc.is_trading_day(d):
            open_ = now.replace(hour=9, minute=30, second=0, microsecond=0)
            if open_ <= now < mc.close_time(d) - timedelta(minutes=1):
                return "MKT"
        return "OPG"

    # ----------------------------------------------------------------- daily decision
    def _peak_and_ytd(self, today: str) -> tuple[float | None, float]:
        year_start = f"{today[:4]}-01-01"
        return self.journal.peak_adj_since(year_start), self.journal.realized_pnl_since(year_start)

    def _year_start_adj(self, today: str) -> float | None:
        """Equity (net of the tax owed) this year started from, for the house-money sizing.

        A manual reset (`reset-year-start`, e.g. after a deposit or withdrawal) wins within its own year; otherwise
        it is the first equity the bot recorded this year.
        """
        manual_day = self.journal.get("year_start_day")
        if manual_day and manual_day[:4] == today[:4]:
            return float(self.journal.get("year_start_adj"))
        first = self.journal.first_equity_since(f"{today[:4]}-01-01")
        return float(first["adj"]) if first else None

    def _last_exit(self, symbol: str) -> str | None:
        """Last exit for the cooldown: real trades, plus the virtual book in shadow mode."""
        days = [self.journal.last_exit_date(symbol)]
        if self.read_only:
            days.append(self.journal.twin_last_exit(symbol))
        days = [d for d in days if d]
        return max(days) if days else None

    def _actual_fee(self, quoted: float | None) -> float:
        """Borrow rate for estimating what the account pays: the demo broker charges the backtest's rate."""
        if self.cfg.mode == "demo" or quoted is None or not _finite(quoted):
            return self.cfg.borrow_annual
        return float(quoted)

    def _twin_set_kind(self, day: str, symbol: str, kind: str, note: str) -> None:
        for r in self.journal.twin_rows(day=day):
            if r["symbol"] == symbol:
                self.journal.twin_update(r["id"], kind=kind, note=note)

    async def _fetch_bars(self, requests: dict[str, int]) -> dict[str, list]:
        """Daily bars for several symbols at once ({symbol: days of history})."""
        sem = asyncio.Semaphore(FETCH_CONCURRENCY)

        async def one(sym: str, days: int):
            async with sem:
                try:
                    return sym, await self.broker.daily_bars(sym, days=days)
                except Exception as exc:
                    log.warning("no bars for %s: %s", sym, type(exc).__name__)
                    return sym, None

        return dict(await asyncio.gather(*(one(s, d) for s, d in requests.items())))

    async def _virtual_book(self, today: str) -> list[dict]:
        """Shadow mode's open virtual shorts, and which of them leave the book today (as the backtest would)."""
        rows = self.journal.twin_rows(kinds=("shadow",), statuses=("waiting", "open"))
        bars_by = await self._fetch_bars({r["symbol"]: 5 for r in rows})
        out = []
        for r in rows:
            bars = bars_by.get(r["symbol"]) or []
            bar = bars[-1] if bars and bars[-1].day[:10] == today and _finite(bars[-1].close) else None
            why = ""
            if bar is not None and r["status"] == "open":
                if bar.high >= r["m_stop"]:
                    why = "stop"
                elif r["m_target"] > 0 and bar.low <= r["m_target"]:
                    why = "target"
                elif self.broker.trading_days_between(r["day"], today) >= self.cfg.hold_days:
                    why = "day 3"
            out.append({"symbol": r["symbol"], "exits_today": bool(why), "why": why})
        return out

    async def decision_cycle(self, allow_entries: bool = True) -> dict:
        async with self.lock:
            b = self.broker
            today = b.today().isoformat()
            self.journal.set("last_decision_day", today)
            await self._sync_fills()

            # 1. Positions and today's exits. Shadow mode has no real positions, so it keeps a virtual book.
            exiting: set[str] = set()
            if self.read_only:
                book = await self._virtual_book(today)
                held = {v["symbol"] for v in book}
                exiting = {v["symbol"] for v in book if v["exits_today"]}
            else:
                shorts = [p for p in await b.positions() if p.shares < 0]
                held = {p.symbol for p in shorts}
                entry_day = {t["symbol"]: t["entry_date"] for t in self.journal.open_trades()}
                for p in shorts:
                    d0 = entry_day.get(p.symbol)
                    if d0 and b.trading_days_between(d0, today) >= self.cfg.hold_days:
                        try:
                            await self._cover(p.symbol, p.shares, "MOC", "day-3 exit")
                            exiting.add(p.symbol)
                        except Exception as exc:
                            self._log("error", "order", f"Day-3 exit for {p.symbol} failed: {type(exc).__name__}")
                            await self.notifier.send(f"Exit failed: {p.symbol}", "Check the position in IBKR", "high")
                await self._sync_fills()

            summary = {"day": today, "candidates": 0, "placed": 0, "exits": len(exiting), "note": ""}
            if not allow_entries:
                summary["note"] = "entries off for the last days of the demo data"
                self.last_decision = summary
                return summary
            # While paused, signals are still checked and tracked (not traded), so the edge check keeps learning
            # and can tell when results recover.
            record_only = self.paused
            if record_only:
                summary["note"] = "paused: no new shorts"

            # 2. New shorts
            acct = await b.account()
            nlv = acct.net_liquidation
            open_syms = held - exiting
            slots = self.cfg.max_positions - len(open_syms)
            if not record_only and (slots <= 0 or not math.isfinite(nlv) or nlv <= 0):
                summary["note"] = "all slots in use" if slots <= 0 else "no equity"
                self.last_decision = summary
                return summary

            candidates = []
            t0 = time.monotonic()
            movers = await b.movers()
            sem = asyncio.Semaphore(FETCH_CONCURRENCY)

            async def fetch(sym: str):
                async with sem:
                    try:
                        return await b.daily_bars(sym)
                    except Exception as exc:
                        log.warning("skipping %s: %s", sym, type(exc).__name__)
                        return None

            histories = await asyncio.gather(*(fetch(s) for s in movers))
            for sym, bars in zip(movers, histories):
                try:
                    if not bars or len(bars) < 2 or bars[-1].day[:10] != today:
                        continue
                    built = build_inputs(sym, bars, await b.gate_info(sym, bars))
                    if built is None:
                        continue
                    sig = evaluate_candidate(built[0], built[1], self._default_quote, self.engine_cfg)
                    if sig is not None:
                        candidates.append((sig, bars))
                except Exception as exc:
                    log.warning("skipping %s: %s", sym, type(exc).__name__)
            candidates.sort(key=lambda c: c[0].ticker_idx)
            candidates.sort(key=lambda c: -c[0].score if math.isfinite(c[0].score) else 1e9)
            summary["candidates"] = len(candidates)
            summary["scan_s"] = round(time.monotonic() - t0, 1)
            if self.cfg.mode != "demo":
                self._log("info", "scan", f"Checked {len(movers)} movers in {summary['scan_s']:.0f} s: "
                                          f"{len(candidates)} signals")

            peak_adj, realized_ytd = self._peak_and_ytd(today)
            year_start = self._year_start_adj(today)
            for sig, bars in candidates:
                sym = sig.ticker

                def note(action: str, detail: str, notional: float = 0.0) -> None:
                    self.journal.record_signal(today, sym, float(sig.score), sig.setups_str, action, detail, notional)

                if record_only:
                    if sym in open_syms or sym in exiting:
                        note("skipped", "already short")
                        continue
                    last_exit = self._last_exit(sym)
                    if last_exit and b.trading_days_between(last_exit, today) < self.cfg.cooldown_days:
                        note("skipped", "10-day cooldown")
                        continue
                    entry = compute_entry_and_brackets(sig.ref_close, sig.ref_high, self.engine_cfg)[0]
                    size = size_bet(self.cfg, sig, entry, acct, peak_adj, realized_ytd, self.model, year_start)
                    mu = self.edge.expected(sig.score) if self.edge is not None else None
                    note("skipped", "paused (tracked for the edge check)")
                    self.journal.twin_add(day=today, symbol=sym, setups=sig.setups_str, score=float(sig.score),
                                          kind="missed", note="paused", exp_ret=mu,
                                          shares=size.notional / entry if entry > 0 else 0.0,
                                          plan_price=sig.ref_close, fee_rate=None)
                    continue
                if slots <= 0:
                    note("skipped", "all slots in use")
                    continue
                if sym in open_syms:
                    note("skipped", "already short")
                    continue
                if sym in exiting:
                    note("skipped", "exits today")  # the backtest starts the cooldown on the exit day
                    continue
                last_exit = self._last_exit(sym)
                if last_exit and b.trading_days_between(last_exit, today) < self.cfg.cooldown_days:
                    note("skipped", "10-day cooldown")
                    continue
                borrow = await b.borrow_check(sym, bars)
                if borrow["split_flag"]:
                    note("skipped", "price history and quote disagree (split?)")
                    continue
                entry, stop, target = compute_entry_and_brackets(sig.ref_close, sig.ref_high, self.engine_cfg)
                size = size_bet(self.cfg, sig, entry, acct, peak_adj, realized_ytd, self.model, year_start)
                shares = size.notional / entry if entry > 0 else 0.0
                fee = borrow["fee"]
                mu = self.edge.expected(sig.score) if self.edge is not None else None
                twin = {"day": today, "symbol": sym, "setups": sig.setups_str, "score": float(sig.score),
                        "exp_ret": mu, "plan_price": sig.ref_close, "fee_rate": self._actual_fee(fee)}
                if not borrow["shortable"] or borrow["available"] <= 0:
                    note("skipped", "no shares to borrow")
                    self.journal.twin_add(**twin, kind="missed", note="no shares to borrow", shares=shares)
                    continue
                if fee is not None and fee > self.cfg.max_borrow_annual:
                    note("skipped", f"borrow fee {fee:.0%}/yr")
                    self.journal.twin_add(**twin, kind="missed", note=f"borrow fee {fee:.0%}/yr", shares=shares)
                    continue
                if self.cfg.mode != "demo":
                    shares = float(int(min(shares, borrow["available"])))
                if shares <= 0 or size.notional < 100:
                    note("skipped", f"size too small ({size.capped_by})")
                    continue
                detail = f"{size.fraction:.1%} of equity, stop {stop:.4g}, target {target:.4g}"
                if mu is not None:
                    detail += f", expected edge {mu:+.1%}"
                if self.read_only:
                    note("would place", detail, size.notional)
                    self.journal.twin_add(**twin, kind="shadow", note="", shares=shares)
                    self._log("info", "shadow", f"Would short {shares:,.0f} {sym} ({sig.setups_str}), {detail}")
                    slots -= 1
                    continue
                self.journal.set(f"plan:{sym}", json.dumps({"notional": size.notional, "stop": stop, "target": target,
                                                            "score": float(sig.score), "setups": sig.setups_str}))
                self.journal.twin_add(**twin, kind="pending", note="", shares=shares)
                try:
                    await b.place_short_bracket(sym, shares, size.notional, sig.ref_close * (1 - LOC_LIMIT_BELOW_LAST),
                                                stop, target, sig.setups_str, nlv)
                except ReadOnlyError:
                    note("would place", detail, size.notional)
                    self._twin_set_kind(today, sym, "shadow", "")
                    continue
                except Exception as exc:
                    note("error", f"order rejected: {type(exc).__name__}")
                    self._twin_set_kind(today, sym, "missed", "order rejected")
                    self._log("error", "order", f"Short {sym} failed: {type(exc).__name__}")
                    continue
                note("placed", detail, size.notional)
                self._log("info", "order", f"Short {shares:,.0f} {sym} ({sig.setups_str}) at the close, {detail}")
                slots -= 1
                open_syms.add(sym)
                summary["placed"] += 1
            await self._sync_fills()
            self.last_decision = summary
            if summary["placed"] or summary["exits"]:
                await self.notifier.send("Close orders sent",
                                         f"{summary['placed']} new shorts, {summary['exits']} day-3 exits")
            return summary

    # ----------------------------------------------------------------- after the close
    async def reconcile(self) -> dict:
        async with self.lock:
            b = self.broker
            today = b.today().isoformat()
            await self._sync_fills()
            acct = await b.account()
            shorts = [p for p in await b.positions() if p.shares < 0]
            orders = await b.open_orders()
            problems = []
            if not self.read_only:
                for p in shorts:
                    working = [o for o in orders if o.symbol == p.symbol and o.status not in ("Cancelled", "Filled")]
                    n_stop = sum(o.role == "stop" for o in working)
                    n_target = sum(o.role == "target" for o in working)
                    if n_stop != 1 or n_target != 1:
                        problems.append(f"{p.symbol}: {n_stop} stop / {n_target} target orders")
                journal_syms = {t["symbol"] for t in self.journal.open_trades()}
                for s in sorted({p.symbol for p in shorts} - journal_syms):
                    problems.append(f"{s}: position not opened by the bot")
            try:
                await self._update_twin(today)
            except Exception as exc:
                log.exception("end-of-day report update failed")
                problems.append(f"end-of-day report not updated ({type(exc).__name__})")
            _, realized_ytd = self._peak_and_ytd(today)
            nlv = acct.net_liquidation
            if math.isfinite(nlv):
                self.journal.record_equity(today, nlv, nlv - self.cfg.sizing.tax_rate * max(0.0, realized_ytd))
            self.journal.set("last_reconcile_day", today)
            for msg in problems:
                self._log("warn", "check", msg)
            if problems:
                await self.notifier.send("Check positions", "\n".join(problems), "high")
            if self.cfg.mode != "demo":
                prev = self.journal.last_equity_before(today)
                day_pnl = nlv - prev["nlv"] if prev and math.isfinite(nlv) else math.nan
                n_open = (len(self.journal.twin_rows(kinds=("shadow",), statuses=("waiting", "open")))
                          if self.read_only else len(shorts))
                text = f"Equity ${nlv:,.0f}, today ${day_pnl:+,.0f}, {n_open} open shorts"
                line = edge_report.summary_line(self.journal, self.cfg.mode)
                await self.notifier.send("Daily summary", text + (f"\n{line}" if line else ""))
                await self._verdict_alerts()
            self.problem = "; ".join(problems)
            return {"day": today, "problems": problems}

    # ----------------------------------------------------------------- end-of-day report
    async def _update_twin(self, today: str) -> None:
        """Move every backtest twin forward to today's close and store today's report snapshot."""
        j, b = self.journal, self.broker
        for r in j.twin_rows(kinds=("pending",)):
            if r["day"] <= today:  # fills were synced first, so this order never filled
                j.twin_update(r["id"], kind="missed", note="entry not filled")
        rows = j.twin_active()
        trades = j.trades_by_id()
        requests: dict[str, int] = {}
        for r in rows:
            if r["status"] == "waiting":
                days = 280  # the full history, to re-check the signal on the final bar
            else:
                last = min(d for d in (r["m_last_day"], r["a_last_day"], today) if d)
                days = b.trading_days_between(last, today) + 5
            requests[r["symbol"]] = max(requests.get(r["symbol"], 0), days)
        bars_by = await self._fetch_bars(requests) if requests else {}
        for r in rows:
            bars = bars_by.get(r["symbol"])
            if not bars:
                continue
            upd = await self._advance_twin(r, bars, today, trades.get(r["trade_id"]))
            if upd:
                j.twin_update(r["id"], **upd)
                if self.read_only and upd.get("status") == "closed" and r["kind"] == "shadow":
                    done = {**r, **upd}
                    self._log("info", "shadow", f"Shadow book: {r['symbol']} left at {done['m_exit']:.4g} "
                                                f"({done['m_reason']}), {edge_report.model_ret(done):+.1%}")
        snap = edge_report.snapshot(j.twin_rows(), j.trades_by_id(), j.commissions_by_trade(),
                                    lambda d: b.trading_days_between(d, today), self.cfg.hold_days,
                                    self.edge.sigma if self.edge is not None else edge_report.SIGMA_FALLBACK)
        if snap["n_open"] or snap["n_closed"] or j.edge_series(1):
            j.edge_upsert(today, snap["actual"], snap["theory"], snap["expected"], snap["var"], snap["missed"],
                          snap["n_open"], snap["n_closed"])

    async def _advance_twin(self, row: dict, bars: list, today: str, trade: dict | None) -> dict:
        tdb = self.broker.trading_days_between
        r, upd = dict(row), {}
        if r["status"] == "waiting":
            idx = next((i for i, x in enumerate(bars) if x.day[:10] == r["day"]), None)
            if idx is None or not _finite(bars[idx].close) or not r["shares"]:
                if tdb(r["day"], today) > 5:
                    upd = {"status": "void", "note": (r["note"] or "") + " (no price data)"}
                return upd
            first = bars[idx]
            e = edge_report.model_entry(first.close, first.high, self.engine_cfg)
            e.update(m_last_day=r["day"], status="open", close_ok=int(await self._still_signal(r["symbol"],
                                                                                              bars[:idx + 1])))
            if r["kind"] == "taken":
                e.update(a_mark=first.close, a_borrow=0.0, a_last_day=r["day"])
            r.update(e)
            upd.update(e)
        for bar in bars:  # the backtest's position management, one trading day at a time
            d = bar.day[:10]
            if r["status"] != "open":
                break
            if d <= r["m_last_day"] or d > today or not _finite(bar.close):
                continue
            step = edge_report.model_step(r, d, bar, tdb(r["day"], d), tdb(r["m_last_day"], d), self.engine_cfg)
            r.update(step)
            upd.update(step)
        if r["kind"] == "taken" and trade is not None and r["a_last_day"]:
            end = trade["exit_date"] if trade["status"] == "closed" else today
            for bar in bars:  # borrow the account pays (estimated) while the real short is open
                d = bar.day[:10]
                if d <= r["a_last_day"] or d > end or not _finite(bar.close):
                    continue
                r["a_borrow"] = (r["a_borrow"] or 0.0) + (tdb(r["a_last_day"], d) * trade["shares"] * r["a_mark"]
                                                          * (r["fee_rate"] or self.cfg.borrow_annual) / 252.0)
                r["a_last_day"] = d
                if trade["status"] == "open":
                    r["a_mark"] = bar.close
                upd.update(a_borrow=r["a_borrow"], a_last_day=d, a_mark=r["a_mark"])
            if trade["status"] == "closed" and today >= trade["exit_date"]:
                upd["a_done"] = 1
        return upd

    async def _still_signal(self, symbol: str, bars: list) -> bool:
        """Is it still a signal on the final daily bar? (The live decision used prices from 15 minutes earlier.)"""
        try:
            built = build_inputs(symbol, bars, await self.broker.gate_info(symbol, bars))
            return built is not None and evaluate_candidate(built[0], built[1], self._default_quote,
                                                            self.engine_cfg) is not None
        except Exception:
            return False

    async def _verdict_alerts(self) -> None:
        """Push an alert when the edge check or the execution check turns red (again only after it recovered)."""
        rep = edge_report.build_report(self.journal, self.edge, self.cfg.mode)
        for key, title in (("edge", "Edge check"), ("execution", "Execution check")):
            verdict = rep[key]["verdict"]
            prev = self.journal.get(f"verdict:{key}")
            if verdict == "bad" and prev != "bad":
                await self.notifier.send(title, rep[key]["text"], "high")
                self._log("warn", "report", f"{title}: {rep[key]['text']}")
                self.journal.set(f"verdict:{key}", "bad")
            elif verdict == "ok" or (prev is None and verdict != "bad"):
                self.journal.set(f"verdict:{key}", verdict)

    def report_view(self) -> dict:
        return edge_report.build_report(self.journal, self.edge, self.cfg.mode)

    # ----------------------------------------------------------------- phone actions
    async def pause(self) -> None:
        self.journal.set("paused", "1")
        self._log("info", "control", "Paused from the app: no new shorts (open positions keep their stops)")
        await self.notifier.send("Paused", "No new shorts until you resume")

    async def resume(self) -> None:
        self.journal.set("paused", "0")
        self._log("info", "control", "Resumed from the app")
        await self.notifier.send("Resumed", "New shorts allowed again")

    async def close_position(self, symbol: str) -> str:
        async with self.lock:
            pos = next((p for p in await self.broker.positions() if p.symbol == symbol and p.shares < 0), None)
            if pos is None:
                raise LookupError(symbol)
            how = self._manual_cover_type()
            await self._cover(symbol, pos.shares, how, "closed from the app")
            await self._sync_fills()
            return how

    async def flatten(self) -> int:
        async with self.lock:
            shorts = [p for p in await self.broker.positions() if p.shares < 0]
            how = self._manual_cover_type()
            for p in shorts:
                try:
                    await self._cover(p.symbol, p.shares, how, "flatten from the app")
                except Exception as exc:
                    self._log("error", "order", f"Flatten {p.symbol} failed: {type(exc).__name__}")
            self.journal.set("paused", "1")
            await self._sync_fills()
            self._log("info", "control", f"Flatten from the app: {len(shorts)} covers sent, bot paused")
            await self.notifier.send("Flatten", f"{len(shorts)} covers sent ({how}); bot paused", "high")
            return len(shorts)

    # ----------------------------------------------------------------- views for the app
    def _next_action(self) -> dict:
        if self.cfg.mode == "demo":
            return {"name": "next demo day", "at": "", "in_minutes": None}
        now = self.broker.now()
        d = now.date()
        for _ in range(10):
            if mc.is_trading_day(d):
                close = mc.close_time(d)
                decide = close - timedelta(minutes=self.cfg.decision_minutes_before_close)
                recon = close + timedelta(minutes=self.cfg.reconcile_minutes_after_close)
                for name, at in (("decision", decide), ("reconcile", recon)):
                    if at > now:
                        return {"name": name, "at": at.strftime("%a %H:%M ET"),
                                "in_minutes": int((at - now).total_seconds() // 60)}
            d = mc.next_trading_day(d)
        return {"name": "", "at": "", "in_minutes": None}

    async def status(self) -> dict:
        b = self.broker
        connected = b.is_connected()
        out = {"mode": self.cfg.mode, "connected": connected, "account": mask_account(getattr(b, "account_id", "")),
               "state": "paused" if self.paused and self.state == "running" else self.state,
               "problem": self.problem, "next": self._next_action(), "last_decision": self.last_decision,
               "max_positions": self.cfg.max_positions,
               "sizing": {"mode": self.cfg.sizing.mode, "static_pct": self.cfg.sizing.static_pct,
                          "kelly_mult": self.cfg.sizing.kelly_mult,
                          "profit_kelly_mult": self.cfg.sizing.profit_kelly_mult, "dd_limit": self.cfg.sizing.dd_limit}}
        if self.cfg.mode == "demo":
            out["demo"] = b.progress()
        if not connected:
            return out
        try:
            acct = await b.account()
            shorts = [p for p in await b.positions() if p.shares < 0]
        except Exception as exc:
            out["problem"] = f"broker error: {type(exc).__name__}"
            return out
        today = b.today().isoformat()
        nlv = acct.net_liquidation
        prev = self.journal.last_equity_before(today)
        peak_adj, realized_ytd = self._peak_and_ytd(today)
        adj = nlv - self.cfg.sizing.tax_rate * max(0.0, realized_ytd)
        peak = max(peak_adj or adj, adj)
        year_start = self._year_start_adj(today)
        out.update({
            "net_liquidation": nlv,
            "day_pnl": nlv - prev["nlv"] if prev else None,
            "drawdown_pct": (adj / peak - 1.0) * 100 if peak > 0 else None,
            "cushion_pct": max(0.0, adj - (1 - self.cfg.sizing.dd_limit) * peak) / nlv * 100 if nlv > 0 else None,
            "house_pct": (max(0.0, adj - year_start) / nlv * 100 if nlv > 0 and year_start is not None else None),
            "margin_use_pct": acct.maint_margin / nlv * 100 if nlv > 0 and math.isfinite(acct.maint_margin) else None,
            "positions": (len(self.journal.twin_rows(kinds=("shadow",), statuses=("waiting", "open")))
                          if self.read_only else len(shorts)),
            "date": today,
        })
        return out

    async def positions_view(self) -> list[dict]:
        b = self.broker
        today = b.today().isoformat()
        if self.read_only:
            return self._virtual_positions(today)
        trades = {t["symbol"]: t for t in self.journal.open_trades()}
        orders = await b.open_orders()
        out = []
        for p in await b.positions():
            if p.shares >= 0:
                continue
            t = trades.get(p.symbol, {})
            stop = next((o.stop_price for o in orders if o.symbol == p.symbol and o.role == "stop"), t.get("stop"))
            target = next((o.limit_price for o in orders if o.symbol == p.symbol and o.role == "target"),
                          t.get("target"))
            entry = t.get("entry_price") or p.avg_cost
            out.append({"symbol": p.symbol, "shares": abs(p.shares), "entry": entry, "last": p.market_price,
                        "pnl": p.unrealized_pnl,
                        "pnl_pct": (1 - p.market_price / entry) * 100 if entry else None,
                        "stop": stop, "target": target, "setups": t.get("setups", ""),
                        "day": b.trading_days_between(t["entry_date"], today) if t.get("entry_date") else None,
                        "hold_days": self.cfg.hold_days})
        return out

    def _virtual_positions(self, today: str) -> list[dict]:
        """Shadow mode: the virtual shorts, priced at the last close the bot recorded."""
        out = []
        for r in self.journal.twin_rows(kinds=("shadow",), statuses=("waiting", "open")):
            entry = r["m_entry"] or r["plan_price"]
            last = r["m_mark"] or r["plan_price"]
            priced = _finite(r["m_entry"])
            out.append({"symbol": r["symbol"], "shares": r["shares"], "entry": entry, "last": last,
                        "pnl": edge_report.model_pnl(r) if priced else None,
                        "pnl_pct": (1 - last / entry) * 100 if priced and entry else None,
                        "stop": r["m_stop"], "target": r["m_target"], "setups": r["setups"] or "",
                        "day": self.broker.trading_days_between(r["day"], today), "hold_days": self.cfg.hold_days,
                        "virtual": True})
        return out

    async def orders_view(self) -> list[dict]:
        return [{"symbol": o.symbol, "role": o.role, "action": o.action, "type": o.order_type, "qty": o.quantity,
                 "limit": o.limit_price, "stop": o.stop_price, "status": o.status}
                for o in await self.broker.open_orders()]

    def signals_view(self) -> dict:
        day = self.journal.last_signal_day()
        return {"day": day, "signals": self.journal.signals(day) if day else []}

    # ----------------------------------------------------------------- loops
    async def _heartbeat(self, ok: bool) -> None:
        if time.monotonic() - self._last_heartbeat >= HEARTBEAT_EVERY_S:
            self._last_heartbeat = time.monotonic()
            await self.notifier.heartbeat(ok)

    async def run(self) -> None:
        if self.cfg.mode == "demo":
            await self.run_demo()
            return
        backoff = 5
        warned_disconnect = False
        while not self._stop.is_set():
            try:
                if not self.broker.is_connected():
                    self.state = "connecting"
                    await self.broker.connect()
                    self._log("info", "connection", f"Connected to TWS ({self.cfg.mode})")
                    warned_disconnect = False
                    backoff = 5
                self.state = "running"
                now = self.broker.now()
                d = now.date()
                if mc.is_trading_day(d):
                    close = mc.close_time(d)
                    decide = close - timedelta(minutes=self.cfg.decision_minutes_before_close)
                    recon = close + timedelta(minutes=self.cfg.reconcile_minutes_after_close)
                    iso = d.isoformat()
                    if decide <= now < close - timedelta(minutes=6) and self.journal.get("last_decision_day") != iso:
                        await self.decision_cycle()
                    if now >= recon and self.journal.get("last_reconcile_day") != iso:
                        await self.reconcile()
                await self._heartbeat(True)
                await asyncio.wait_for(self._stop.wait(), timeout=15)
            except asyncio.TimeoutError:
                continue
            except (ConnectionError, OSError) as exc:
                self.state = "disconnected"
                self.problem = "cannot reach TWS"
                if not warned_disconnect:
                    self._log("warn", "connection", f"TWS connection problem: {type(exc).__name__}")
                    await self.notifier.send("TWS disconnected", "Retrying; check TWS on the laptop", "high")
                    warned_disconnect = True
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)
            except Exception as exc:
                self.state = "error"
                self.problem = f"{type(exc).__name__}"
                log.exception("service loop error")
                self.journal.event("error", "service", f"Unexpected error: {type(exc).__name__}")
                await self.notifier.send("Bot error", f"{type(exc).__name__}; retrying in a minute", "high")
                await asyncio.sleep(60)

    async def run_demo(self, seconds_per_day: float | None = None, loop: bool = True) -> None:
        sim = self.broker
        pace = self.cfg.demo_seconds_per_day if seconds_per_day is None else seconds_per_day
        self.journal.reset()
        self.state = "running"
        self._log("info", "demo", "Demo started: replaying history through the mock broker")
        while not self._stop.is_set():
            if sim.finished:
                if not loop:
                    break
                sim.reset()
                self.journal.reset()
                self._log("info", "demo", "Demo restarted from the beginning")
            sim.begin_day()
            # no new shorts on the last two days of data, where their exits could not be simulated
            await self.decision_cycle(allow_entries=sim.days_left() >= 2)
            sim.end_day()
            await self.reconcile()
            if pace > 0:
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=pace)
                except asyncio.TimeoutError:
                    pass
