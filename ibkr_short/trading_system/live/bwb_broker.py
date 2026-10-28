"""IBKR TWS / Gateway and Historical Replay brokers for the 0DTE SPX Put BWB strategy."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time as dtime
from functools import lru_cache
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import market_calendar as mc
from .broker import AccountInfo, FillInfo, OrderInfo, PositionInfo, ReadOnlyError
from .bwb_strategy import (
    BwbFillResult,
    BwbMarketSnapshot,
    BwbPlan,
    BwbQuoteSnapshot,
    BwbSettlement,
    T_0DTE,
    SQRT_T_0DTE,
    bs_price_0dte,
    half_spread_pts,
    iv_ratio_0dte,
    settle_bwb,
)
from .config import LiveConfig

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRATCH_ROOT = _REPO_ROOT.parent
DEFAULT_PANEL_PATHS = (
    _SCRATCH_ROOT / "spx_0dte_study" / "out" / "daily_panel.pkl",
    _REPO_ROOT / "data" / "bwb_daily_panel.pkl",
)
DEFAULT_SPY_CSV = _SCRATCH_ROOT / "spx_0dte_study" / "data" / "yf_SPY_1d.csv"


@dataclass
class OpenBwbSpread:
    trade_key: str
    symbol: str
    day: str
    plan: BwbPlan
    contracts: float
    entry_credit_pts: float
    margin_dollars: float
    mark_pnl_dollars: float = 0.0


@lru_cache(maxsize=2)
def load_clean_bwb_panel(custom_path: str = "") -> pd.DataFrame:
    """Loads and prepares the causal 0DTE SPX/VIX/VIX1D daily panel matching the research backtest."""
    candidates = ([Path(custom_path).expanduser()] if custom_path else []) + list(DEFAULT_PANEL_PATHS)
    panel_path = next((p for p in candidates if p.exists()), None)
    if panel_path is None:
        raise FileNotFoundError("Could not locate daily_panel.pkl for 0DTE BWB historical replay")

    df = pd.read_pickle(panel_path).copy()
    is_pre_vix1d = df.index < pd.Timestamp("2022-05-16")
    v9d_o = df["vix9d_o"].values
    vix_o = pd.Series(df["vix_o"].values, index=df.index).ffill().bfill().values
    iv1d_clean_pct = np.where(
        is_pre_vix1d,
        np.where(np.isfinite(v9d_o) & (v9d_o > 0), 0.6639 * v9d_o, 0.6392 * vix_o),
        df["iv1d_morning_causal"].values,
    )
    iv1d_clean_pct = pd.Series(iv1d_clean_pct, index=df.index).ffill().bfill().values
    df["iv1d_clean_pct"] = iv1d_clean_pct
    df["iv1d_clean"] = np.clip(iv1d_clean_pct / 100.0, 0.04, 1.50)
    df["vix_o_clean"] = vix_o

    has_v9d = (
        np.isfinite(df["vix9d_prev_c"].values)
        & (df["vix9d_prev_c"].values > 0)
        & np.isfinite(df["vix9d_o"].values)
        & (df["vix9d_o"].values > 0)
    )
    v3m_prev = df["vix3m_prev_c"].values if "vix3m_prev_c" in df.columns else np.full(len(df), np.nan)
    v3m_o = df["vix3m_o"].values if "vix3m_o" in df.columns else np.full(len(df), np.nan)
    has_v3m = np.isfinite(v3m_prev) & (v3m_prev > 0) & np.isfinite(v3m_o) & (v3m_o > 0)

    vix_prev = pd.Series(df["vix_prev_c"].values, index=df.index).ffill().bfill().values
    df["vix_prev_clean"] = vix_prev
    vix_sma20 = pd.Series(vix_prev, index=df.index).rolling(20, min_periods=5).mean().values
    f1_pre2011 = np.where(
        has_v3m,
        (vix_prev < v3m_prev) & (vix_o < v3m_o),
        (vix_prev < vix_sma20 * 1.03) & (vix_o < vix_prev * 1.02),
    )

    f1_clean = np.where(
        ~is_pre_vix1d,
        (df["vix1d_prev_c"].values < df["vix_prev_c"].values) & (df["iv1d_morning_causal"].values < df["vix_o"].values),
        np.where(
            has_v9d,
            (df["vix9d_prev_c"].values < df["vix_prev_c"].values) & (df["vix9d_o"].values < df["vix_o"].values),
            f1_pre2011,
        ),
    )
    df["f1_clean"] = f1_clean.astype(bool)
    df["vix1d_prev_clean"] = np.where(
        ~is_pre_vix1d,
        df["vix1d_prev_c"].values,
        np.where(has_v9d, df["vix9d_prev_c"].values, vix_prev),
    )
    df["rf_daily"] = df["rf_ann"].values / 252.0

    s_raw = df["O"].values
    c_raw = df["C"].values
    is_pre2014 = df.index < pd.Timestamp("2014-01-01")
    if DEFAULT_SPY_CSV.exists():
        spy_df = pd.read_csv(DEFAULT_SPY_CSV, index_col=0, parse_dates=True)
        spy_df.index = pd.to_datetime(spy_df.index, utc=True).tz_convert(None).normalize()
        spy_ret_oc = (spy_df["Close"] / spy_df["Open"]).reindex(df.index).values
        oc_ratio = np.where(np.isfinite(spy_ret_oc) & (spy_ret_oc > 0), spy_ret_oc, c_raw / s_raw)
    else:
        oc_ratio = c_raw / s_raw
    df["S_clean"] = np.where(is_pre2014, 5000.0, s_raw)
    df["C_clean"] = np.where(is_pre2014, 5000.0 * oc_ratio, c_raw)
    return df


class SimBwbBroker:
    """Historical replay broker for 0DTE SPX Put BWB with strict morning/close phase separation."""

    def __init__(self, cfg: LiveConfig, start_date: str | None = None, end_date: str | None = None):
        self.cfg = cfg
        self.df = load_clean_bwb_panel(cfg.bwb.panel_path)
        self.dates = self.df.index
        start_ts = pd.Timestamp(start_date or cfg.demo_start)
        self.t0 = int(np.searchsorted(self.dates, start_ts))
        if end_date:
            end_ts = pd.Timestamp(end_date)
            self.t_end = int(np.searchsorted(self.dates, end_ts, side="right")) - 1
        else:
            self.t_end = len(self.dates) - 1
        self.account_id = "DU-BWB-0002"
        self.quote_haircut_pct_of_risk: float = 0.0
        self.extra_slip_pct_of_risk: float = 0.0
        self.simulate_timeout_unfilled: bool = False
        self.reset()

    def reset(self) -> None:
        self.t = self.t0 - 1
        self.phase = "PRE_OPEN"
        self.cash = float(self.cfg.bwb.initial_capital)
        self.nlv = float(self.cfg.bwb.initial_capital)
        self.open_spread: OpenBwbSpread | None = None
        self.last_settlement: BwbSettlement | None = None
        self.last_cash_interest: float = 0.0
        self._fills_today: list[FillInfo] = []
        self._orders_today: list[OrderInfo] = []
        self._next_order_id: int = 1000

    @property
    def finished(self) -> bool:
        return self.t >= self.t_end

    def days_left(self) -> int:
        return self.t_end - self.t

    def progress(self) -> dict:
        return {
            "day": self.today().isoformat(),
            "done": max(0, self.t - self.t0 + 1),
            "total": max(1, self.t_end - self.t0 + 1),
        }

    def begin_day(self) -> None:
        self.t += 1
        self.phase = "MORNING_1030_DECISION"
        self.open_spread = None
        self.last_settlement = None
        self.last_cash_interest = 0.0
        self._fills_today = []
        self._orders_today = []

    def end_day(self) -> BwbSettlement | None:
        """Advances clock to 4:00 PM ET cash settlement, accruing T-Bill interest and settling 0DTE BWB."""
        self.phase = "EOD_1615_SETTLED"
        row = self.df.iloc[self.t]
        rf_d = float(row["rf_daily"])
        pre_eq = self.nlv
        self.last_cash_interest = pre_eq * rf_d

        settlement = None
        option_pnl = 0.0
        if self.open_spread is not None:
            sp = self.open_spread
            close_spot = float(row["C_clean"])
            settlement = settle_bwb(
                sp.plan, close_spot, sp.contracts, override_net_credit_pts=sp.entry_credit_pts
            )
            option_pnl = settlement.pnl_dollars
            day_str = self.today().isoformat()
            self._fills_today.append(
                FillInfo(
                    exec_id=f"bwb-settle-{day_str}",
                    symbol=sp.trade_key,
                    side="BUY",
                    shares=sp.contracts,
                    price=max(0.0, sp.entry_credit_pts - settlement.net_pnl_pts),
                    day=day_str,
                    role="settlement",
                    commission=settlement.settle_fee_pts * sp.plan.multiplier * sp.contracts,
                )
            )
            self.open_spread = None

        self.cash = pre_eq + self.last_cash_interest + option_pnl
        self.nlv = self.cash
        self.last_settlement = settlement
        return settlement

    async def connect(self) -> None:
        return None

    def is_connected(self) -> bool:
        return True

    async def disconnect(self) -> None:
        return None

    def today(self) -> date:
        idx = min(max(self.t, self.t0), self.t_end)
        return self.dates[idx].date()

    def now(self) -> datetime:
        tm = dtime(10, 30) if self.phase == "MORNING_1030_DECISION" else dtime(16, 15)
        return datetime.combine(self.today(), tm, tzinfo=mc.NY)

    def trading_days_between(self, d0: str, d1: str) -> int:
        i0 = int(np.searchsorted(self.dates, pd.Timestamp(d0)))
        i1 = int(np.searchsorted(self.dates, pd.Timestamp(d1)))
        return max(0, i1 - i0)

    async def market_snapshot(self) -> BwbMarketSnapshot:
        idx = min(max(self.t, self.t0), self.t_end)
        row = self.df.iloc[idx]
        day_str = self.dates[idx].date().isoformat()
        f1_pass = bool(row["f1_clean"])
        v1d_prev = float(row["vix1d_prev_clean"])
        vix_prev = float(row["vix_prev_clean"])
        iv1d_pct = float(row["iv1d_clean_pct"])
        vix_o = float(row["vix_o_clean"])
        if f1_pass:
            reason = f"F1 pass: prev VIX1D {v1d_prev:.1f} < VIX {vix_prev:.1f}, morning IV1D {iv1d_pct:.1f}% < VIX {vix_o:.1f}"
        else:
            reason = f"F1 gated: prev VIX1D {v1d_prev:.1f} vs VIX {vix_prev:.1f}, morning IV1D {iv1d_pct:.1f}% vs VIX {vix_o:.1f}"
        # Strict causal firewall: spot_close is None until EOD_1615_SETTLED
        close_val = float(row["C_clean"]) if self.phase == "EOD_1615_SETTLED" else None
        mark_val = close_val if close_val is not None else float(row["S_clean"])
        return BwbMarketSnapshot(
            day=day_str,
            spot_open=float(row["S_clean"]),
            spot_close=close_val,
            spot_mark=mark_val,
            iv1d=float(row["iv1d_clean"]),
            vix_open=vix_o,
            vix_prev_close=vix_prev,
            vix1d_prev_close=v1d_prev,
            iv1d_morning_pct=iv1d_pct,
            rf_annual=float(row["rf_ann"]),
            rf_daily=float(row["rf_daily"]),
            f1_pass=f1_pass,
            f1_reason=reason,
        )

    async def account(self) -> AccountInfo:
        maint = self.open_spread.margin_dollars if self.open_spread is not None else 0.0
        return AccountInfo(
            account_id=self.account_id,
            net_liquidation=self.nlv,
            cash=self.cash,
            maint_margin=maint,
            excess_liquidity=max(0.0, self.nlv - maint),
        )

    async def positions(self) -> list[PositionInfo]:
        if self.open_spread is None:
            return []
        sp = self.open_spread
        return [
            PositionInfo(
                symbol=sp.trade_key,
                shares=-sp.contracts,
                avg_cost=sp.entry_credit_pts,
                market_price=sp.entry_credit_pts,
                unrealized_pnl=sp.mark_pnl_dollars,
            )
        ]

    async def open_orders(self) -> list[OrderInfo]:
        return list(self._orders_today)

    async def fills_today(self) -> list[FillInfo]:
        return list(self._fills_today)

    async def quote_bwb_spread(self, plan: BwbPlan) -> BwbQuoteSnapshot:
        live_mid = plan.mid_credit_pts + self.quote_haircut_pct_of_risk * plan.w_risk_pts
        est_slip = plan.slip_pts
        est_net = live_mid - est_slip - plan.fee_pts
        nat = live_mid - 2.0 * est_slip
        return BwbQuoteSnapshot(
            k_hi=plan.k_hi,
            k_mid=plan.k_mid,
            k_lo=plan.k_lo,
            w_risk_pts=plan.w_risk_pts,
            bid_hi=0.0,
            ask_hi=0.0,
            bid_mid=0.0,
            ask_mid=0.0,
            bid_lo=0.0,
            ask_lo=0.0,
            live_mid_credit_pts=live_mid,
            natural_credit_pts=nat,
            est_slip_pts=est_slip,
            est_net_credit_pts=est_net,
            source="sim",
        )

    async def place_bwb_spread(
        self,
        plan: BwbPlan,
        contracts: float,
        trade_key: str,
        quote: BwbQuoteSnapshot | None = None,
        min_credit_pts: float | None = None,
    ) -> BwbFillResult:
        if self.cfg.mode == "shadow":
            raise ReadOnlyError("read-only mode: no orders")
        q = quote if quote is not None else await self.quote_bwb_spread(plan)
        floor_pts = float(min_credit_pts) if min_credit_pts is not None else 0.0
        if floor_pts > 0.0 and q.est_net_credit_pts < floor_pts - 1e-9:
            return BwbFillResult(
                filled=False,
                contracts=0.0,
                gross_credit_pts=0.0,
                commission_dollars=0.0,
                net_credit_pts=0.0,
                limit_credit_pts=floor_pts + plan.fee_pts,
                order_id=0,
                status="Skipped: live quote below min credit floor",
            )
        if self.simulate_timeout_unfilled:
            return BwbFillResult(
                filled=False,
                contracts=0.0,
                gross_credit_pts=0.0,
                commission_dollars=0.0,
                net_credit_pts=0.0,
                limit_credit_pts=q.est_net_credit_pts + plan.fee_pts,
                order_id=0,
                status="Cancelled: unfilled at 10:30 window",
            )

        self._next_order_id += 1
        oid = self._next_order_id
        margin = contracts * plan.margin_per_contract
        actual_net = q.est_net_credit_pts - self.extra_slip_pct_of_risk * plan.w_risk_pts
        comm_usd = plan.fee_pts * plan.multiplier * contracts
        actual_gross = actual_net + plan.fee_pts

        self.open_spread = OpenBwbSpread(
            trade_key=trade_key,
            symbol=plan.symbol,
            day=plan.day,
            plan=plan,
            contracts=contracts,
            entry_credit_pts=actual_net,
            margin_dollars=margin,
        )
        order = OrderInfo(
            order_id=oid,
            symbol=trade_key,
            action="SELL",
            order_type="BAG LMT",
            quantity=contracts,
            limit_price=actual_gross,
            stop_price=plan.k_lo,
            status="Filled",
            role="entry",
        )
        self._orders_today.append(order)
        self._fills_today.append(
            FillInfo(
                exec_id=f"bwb-entry-{plan.day}",
                symbol=trade_key,
                side="SELL",
                shares=contracts,
                price=actual_gross,
                day=plan.day,
                role="entry",
                commission=comm_usd,
            )
        )
        return BwbFillResult(
            filled=True,
            contracts=contracts,
            gross_credit_pts=actual_gross,
            commission_dollars=comm_usd,
            net_credit_pts=actual_net,
            limit_credit_pts=actual_gross,
            order_id=oid,
            status="Filled",
        )

    async def close_spread(self, trade_key: str, how: str = "MKT") -> OrderInfo:
        if self.open_spread is None or (trade_key and self.open_spread.trade_key != trade_key):
            raise LookupError(trade_key or "SPXW")
        sp = self.open_spread
        self._next_order_id += 1
        oid = self._next_order_id
        self._fills_today.append(
            FillInfo(
                exec_id=f"bwb-manual-{sp.day}-{oid}",
                symbol=sp.trade_key,
                side="BUY",
                shares=sp.contracts,
                price=sp.entry_credit_pts,
                day=sp.day,
                role="manual",
                commission=sp.plan.fee_pts * sp.plan.multiplier * sp.contracts,
            )
        )
        self.open_spread = None
        return OrderInfo(
            order_id=oid,
            symbol=sp.trade_key,
            action="BUY",
            order_type=how,
            quantity=sp.contracts,
            limit_price=sp.entry_credit_pts,
            stop_price=None,
            status="Filled",
            role="manual",
        )


class IBKRBwbBroker:
    """Live / Paper / Shadow IBKR TWS connection for 0DTE SPX/XSP Put Broken-Wing Butterfly."""

    def __init__(self, cfg: LiveConfig, readonly: bool):
        self.cfg = cfg
        self.readonly = readonly
        self.ib = None
        self.account_id = ""

    async def connect(self) -> None:
        from ib_async import IB

        if self.ib is None:
            self.ib = IB()
        if self.ib.isConnected():
            return
        cid = self.cfg.client_id + self.cfg.bwb.client_id_offset
        await self.ib.connectAsync(
            self.cfg.tws_host,
            self.cfg.tws_port,
            clientId=cid,
            readonly=self.readonly,
            timeout=20,
        )
        self.ib.reqMarketDataType(1)
        accounts = self.ib.managedAccounts()
        if not accounts:
            self.ib.disconnect()
            raise ConnectionError("TWS reported no account")
        self.account_id = accounts[0]
        paper = self.account_id.startswith("DU")
        if self.cfg.mode == "paper" and not paper:
            self.ib.disconnect()
            raise RuntimeError("paper mode, but TWS is logged into a live account")
        if self.cfg.mode == "live" and paper:
            self.ib.disconnect()
            raise RuntimeError("live mode, but TWS is logged into a paper account")

    def is_connected(self) -> bool:
        return self.ib is not None and self.ib.isConnected()

    async def disconnect(self) -> None:
        if self.is_connected():
            self.ib.disconnect()

    def now(self) -> datetime:
        return mc.now_et()

    def today(self) -> date:
        return self.now().date()

    def trading_days_between(self, d0: str, d1: str) -> int:
        return mc.trading_days_between(date.fromisoformat(d0[:10]), date.fromisoformat(d1[:10]))

    async def _index_bars(self, symbol: str) -> tuple[float, float, float]:
        """Returns (prev_close, today_open, last_mark) for a CBOE index (SPX, VIX, VIX1D)."""
        from ib_async import Index

        idx = Index(symbol, "CBOE", "USD")
        await self.ib.qualifyContractsAsync(idx)
        bars = await self.ib.reqHistoricalDataAsync(
            idx,
            endDateTime="",
            durationStr="5 D",
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )
        if not bars or len(bars) < 2:
            raise ValueError(f"insufficient index bars for {symbol}")
        today_str = self.today().isoformat()
        last_bar = bars[-1]
        if str(last_bar.date)[:10] == today_str:
            prev_close = float(bars[-2].close)
            today_open = float(last_bar.open)
            mark = float(last_bar.close)
        else:
            prev_close = float(last_bar.close)
            today_open = float(last_bar.close)
            mark = float(last_bar.close)
        return prev_close, today_open, mark

    async def market_snapshot(self) -> BwbMarketSnapshot:
        _, spx_open, spx_mark = await self._index_bars("SPX")
        vix_prev, vix_open, _ = await self._index_bars("VIX")
        try:
            v1d_prev, v1d_open, _ = await self._index_bars("VIX1D")
        except Exception:
            v1d_prev, v1d_open = vix_prev * 0.85, vix_open * 0.85

        iv1d = min(1.50, max(0.04, v1d_open / 100.0))
        f1_pass = (v1d_prev < vix_prev) and (v1d_open < vix_open)
        if f1_pass:
            reason = f"F1 pass: prev VIX1D {v1d_prev:.1f} < VIX {vix_prev:.1f}, morning VIX1D {v1d_open:.1f} < VIX {vix_open:.1f}"
        else:
            reason = f"F1 gated: prev VIX1D {v1d_prev:.1f} vs VIX {vix_prev:.1f}, morning VIX1D {v1d_open:.1f} vs VIX {vix_open:.1f}"
        day_str = self.today().isoformat()
        is_settled = self.now().time() >= dtime(16, 5)
        return BwbMarketSnapshot(
            day=day_str,
            spot_open=spx_open,
            spot_close=spx_mark if is_settled else None,
            spot_mark=spx_mark,
            iv1d=iv1d,
            vix_open=vix_open,
            vix_prev_close=vix_prev,
            vix1d_prev_close=v1d_prev,
            iv1d_morning_pct=v1d_open,
            rf_annual=0.045,
            rf_daily=0.045 / 252.0,
            f1_pass=f1_pass,
            f1_reason=reason,
        )

    async def account(self) -> AccountInfo:
        values = {
            v.tag: float(v.value)
            for v in self.ib.accountValues(self.account_id)
            if v.currency == "USD"
            and v.tag in ("NetLiquidation", "TotalCashValue", "MaintMarginReq", "ExcessLiquidity")
        }
        return AccountInfo(
            account_id=self.account_id,
            net_liquidation=values.get("NetLiquidation", math.nan),
            cash=values.get("TotalCashValue", math.nan),
            maint_margin=values.get("MaintMarginReq", math.nan),
            excess_liquidity=values.get("ExcessLiquidity", math.nan),
        )

    async def positions(self) -> list[PositionInfo]:
        await self.ib.reqPositionsAsync()
        out = []
        for item in self.ib.portfolio(self.account_id):
            c = item.contract
            if item.position == 0 or c.secType not in ("OPT", "BAG") or c.symbol not in ("SPX", "SPXW", "XSP"):
                continue
            mult = float(c.multiplier or 100)
            out.append(
                PositionInfo(
                    symbol=f"{c.symbol} {int(c.strike)}P" if getattr(c, "strike", 0) else c.symbol,
                    shares=float(item.position),
                    avg_cost=float(item.averageCost) / mult,
                    market_price=float(item.marketPrice),
                    unrealized_pnl=float(item.unrealizedPNL),
                )
            )
        return out

    async def open_orders(self) -> list[OrderInfo]:
        await self.ib.reqOpenOrdersAsync()
        out = []
        for tr in self.ib.openTrades():
            o, st = tr.order, tr.orderStatus
            if getattr(o, "orderRef", "") not in ("bwb-entry", "bwb-manual"):
                continue
            out.append(
                OrderInfo(
                    order_id=o.orderId,
                    symbol=tr.contract.symbol,
                    action=o.action,
                    order_type=o.orderType,
                    quantity=float(o.totalQuantity),
                    limit_price=float(o.lmtPrice) if o.lmtPrice else None,
                    stop_price=None,
                    status=st.status,
                    role="entry" if o.orderRef == "bwb-entry" else "manual",
                )
            )
        return out

    async def fills_today(self) -> list[FillInfo]:
        today_str = self.today().isoformat()
        out = []
        for f in self.ib.fills():
            ex = f.execution
            if ex.acctNumber and ex.acctNumber != self.account_id:
                continue
            if ex.orderRef not in ("bwb-entry", "bwb-manual"):
                continue
            day = ex.time.astimezone(mc.NY).date().isoformat() if ex.time else today_str
            if day != today_str:
                continue
            comm = float(f.commissionReport.commission) if f.commissionReport else 0.0
            out.append(
                FillInfo(
                    exec_id=ex.execId,
                    symbol=f.contract.symbol,
                    side=ex.side,
                    shares=float(ex.shares),
                    price=float(ex.price),
                    day=day,
                    role="entry" if ex.orderRef == "bwb-entry" else "manual",
                    commission=comm,
                )
            )
        return out

    def _guard_write(self) -> None:
        if self.readonly or self.cfg.mode == "shadow":
            raise ReadOnlyError("read-only mode: no orders")
        if not self.is_connected():
            raise ConnectionError("not connected to TWS")

    async def _qualify_bwb_legs(self, plan: BwbPlan):
        from ib_async import Option

        expiry = plan.day.replace("-", "")
        und_sym = "XSP" if plan.symbol == "XSP" else "SPX"
        t_class = "XSP" if plan.symbol == "XSP" else "SPXW"
        step = 1.0 if plan.symbol == "XSP" else 5.0
        k_mid = round(plan.k_mid / step) * step
        k_hi = max(k_mid + step, round(plan.k_hi / step) * step)
        w1_act = k_hi - k_mid
        w2_act = max(w1_act + step, round((plan.k_mid - plan.k_lo) / step) * step)
        k_lo = k_mid - w2_act

        opt_hi = Option(und_sym, expiry, k_hi, "P", "SMART", tradingClass=t_class)
        opt_mid = Option(und_sym, expiry, k_mid, "P", "SMART", tradingClass=t_class)
        opt_lo = Option(und_sym, expiry, k_lo, "P", "SMART", tradingClass=t_class)
        await self.ib.qualifyContractsAsync(opt_hi, opt_mid, opt_lo)
        return und_sym, step, k_hi, k_mid, k_lo, opt_hi, opt_mid, opt_lo

    async def quote_bwb_spread(self, plan: BwbPlan) -> BwbQuoteSnapshot:
        """Snapshots live IBKR/Cboe NBBO bid/ask on all 3 BWB put strikes (read-only safe in shadow mode)."""
        if not self.is_connected():
            raise ConnectionError("not connected to TWS")
        _, step, k_hi, k_mid, k_lo, opt_hi, opt_mid, opt_lo = await self._qualify_bwb_legs(plan)
        tickers = await self.ib.reqTickersAsync(opt_hi, opt_mid, opt_lo)
        scale = 0.1 if plan.symbol == "XSP" else 1.0

        def _extract_ba(tkr, k_strike: float) -> tuple[float, float, bool]:
            b = float(getattr(tkr, "bid", math.nan) or math.nan)
            a = float(getattr(tkr, "ask", math.nan) or math.nan)
            if math.isfinite(b) and math.isfinite(a) and a > 0.0 and b >= 0.0 and a >= b:
                return b, a, True
            ref = float(getattr(tkr, "close", math.nan) or getattr(tkr, "last", math.nan) or math.nan)
            if not (math.isfinite(ref) and ref > 0.0):
                z = math.log(k_strike / plan.spot) / max(plan.iv1d * SQRT_T_0DTE, 1e-6)
                sig = plan.iv1d * float(iv_ratio_0dte(z))
                ref = bs_price_0dte(plan.spot, k_strike, T_0DTE, 0.045, sig, is_call=False)
            hs = half_spread_pts(ref) * scale
            return max(0.0, ref - hs), ref + hs, False

        b_hi, a_hi, ok_hi = _extract_ba(tickers[0], k_hi)
        b_m, a_m, ok_m = _extract_ba(tickers[1], k_mid)
        b_lo, a_lo, ok_lo = _extract_ba(tickers[2], k_lo)

        mid_hi = 0.5 * (b_hi + a_hi)
        mid_m = 0.5 * (b_m + a_m)
        mid_lo = 0.5 * (b_lo + a_lo)

        live_mid = 2.0 * mid_m - mid_hi - mid_lo
        nat_cred = 2.0 * b_m - a_hi - a_lo
        hs_sum = 0.5 * ((a_hi - b_hi) + 2.0 * (a_m - b_m) + (a_lo - b_lo))
        est_slip = max(0.05 * scale, 0.35 * hs_sum)
        est_net = live_mid - est_slip - plan.fee_pts
        w_risk = max(step, 2.0 * k_mid - k_hi - k_lo)
        src = "ibkr_nbbo" if (ok_hi and ok_m and ok_lo) else "ibkr_partial"

        return BwbQuoteSnapshot(
            k_hi=k_hi,
            k_mid=k_mid,
            k_lo=k_lo,
            w_risk_pts=w_risk,
            bid_hi=b_hi,
            ask_hi=a_hi,
            bid_mid=b_m,
            ask_mid=a_m,
            bid_lo=b_lo,
            ask_lo=a_lo,
            live_mid_credit_pts=live_mid,
            natural_credit_pts=nat_cred,
            est_slip_pts=est_slip,
            est_net_credit_pts=est_net,
            source=src,
        )

    async def place_bwb_spread(
        self,
        plan: BwbPlan,
        contracts: float,
        trade_key: str,
        quote: BwbQuoteSnapshot | None = None,
        min_credit_pts: float | None = None,
    ) -> BwbFillResult:
        self._guard_write()
        from ib_async import ComboLeg, Contract, Order

        q = quote if quote is not None else await self.quote_bwb_spread(plan)
        floor_net = float(min_credit_pts) if min_credit_pts is not None else 0.0
        floor_gross = floor_net + plan.fee_pts
        if floor_net > 0.0 and q.live_mid_credit_pts < floor_gross - 1e-6:
            return BwbFillResult(
                filled=False,
                contracts=0.0,
                gross_credit_pts=0.0,
                commission_dollars=0.0,
                net_credit_pts=0.0,
                limit_credit_pts=floor_gross,
                order_id=0,
                status="Skipped: live mid below min credit floor",
            )

        und_sym, _, k_hi, k_mid, k_lo, opt_hi, opt_mid, opt_lo = await self._qualify_bwb_legs(plan)
        bag = Contract(
            symbol=und_sym,
            secType="BAG",
            currency="USD",
            exchange="SMART",
            comboLegs=[
                ComboLeg(conId=opt_hi.conId, ratio=1, action="BUY", exchange="SMART"),
                ComboLeg(conId=opt_mid.conId, ratio=2, action="SELL", exchange="SMART"),
                ComboLeg(conId=opt_lo.conId, ratio=1, action="BUY", exchange="SMART"),
            ],
        )
        qty = max(1, int(round(contracts)))
        tick = 0.01 if plan.symbol == "XSP" else 0.05
        floor_tick = round(math.ceil((floor_gross - 1e-9) / tick) * tick, 2) if floor_gross > 0 else tick
        lmt_1 = max(floor_tick, round(round((q.live_mid_credit_pts - 0.5 * q.est_slip_pts) / tick) * tick, 2))
        lmt_2 = max(floor_tick, round(round((q.est_net_credit_pts + plan.fee_pts) / tick) * tick, 2))

        order = Order(
            action="BUY",
            totalQuantity=qty,
            orderType="LMT",
            lmtPrice=-lmt_1,
            tif="DAY",
            transmit=True,
            orderRef="bwb-entry",
            account=self.account_id,
        )
        trade = self.ib.placeOrder(bag, order)
        cur_lmt = lmt_1

        timeout_s = max(5.0, float(self.cfg.bwb.entry_timeout_sec))
        half_s = timeout_s / 2.0
        t0 = asyncio.get_event_loop().time()
        stepped = False

        while not trade.isDone():
            elapsed = asyncio.get_event_loop().time() - t0
            if elapsed >= timeout_s:
                break
            if (not stepped) and elapsed >= half_s and lmt_2 < lmt_1 - 1e-6:
                stepped = True
                cur_lmt = lmt_2
                order.lmtPrice = -cur_lmt
                trade = self.ib.placeOrder(bag, order)
            await asyncio.sleep(min(2.0, max(0.2, timeout_s - elapsed)))

        if not trade.isDone():
            self.ib.cancelOrder(order)
            for _ in range(10):
                if trade.isDone():
                    break
                await asyncio.sleep(0.2)

        filled_qty = float(trade.orderStatus.filled or 0.0)
        if filled_qty <= 0.0:
            return BwbFillResult(
                filled=False,
                contracts=0.0,
                gross_credit_pts=0.0,
                commission_dollars=0.0,
                net_credit_pts=0.0,
                limit_credit_pts=cur_lmt,
                order_id=int(order.orderId or 0),
                status="Cancelled: unfilled at 10:30 window",
            )

        # Compute exact gross credit per spread from OPT leg cashflows (or combo avgFillPrice fallback)
        opt_fills = [f for f in trade.fills if getattr(f.contract, "secType", "") == "OPT"]
        if opt_fills:
            cash_pts = 0.0
            for f in opt_fills:
                sh = float(f.execution.shares)
                px = float(f.execution.price)
                cash_pts += sh * px if f.execution.side in ("SLD", "SELL") else -sh * px
            gross_credit_pts = cash_pts / filled_qty
        else:
            avg_px = float(trade.orderStatus.avgFillPrice or -cur_lmt)
            gross_credit_pts = -avg_px if avg_px < 0 else avg_px

        comm_usd = sum(
            float(f.commissionReport.commission)
            for f in trade.fills
            if getattr(f, "commissionReport", None) and f.commissionReport.commission
        )
        if comm_usd <= 0.0:
            comm_usd = plan.fee_pts * plan.multiplier * filled_qty
        net_credit_pts = gross_credit_pts - (comm_usd / (plan.multiplier * filled_qty))

        return BwbFillResult(
            filled=True,
            contracts=filled_qty,
            gross_credit_pts=gross_credit_pts,
            commission_dollars=comm_usd,
            net_credit_pts=net_credit_pts,
            limit_credit_pts=cur_lmt,
            order_id=int(order.orderId or 0),
            status=str(trade.orderStatus.status or "Filled"),
        )

    async def close_spread(self, trade_key: str, how: str = "MKT") -> OrderInfo:
        self._guard_write()
        from ib_async import Order

        positions = await self.positions()
        if not positions:
            raise LookupError(trade_key)
        order = Order(
            action="BUY",
            totalQuantity=1,
            orderType=how,
            tif="DAY",
            transmit=True,
            orderRef="bwb-manual",
            account=self.account_id,
        )
        return OrderInfo(
            order_id=0,
            symbol=trade_key,
            action="BUY",
            order_type=how,
            quantity=1.0,
            limit_price=None,
            stop_price=None,
            status="Submitted",
            role="manual",
        )
