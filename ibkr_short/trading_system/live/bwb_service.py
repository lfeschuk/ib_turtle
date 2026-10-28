"""Trading service for Strategy 2: Vol-Scaled 0DTE SPX Put Broken-Wing Butterfly (BWB) with Earned-Money Kelly Ramp."""
from __future__ import annotations

import asyncio
from datetime import datetime, time as dtime, timedelta
import json
import logging
import math
import time

from . import edge_report
from . import market_calendar as mc
from .broker import ReadOnlyError
from .bwb_strategy import (
    BwbFillResult,
    BwbPlan,
    BwbQuoteSnapshot,
    BwbSizeDecision,
    build_bwb_plan,
    compute_earned_kelly_fraction,
    effective_min_credit_pct,
    settle_bwb,
    size_bwb_bet,
    summarize_bwb_premium_audit,
)
from .config import LiveConfig
from .journal import Journal
from .notify import Notifier
from .service import HEARTBEAT_EVERY_S, mask_account

log = logging.getLogger(__name__)


class _BwbEdgeRef:
    """Reference edge distribution for the 0DTE Put BWB end-of-day report."""

    def __init__(self, delta_mid: float):
        is_15 = abs(delta_mid - 0.15) < 0.025
        self.mu = 0.01178 if is_15 else 0.01595
        self.sigma = 0.125 if is_15 else 0.145

    def expected(self, _score: float) -> float:
        return self.mu

    def rank(self, _score: float, ret: float) -> float:
        # Empirical rank of return-on-risk (win ~84% around +4% to +12%, tail losses down to -92%)
        z = (ret - self.mu) / max(self.sigma, 1e-6)
        return float(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))))

    def rank_drop_without_edge(self, mu: float) -> float:
        return min(0.25, max(0.02, mu / max(self.sigma, 1e-6) * 0.28))


class BwbBotService:
    """Independent service managing the $100k 0DTE SPX Put BWB strategy."""

    strategy_id = "bwb"
    strategy_name = "0DTE SPX Put BWB"

    def __init__(self, cfg: LiveConfig, broker, journal: Journal, notifier: Notifier, peer_service=None):
        self.cfg = cfg
        self.broker = broker
        self.journal = journal
        self.notifier = notifier
        self.peer_service = peer_service
        self.edge = _BwbEdgeRef(cfg.bwb.delta_mid)
        self.lock = asyncio.Lock()
        self.state = "starting"
        self.problem = ""
        self.last_decision: dict = {}
        self._last_heartbeat = 0.0
        self._stop = asyncio.Event()
        # Cached in-memory equity & HWM so long multi-year replays run in milliseconds
        self._eq_cache: float | None = None
        self._hwm_cache: float | None = None
        self._yr_anchor_cache: tuple[str, float] | None = None
        self._active_day: str | None = None
        self._active_plan: BwbPlan | None = None
        self._active_size: BwbSizeDecision | None = None
        self._active_quote: BwbQuoteSnapshot | None = None
        self._active_fill: BwbFillResult | None = None
        self._active_trade_id: int | None = None
        self._active_twin_id: int | None = None
        self._active_trade_key: str = ""

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

    def _current_equity_and_hwm(self) -> tuple[float, float]:
        if self._eq_cache is not None and self._hwm_cache is not None:
            return self._eq_cache, self._hwm_cache
        series = self.journal.equity(limit=10000)
        w0 = float(self.cfg.bwb.initial_capital)
        if not series:
            self._eq_cache = w0
            self._hwm_cache = w0
            return w0, w0
        eq = float(series[-1]["nlv"])
        hwm = max(w0, max(float(r["nlv"]) for r in series))
        self._eq_cache = eq
        self._hwm_cache = hwm
        return eq, hwm

    def _trade_key(self, plan: BwbPlan) -> str:
        return f"{plan.symbol} {plan.k_hi:.0f}/{plan.k_mid:.0f}/{plan.k_lo:.0f}P"

    def _year_start_anchor(self, today: str, current_eq: float) -> float:
        w0 = float(self.cfg.bwb.initial_capital)
        yr = today[:4]
        pin_day = self.journal.get("year_start_day")
        pin_adj = self.journal.get("year_start_adj")
        if pin_day and pin_adj and pin_day[:4] == yr:
            try:
                return max(w0, float(pin_adj))
            except ValueError:
                pass
        if self._yr_anchor_cache is not None and self._yr_anchor_cache[0] == yr:
            return self._yr_anchor_cache[1]
        first = self.journal.first_equity_since(f"{yr}-01-01")
        anchor = max(w0, float(first["adj"] if first and first.get("adj") else (first["nlv"] if first else current_eq)))
        self._yr_anchor_cache = (yr, anchor)
        return anchor

    async def _shared_state(self, today: str) -> tuple[float, float, float, float]:
        """Returns (equity, hwm, year_start_anchor, other_margin_used_pct) accounting for isolated vs shared capital."""
        eq, hwm = self._current_equity_and_hwm()
        other_m_pct = 0.0
        if not self.cfg.bwb.isolated_capital:
            if self.peer_service is not None:
                try:
                    gs_st = await self.peer_service.status()
                    gs_w0 = float(gs_st.get("initial_capital") or self.cfg.initial_capital)
                    gs_nlv = float(gs_st.get("net_liquidation") or gs_w0)
                    other_m_pct = max(0.0, float(gs_st.get("margin_use_pct") or 0.0) / 100.0)
                    # Add Gap Short's cumulative P&L onto the shared $100k capital pool (never raw IBKR $1M paper balance)
                    eq = max(1.0, eq + (gs_nlv - gs_w0))
                    hwm = max(hwm, eq)
                except Exception:
                    pass
        yr_anchor = self._year_start_anchor(today, eq)
        return eq, hwm, yr_anchor, other_m_pct

    # ----------------------------------------------------------------- morning 10:30 ET decision
    async def decision_cycle(self, allow_entries: bool = True) -> dict:
        async with self.lock:
            b = self.broker
            today = b.today().isoformat()
            self.journal.set("last_decision_day", today)

            snap = await b.market_snapshot()
            eq, hwm, yr_anchor, other_m_pct = await self._shared_state(today)
            plan = build_bwb_plan(snap, self.cfg.bwb, equity=eq)
            discrete = self.cfg.mode in ("paper", "live") and self.cfg.bwb.discrete_strikes
            size = size_bwb_bet(
                eq,
                hwm,
                plan,
                self.cfg.bwb,
                discrete_contracts=discrete,
                year_start_equity=yr_anchor,
                other_margin_used_pct=other_m_pct,
            )
            tkey = self._trade_key(plan)
            setup_label = f"{int(round(plan.delta_mid * 100))}Δ Put BWB ({plan.k_hi:.0f}/{plan.k_mid:.0f}/{plan.k_lo:.0f})"
            score = float(snap.vix_open - snap.iv1d_morning_pct)

            self._active_day = today
            self._active_plan = plan
            self._active_size = size
            self._active_quote = None
            self._active_fill = None
            self._active_trade_id = None
            self._active_twin_id = None
            self._active_trade_key = tkey

            min_floor_pct = effective_min_credit_pct(self.cfg.bwb, self.cfg.mode)
            min_floor_pts = min_floor_pct * plan.w_risk_pts

            bwb_meta = {
                "day": today,
                "symbol": plan.symbol,
                "trade_key": tkey,
                "spot_open": snap.spot_open,
                "iv1d_pct": snap.iv1d * 100.0,
                "vix_open": snap.vix_open,
                "vix_prev_close": snap.vix_prev_close,
                "vix1d_prev_close": snap.vix1d_prev_close,
                "f1_pass": snap.f1_pass,
                "f1_reason": snap.f1_reason,
                "delta_mid": plan.delta_mid,
                "k_hi": plan.k_hi,
                "k_mid": plan.k_mid,
                "k_lo": plan.k_lo,
                "k_be": plan.k_be,
                "w1_pts": plan.w1_pts,
                "w2_pts": plan.w2_pts,
                "w_risk_pts": plan.w_risk_pts,
                "mid_credit_pts": plan.mid_credit_pts,
                "net_credit_pts": plan.net_credit_pts,
                "min_credit_pts": min_floor_pts,
                "live_mid_pts": None,
                "est_net_pts": None,
                "actual_net_pts": None,
                "collat_fraction": size.collat_fraction,
                "collat_budget": size.collat_budget,
                "contracts": size.contracts,
                "house_cushion_dollars": size.house_cushion_dollars,
                "house_cushion_pct": size.house_cushion_pct,
                "ramp_progress_pct": size.ramp_progress_pct,
                "sizing_note": size.note,
            }
            self.journal.set("last_bwb_plan", json.dumps(bwb_meta))

            summary = {
                "day": today,
                "candidates": 1 if snap.f1_pass else 0,
                "placed": 0,
                "exits": 0,
                "f1_pass": snap.f1_pass,
                "collat_pct": round(size.collat_fraction * 100.0, 2),
                "note": snap.f1_reason,
            }

            if not allow_entries:
                summary["note"] = "entries off"
                self._active_plan = None
                self.last_decision = summary
                return summary

            if not snap.f1_pass:
                self.journal.record_signal(today, tkey, score, setup_label, "skipped", snap.f1_reason, 0.0)
                self._active_plan = None
                self.last_decision = summary
                return summary

            # Snapshot live 10:30 AM option quotes on the 3 BWB put strikes (read-only safe in shadow mode)
            quote = await b.quote_bwb_spread(plan)
            self._active_quote = quote
            bwb_meta["live_mid_pts"] = quote.live_mid_credit_pts
            bwb_meta["est_net_pts"] = quote.est_net_credit_pts
            self.journal.set("last_bwb_plan", json.dumps(bwb_meta))

            detail = (
                f"{size.collat_fraction:.2%} collat (${size.margin_dollars:,.0f}, {size.contracts:.2f}x), "
                f"model {plan.net_credit_pts:.2f}pt, live est {quote.est_net_credit_pts:.2f}pt "
                f"(mid {quote.live_mid_credit_pts:.2f}pt), BE {plan.k_be:.0f}, floor {plan.k_lo:.0f}"
            )

            if self.paused:
                self.journal.bwb_quote_upsert(
                    day=today,
                    symbol=plan.symbol,
                    trade_key=tkey,
                    delta_mid=plan.delta_mid,
                    w_risk_pts=quote.w_risk_pts,
                    contracts=size.contracts,
                    model_mid_pts=plan.mid_credit_pts,
                    model_net_pts=plan.net_credit_pts,
                    live_mid_pts=quote.live_mid_credit_pts,
                    est_net_pts=quote.est_net_credit_pts,
                    actual_gross_pts=None,
                    actual_net_pts=None,
                    commission_usd=0.0,
                    quote_source=quote.source,
                    action="paused",
                    note="paused",
                )
                self.journal.record_signal(
                    today, tkey, score, setup_label, "skipped", "paused (tracked for the edge check)", size.margin_dollars
                )
                self.journal.twin_add(
                    day=today,
                    symbol=tkey,
                    setups=setup_label,
                    score=score,
                    kind="missed",
                    note="paused",
                    exp_ret=plan.expected_ret_on_risk,
                    shares=size.contracts,
                    plan_price=plan.margin_per_contract,
                    fee_rate=0.0,
                )
                summary["note"] = "paused: no new BWB"
                self.last_decision = summary
                return summary

            if self.read_only:
                below_floor = min_floor_pts > 0.0 and quote.est_net_credit_pts < min_floor_pts - 1e-9
                act_lbl = "skipped_low_credit" if below_floor else "would_place"
                note_lbl = (
                    f"shadow est {quote.est_net_credit_pts:.2f}pt < min floor {min_floor_pts:.2f}pt"
                    if below_floor
                    else "shadow"
                )
                self.journal.bwb_quote_upsert(
                    day=today,
                    symbol=plan.symbol,
                    trade_key=tkey,
                    delta_mid=plan.delta_mid,
                    w_risk_pts=quote.w_risk_pts,
                    contracts=size.contracts,
                    model_mid_pts=plan.mid_credit_pts,
                    model_net_pts=plan.net_credit_pts,
                    live_mid_pts=quote.live_mid_credit_pts,
                    est_net_pts=quote.est_net_credit_pts,
                    actual_gross_pts=None,
                    actual_net_pts=None,
                    commission_usd=0.0,
                    quote_source=quote.source,
                    action=act_lbl,
                    note=note_lbl,
                )
                self.journal.record_signal(
                    today,
                    tkey,
                    score,
                    setup_label,
                    "skipped" if below_floor else "would place",
                    note_lbl if below_floor else detail,
                    0.0 if below_floor else size.margin_dollars,
                )
                self.journal.twin_add(
                    day=today,
                    symbol=tkey,
                    setups=setup_label,
                    score=score,
                    kind="missed" if below_floor else "shadow",
                    note="below min credit floor" if below_floor else "",
                    exp_ret=plan.expected_ret_on_risk,
                    shares=size.contracts,
                    plan_price=plan.margin_per_contract,
                    fee_rate=0.0,
                )
                self._log("info", "shadow", f"Shadow {tkey}: {note_lbl if below_floor else detail}")
                self.last_decision = summary
                return summary

            if min_floor_pts > 0.0 and quote.est_net_credit_pts < min_floor_pts - 1e-9:
                skip_msg = (
                    f"live est credit {quote.est_net_credit_pts:.2f}pt ({quote.est_net_credit_pts / quote.w_risk_pts:.2%}) "
                    f"< min positive-edge floor {min_floor_pts:.2f}pt ({min_floor_pct:.2%})"
                )
                self.journal.bwb_quote_upsert(
                    day=today,
                    symbol=plan.symbol,
                    trade_key=tkey,
                    delta_mid=plan.delta_mid,
                    w_risk_pts=quote.w_risk_pts,
                    contracts=size.contracts,
                    model_mid_pts=plan.mid_credit_pts,
                    model_net_pts=plan.net_credit_pts,
                    live_mid_pts=quote.live_mid_credit_pts,
                    est_net_pts=quote.est_net_credit_pts,
                    actual_gross_pts=None,
                    actual_net_pts=None,
                    commission_usd=0.0,
                    quote_source=quote.source,
                    action="skipped_low_credit",
                    note=skip_msg,
                )
                self.journal.record_signal(today, tkey, score, setup_label, "skipped", skip_msg, 0.0)
                self.journal.twin_add(
                    day=today,
                    symbol=tkey,
                    setups=setup_label,
                    score=score,
                    kind="missed",
                    note="below min credit floor",
                    exp_ret=plan.expected_ret_on_risk,
                    shares=size.contracts,
                    plan_price=plan.margin_per_contract,
                    fee_rate=0.0,
                )
                self._log("warn", "credit_gate", f"Skipped {tkey}: {skip_msg}")
                summary["note"] = "skipped: below min credit floor"
                self.last_decision = summary
                return summary

            try:
                fill = await b.place_bwb_spread(
                    plan, size.contracts, tkey, quote=quote, min_credit_pts=min_floor_pts
                )
            except ReadOnlyError:
                self.journal.record_signal(today, tkey, score, setup_label, "would place", detail, size.margin_dollars)
                self.last_decision = summary
                return summary
            except Exception as exc:
                self.journal.record_signal(
                    today, tkey, score, setup_label, "error", f"order rejected: {type(exc).__name__}", 0.0
                )
                self._log("error", "order", f"BWB order {tkey} failed: {type(exc).__name__}")
                self._active_plan = None
                self.last_decision = summary
                return summary

            if not fill.filled or fill.contracts <= 0.0:
                act_code = "skipped_low_credit" if "floor" in fill.status.lower() else "unfilled_cancelled"
                self.journal.bwb_quote_upsert(
                    day=today,
                    symbol=plan.symbol,
                    trade_key=tkey,
                    delta_mid=plan.delta_mid,
                    w_risk_pts=quote.w_risk_pts,
                    contracts=size.contracts,
                    model_mid_pts=plan.mid_credit_pts,
                    model_net_pts=plan.net_credit_pts,
                    live_mid_pts=quote.live_mid_credit_pts,
                    est_net_pts=quote.est_net_credit_pts,
                    actual_gross_pts=None,
                    actual_net_pts=None,
                    commission_usd=0.0,
                    quote_source=quote.source,
                    action=act_code,
                    note=fill.status,
                )
                self.journal.record_signal(today, tkey, score, setup_label, "skipped", fill.status, 0.0)
                self.journal.twin_add(
                    day=today,
                    symbol=tkey,
                    setups=setup_label,
                    score=score,
                    kind="missed",
                    note="below min credit floor" if act_code == "skipped_low_credit" else "unfilled at 10:30",
                    exp_ret=plan.expected_ret_on_risk,
                    shares=size.contracts,
                    plan_price=plan.margin_per_contract,
                    fee_rate=0.0,
                )
                self._log("warn", "order", f"{tkey} not entered: {fill.status}")
                summary["note"] = fill.status
                self.last_decision = summary
                return summary

            self._active_fill = fill
            actual_contracts = fill.contracts
            actual_margin = actual_contracts * plan.margin_per_contract
            bwb_meta["actual_net_pts"] = fill.net_credit_pts
            bwb_meta["actual_gross_pts"] = fill.gross_credit_pts
            bwb_meta["contracts"] = actual_contracts
            bwb_meta["collat_budget"] = actual_margin
            self.journal.set("last_bwb_plan", json.dumps(bwb_meta))

            self.journal.bwb_quote_upsert(
                day=today,
                symbol=plan.symbol,
                trade_key=tkey,
                delta_mid=plan.delta_mid,
                w_risk_pts=quote.w_risk_pts,
                contracts=actual_contracts,
                model_mid_pts=plan.mid_credit_pts,
                model_net_pts=plan.net_credit_pts,
                live_mid_pts=quote.live_mid_credit_pts,
                est_net_pts=quote.est_net_credit_pts,
                actual_gross_pts=fill.gross_credit_pts,
                actual_net_pts=fill.net_credit_pts,
                commission_usd=fill.commission_dollars,
                quote_source=quote.source,
                action="placed",
                note=fill.status,
            )

            filled_detail = (
                f"{size.collat_fraction:.2%} collat (${actual_margin:,.0f}, {actual_contracts:.2f}x), "
                f"filled net {fill.net_credit_pts:.2f}pt vs model {plan.net_credit_pts:.2f}pt "
                f"(live mid {quote.live_mid_credit_pts:.2f}pt), BE {plan.k_be:.0f}"
            )

            # Record entry in trades and twin tables using margin_per_contract as unit notional
            trade_id, _, _ = self.journal.record_entry_fill(
                symbol=tkey,
                day=today,
                price=plan.margin_per_contract,
                shares=actual_contracts,
                plan={
                    "notional": actual_margin,
                    "stop": plan.k_lo,
                    "target": plan.k_mid,
                    "score": score,
                    "setups": setup_label,
                },
            )
            self._active_trade_id = trade_id
            self.journal.record_fill(
                exec_id=f"bwb-entry-{today}",
                symbol=tkey,
                side="SELL",
                shares=actual_contracts,
                price=plan.margin_per_contract,
                day=today,
                role="entry",
                commission=0.0,
                trade_id=trade_id,
            )
            self.journal.twin_add(
                day=today,
                symbol=tkey,
                setups=setup_label,
                score=score,
                kind="taken",
                note="",
                exp_ret=plan.expected_ret_on_risk,
                shares=actual_contracts,
                plan_price=plan.margin_per_contract,
                fee_rate=0.0,
            )
            self.journal.twin_link_fill(today, tkey, trade_id, actual_contracts)
            self.journal.record_signal(today, tkey, score, setup_label, "placed", filled_detail, actual_margin)
            summary["placed"] = 1
            self.last_decision = summary
            return summary

    # ----------------------------------------------------------------- 16:15 ET cash-settlement reconciliation
    async def reconcile(self) -> dict:
        async with self.lock:
            b = self.broker
            today = b.today().isoformat()
            snap = await b.market_snapshot()
            prev_eq, hwm = self._current_equity_and_hwm()

            cash_interest = prev_eq * snap.rf_daily
            option_pnl = 0.0
            settlement = None

            if self._active_day != today or self._active_plan is None:
                # Recover intraday state if service restarted between 10:30 AM and 16:15 ET
                raw_meta = self.journal.get("last_bwb_plan")
                meta = json.loads(raw_meta) if raw_meta else {}
                open_tr = [t for t in self.journal.open_trades() if t["entry_date"] == today]
                if meta.get("day") == today and meta.get("f1_pass"):
                    self._active_day = today
                    self._active_plan = build_bwb_plan(snap, self.cfg.bwb, equity=prev_eq)
                    self._active_trade_key = meta.get("trade_key") or self._trade_key(self._active_plan)
                    ct = float(open_tr[0]["shares"]) if open_tr else float(meta.get("contracts") or 0.0)
                    self._active_size = BwbSizeDecision(
                        collat_fraction=float(meta.get("collat_fraction") or 0.075),
                        collat_budget=ct * self._active_plan.margin_per_contract,
                        contracts=ct,
                        margin_dollars=ct * self._active_plan.margin_per_contract,
                        house_cushion_dollars=float(meta.get("house_cushion_dollars") or 0.0),
                        house_cushion_pct=float(meta.get("house_cushion_pct") or 0.0),
                        ramp_progress_pct=float(meta.get("ramp_progress_pct") or 0.0),
                        sizing_mode=self.cfg.bwb.sizing_mode,
                        note=str(meta.get("sizing_note") or ""),
                    )
                    if open_tr and meta.get("actual_net_pts") is not None:
                        self._active_trade_id = int(open_tr[0]["id"])
                        self._active_fill = BwbFillResult(
                            filled=True,
                            contracts=ct,
                            gross_credit_pts=float(meta.get("actual_gross_pts") or meta["actual_net_pts"]),
                            commission_dollars=0.0,
                            net_credit_pts=float(meta["actual_net_pts"]),
                            limit_credit_pts=float(meta.get("actual_gross_pts") or meta["actual_net_pts"]),
                            order_id=0,
                            status="Recovered",
                        )

            if self._active_day == today and self._active_plan is not None and self._active_size is not None:
                plan = self._active_plan
                size = self._active_size
                tkey = self._active_trade_key
                close_spot = snap.spot_close if snap.spot_close is not None else snap.spot_mark

                actual_contracts = self._active_fill.contracts if self._active_fill is not None else size.contracts
                actual_net_pts = (
                    self._active_fill.net_credit_pts if self._active_fill is not None else plan.net_credit_pts
                )
                comm_usd = self._active_fill.commission_dollars if self._active_fill is not None else 0.0

                # Refresh late-arriving IBKR commissions if present on fills_today()
                if self._active_fill is not None and self.cfg.mode in ("paper", "live"):
                    try:
                        todays_fills = await b.fills_today()
                        late_comm = sum(f.commission for f in todays_fills if f.role == "entry" and f.commission > 0)
                        if late_comm > 0.0 and abs(late_comm - comm_usd) > 1e-6 and actual_contracts > 0:
                            comm_usd = late_comm
                            actual_net_pts = self._active_fill.gross_credit_pts - (
                                comm_usd / (plan.multiplier * actual_contracts)
                            )
                    except Exception:
                        pass

                settlement = settle_bwb(
                    plan, close_spot, actual_contracts, override_net_credit_pts=actual_net_pts
                )
                twin_plan = build_bwb_plan(snap, self.cfg.bwb, equity=prev_eq, force_continuous=True)
                twin_settle = settle_bwb(twin_plan, close_spot, actual_contracts)

                scale = 0.1 if plan.symbol == "XSP" and close_spot > 1000.0 else 1.0
                breached_be = int((float(close_spot) * scale) < plan.k_be)
                self.journal.bwb_quote_settle(
                    day=today,
                    close_spot=settlement.close_spot,
                    payoff_pts=settlement.payoff_pts,
                    settle_fee_pts=settlement.settle_fee_pts,
                    actual_ret_on_risk=settlement.ret_on_risk,
                    model_ret_on_risk=twin_settle.ret_on_risk,
                    zone=settlement.zone,
                    breached_be=breached_be,
                    actual_net_pts=actual_net_pts if self._active_trade_id is not None else None,
                    commission_usd=comm_usd if self._active_trade_id is not None else None,
                )

                if self._active_trade_id is not None:
                    option_pnl = settlement.pnl_dollars
                    exit_price = plan.margin_per_contract - (settlement.net_pnl_pts * plan.multiplier)
                    reason = f"4pm cash settle ({settlement.zone}, SPX {settlement.close_spot:.1f})"
                    self.journal.record_exit_fill(tkey, today, exit_price, actual_contracts, reason)
                    self.journal.record_fill(
                        exec_id=f"bwb-settle-{today}",
                        symbol=tkey,
                        side="BUY",
                        shares=actual_contracts,
                        price=exit_price,
                        day=today,
                        role="exit",
                        commission=0.0,
                        trade_id=self._active_trade_id,
                    )

                # Update today's twin row so the Actual vs Backtest Twin vs Expected Edge report stays current
                m_entry = twin_plan.margin_per_contract
                m_exit = m_entry - (twin_settle.net_pnl_pts * twin_plan.multiplier)
                for r in self.journal.twin_rows(day=today):
                    if r["symbol"] == tkey:
                        self.journal.twin_update(
                            r["id"],
                            status="closed",
                            close_ok=1,
                            m_close=snap.spot_open,
                            m_entry=m_entry,
                            m_stop=twin_plan.k_lo,
                            m_target=twin_plan.k_mid,
                            m_mark=m_exit,
                            m_borrow=0.0,
                            m_last_day=today,
                            m_exit_day=today,
                            m_exit=m_exit,
                            m_reason=twin_settle.zone,
                            a_mark=m_exit,
                            a_borrow=0.0,
                            a_last_day=today,
                            a_done=1,
                        )

            new_eq = prev_eq + cash_interest + option_pnl
            new_hwm = max(hwm, new_eq)
            self._eq_cache = new_eq
            self._hwm_cache = new_hwm

            year_start = f"{today[:4]}-01-01"
            first_yr = self.journal.first_equity_since(year_start)
            yr_base = float(first_yr["nlv"]) if first_yr else float(self.cfg.bwb.initial_capital)
            ytd_gain = max(0.0, new_eq - yr_base)
            adj_eq = new_eq - self.cfg.sizing.tax_rate * ytd_gain
            self.journal.record_equity(today, new_eq, adj_eq)
            self.journal.set("last_reconcile_day", today)

            # Update cumulative edge_daily snapshot in O(1) time when a signal occurred today
            if settlement is not None and self._active_plan is not None and self._active_size is not None:
                prev_edges = self.journal.edge_series(limit=1)
                p_edge = prev_edges[-1] if prev_edges else {
                    "actual": 0.0, "theory": 0.0, "expected": 0.0, "var": 0.0, "missed": 0.0, "n_closed": 0
                }
                notional_d = actual_contracts * twin_plan.margin_per_contract
                missed_today = self.paused or (not self.read_only and self._active_trade_id is None)
                if missed_today:
                    self.journal.edge_upsert(
                        today,
                        p_edge["actual"],
                        float(p_edge["theory"]),
                        float(p_edge["expected"]),
                        float(p_edge["var"]),
                        float(p_edge["missed"]) + twin_settle.pnl_dollars,
                        0,
                        int(p_edge["n_closed"] or 0),
                    )
                else:
                    act_prev = float(p_edge["actual"] or 0.0)
                    new_actual = None if self.read_only else (act_prev + settlement.pnl_dollars)
                    self.journal.edge_upsert(
                        today,
                        new_actual,
                        float(p_edge["theory"]) + twin_settle.pnl_dollars,
                        float(p_edge["expected"]) + twin_plan.expected_ret_on_risk * notional_d,
                        float(p_edge["var"]) + (self.edge.sigma * notional_d) ** 2,
                        float(p_edge["missed"]),
                        0,
                        int(p_edge["n_closed"] or 0) + 1,
                    )

            self._active_plan = None
            self._active_size = None
            self._active_quote = None
            self._active_fill = None
            self._active_trade_id = None
            return {
                "day": today,
                "nlv": new_eq,
                "cash_interest": cash_interest,
                "option_pnl": option_pnl,
                "problems": [],
            }

    # ----------------------------------------------------------------- phone actions
    async def pause(self) -> None:
        self.journal.set("paused", "1")
        self._log("info", "control", "0DTE BWB paused from the app: no new spreads")
        await self.notifier.send("0DTE BWB Paused", "No new 0DTE BWB spreads until you resume")

    async def resume(self) -> None:
        self.journal.set("paused", "0")
        self._log("info", "control", "0DTE BWB resumed from the app")
        await self.notifier.send("0DTE BWB Resumed", "Daily 0DTE BWB entries allowed again")

    async def close_position(self, symbol: str) -> str:
        async with self.lock:
            await self.broker.close_spread(symbol, how="MKT")
            if self._active_trade_id is not None and self._active_plan is not None and self._active_size is not None:
                today = self.broker.today().isoformat()
                self.journal.record_exit_fill(
                    self._active_trade_key,
                    today,
                    self._active_plan.margin_per_contract,
                    self._active_size.contracts,
                    "manual close",
                )
                self._active_plan = None
                self._active_trade_id = None
            self._log("info", "control", f"Closed {symbol} from the app (MKT)")
            return "MKT"

    async def flatten(self) -> int:
        async with self.lock:
            positions = await self.broker.positions()
            n = 0
            for p in positions:
                try:
                    await self.broker.close_spread(p.symbol, how="MKT")
                    n += 1
                except Exception as exc:
                    self._log("error", "order", f"Flatten {p.symbol} failed: {type(exc).__name__}")
            if self._active_trade_id is not None and self._active_plan is not None and self._active_size is not None:
                today = self.broker.today().isoformat()
                self.journal.record_exit_fill(
                    self._active_trade_key,
                    today,
                    self._active_plan.margin_per_contract,
                    self._active_size.contracts,
                    "flatten from the app",
                )
                self._active_plan = None
                self._active_trade_id = None
            self.journal.set("paused", "1")
            self._log("info", "control", f"0DTE BWB flatten: {n} spread(s) closed, bot paused")
            return n

    # ----------------------------------------------------------------- views for the app
    def _next_action(self) -> dict:
        if self.cfg.mode == "demo":
            return {"name": "next demo day", "at": "", "in_minutes": None}
        now = self.broker.now()
        d = now.date()
        for _ in range(10):
            if mc.is_trading_day(d):
                open_dt = datetime.combine(d, dtime(9, 30), tzinfo=mc.NY)
                decide = open_dt + timedelta(minutes=self.cfg.bwb.entry_minutes_after_open)
                close = mc.close_time(d)
                recon = close + timedelta(minutes=self.cfg.reconcile_minutes_after_close)
                for name, at in (("10:30 BWB entry", decide), ("4pm settle check", recon)):
                    if at > now:
                        return {
                            "name": name,
                            "at": at.strftime("%a %H:%M ET"),
                            "in_minutes": int((at - now).total_seconds() // 60),
                        }
            d = mc.next_trading_day(d)
        return {"name": "", "at": "", "in_minutes": None}

    async def status(self) -> dict:
        b = self.broker
        connected = b.is_connected()
        today = b.today().isoformat() if connected else "2026-01-01"
        eq, hwm, yr_anchor, other_m_pct = await self._shared_state(today)
        w0 = yr_anchor if self.cfg.bwb.sizing_mode == "yearly_house" else float(self.cfg.bwb.initial_capital)
        f_raw = compute_earned_kelly_fraction(
            eq, self.cfg.bwb.initial_capital, hwm, self.cfg.bwb, year_start_equity=yr_anchor
        )
        if not self.cfg.bwb.isolated_capital or other_m_pct > 0.0:
            f_t = min(f_raw, max(0.0, float(self.cfg.bwb.max_combined_margin_pct) - other_m_pct))
        else:
            f_t = f_raw
        house_dollars = max(0.0, eq - w0)
        house_pct = (house_dollars / w0) * 100.0 if w0 > 0 else 0.0
        span = max(1e-9, self.cfg.bwb.max_collat_pct - self.cfg.bwb.base_collat_pct)
        ramp_pct = float(min(100.0, max(0.0, (f_t - self.cfg.bwb.base_collat_pct) / span * 100.0)))

        raw_plan = self.journal.get("last_bwb_plan")
        bwb_plan = json.loads(raw_plan) if raw_plan else None

        out = {
            "strategy": "bwb",
            "strategy_name": self.strategy_name,
            "initial_capital": float(self.cfg.bwb.initial_capital),
            "isolated_capital": self.cfg.bwb.isolated_capital,
            "year_start_anchor": yr_anchor,
            "other_margin_used_pct": other_m_pct * 100.0,
            "mode": self.cfg.mode,
            "connected": connected,
            "account": mask_account(getattr(b, "account_id", "")),
            "state": "paused" if self.paused and self.state == "running" else self.state,
            "problem": self.problem,
            "next": self._next_action(),
            "last_decision": self.last_decision,
            "max_positions": 1,
            "sizing": {
                "mode": self.cfg.bwb.sizing_mode,
                "delta_mid": self.cfg.bwb.delta_mid,
                "base_collat_pct": self.cfg.bwb.base_collat_pct,
                "max_collat_pct": self.cfg.bwb.max_collat_pct,
                "current_collat_pct": f_t,
                "house_cushion_dollars": house_dollars,
                "house_cushion_pct": house_pct,
                "ramp_progress_pct": ramp_pct,
            },
            "bwb_plan": bwb_plan,
        }
        if self.cfg.mode == "demo" and hasattr(b, "progress"):
            out["demo"] = b.progress()
        if not connected:
            return out

        today = b.today().isoformat()
        prev = self.journal.last_equity_before(today)
        positions = await b.positions()
        maint = sum(abs(p.shares) * (bwb_plan["w_risk_pts"] * 100.0 if bwb_plan else 0.0) for p in positions)
        out.update(
            {
                "net_liquidation": eq,
                "day_pnl": eq - float(prev["nlv"]) if prev else 0.0,
                "drawdown_pct": (eq / hwm - 1.0) * 100.0 if hwm > 0 else 0.0,
                "initial_dd_pct": min(0.0, (eq / float(self.cfg.bwb.initial_capital) - 1.0) * 100.0),
                "total_return_pct": (eq / float(self.cfg.bwb.initial_capital) - 1.0) * 100.0,
                "cushion_pct": house_pct,
                "house_pct": house_pct,
                "collat_pct": f_t * 100.0,
                "ramp_progress_pct": ramp_pct,
                "margin_use_pct": (maint / eq * 100.0) if eq > 0 else 0.0,
                "positions": len(positions),
                "date": today,
            }
        )
        return out

    async def positions_view(self) -> list[dict]:
        b = self.broker
        raw_plan = self.journal.get("last_bwb_plan")
        meta = json.loads(raw_plan) if raw_plan else {}
        out = []
        for p in await b.positions():
            out.append(
                {
                    "symbol": p.symbol,
                    "shares": abs(p.shares),
                    "entry": p.avg_cost,
                    "last": p.market_price,
                    "pnl": p.unrealized_pnl,
                    "pnl_pct": 0.0,
                    "stop": meta.get("k_lo"),
                    "target": meta.get("k_mid"),
                    "setups": f"{int(round(meta.get('delta_mid', 0.20) * 100))}Δ Put BWB (BE {meta.get('k_be', 0):.0f})",
                    "day": 0,
                    "hold_days": 1,
                }
            )
        return out

    async def orders_view(self) -> list[dict]:
        return [
            {
                "symbol": o.symbol,
                "role": o.role,
                "action": o.action,
                "type": o.order_type,
                "qty": o.quantity,
                "limit": o.limit_price,
                "stop": o.stop_price,
                "status": o.status,
            }
            for o in await self.broker.open_orders()
        ]

    def signals_view(self) -> dict:
        day = self.journal.last_signal_day()
        return {"day": day, "signals": self.journal.signals(day) if day else []}

    def report_view(self) -> dict:
        rep = edge_report.build_report(self.journal, self.edge, self.cfg.mode)
        rep["bwb_audit"] = summarize_bwb_premium_audit(
            self.journal.bwb_quote_rows(limit=2500),
            self.cfg.bwb.delta_mid,
            self.cfg.bwb.max_collat_pct,
            self.cfg.mode,
        )
        return rep

    # ----------------------------------------------------------------- runtime loops
    async def _heartbeat(self, ok: bool) -> None:
        if time.monotonic() - self._last_heartbeat >= HEARTBEAT_EVERY_S:
            self._last_heartbeat = time.monotonic()
            await self.notifier.heartbeat(ok)

    async def run(self) -> None:
        if self.cfg.mode == "demo":
            await self.run_demo()
            return
        backoff = 5
        while not self._stop.is_set():
            try:
                if not self.broker.is_connected():
                    self.state = "connecting"
                    await self.broker.connect()
                    self._log("info", "connection", f"0DTE BWB connected to TWS ({self.cfg.mode})")
                    backoff = 5
                self.state = "running"
                now = self.broker.now()
                d = now.date()
                if mc.is_trading_day(d):
                    open_dt = now.replace(hour=9, minute=30, second=0, microsecond=0)
                    decide = open_dt + timedelta(minutes=self.cfg.bwb.entry_minutes_after_open)
                    close = mc.close_time(d)
                    recon = close + timedelta(minutes=self.cfg.reconcile_minutes_after_close)
                    iso = d.isoformat()
                    if decide <= now < close - timedelta(minutes=30) and self.journal.get("last_decision_day") != iso:
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
                self._log("warn", "connection", f"0DTE BWB TWS connection problem: {type(exc).__name__}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)
            except Exception as exc:
                self.state = "error"
                self.problem = f"{type(exc).__name__}"
                log.exception("BWB service loop error")
                await asyncio.sleep(60)

    async def run_demo(self, seconds_per_day: float | None = None, loop: bool = True) -> None:
        sim = self.broker
        pace = self.cfg.demo_seconds_per_day if seconds_per_day is None else seconds_per_day
        self.journal.reset()
        self._eq_cache = None
        self._hwm_cache = None
        self._yr_anchor_cache = None
        self.state = "running"
        self._log("info", "demo", "0DTE Put BWB demo started: replaying historical SPX/VIX1D data")
        while not self._stop.is_set():
            if sim.finished:
                if not loop:
                    break
                sim.reset()
                self.journal.reset()
                self._eq_cache = None
                self._hwm_cache = None
                self._yr_anchor_cache = None
                self._log("info", "demo", "0DTE Put BWB demo restarted from the beginning")
            sim.begin_day()
            await self.decision_cycle(allow_entries=True)
            sim.end_day()
            await self.reconcile()
            if pace > 0:
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=pace)
                except asyncio.TimeoutError:
                    pass
