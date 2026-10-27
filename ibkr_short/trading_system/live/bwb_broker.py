"""IBKR TWS / Gateway and Historical Replay brokers for the 0DTE SPX Put BWB strategy."""
from __future__ import annotations

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
from .bwb_strategy import BwbMarketSnapshot, BwbPlan, BwbSettlement, settle_bwb
from .config import LiveConfig

log = logging.getLogger(__name__)

DEFAULT_PANEL_PATHS = (
    Path("/usr/local/google/home/lfesch/.gemini/jetski/scratch/spx_0dte_study/out/daily_panel.pkl"),
    Path(__file__).resolve().parents[2] / "data" / "bwb_daily_panel.pkl",
)
DEFAULT_SPY_CSV = Path("/usr/local/google/home/lfesch/.gemini/jetski/scratch/spx_0dte_study/data/yf_SPY_1d.csv")


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
            settlement = settle_bwb(sp.plan, close_spot, sp.contracts)
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

    async def place_bwb_spread(self, plan: BwbPlan, contracts: float, trade_key: str) -> OrderInfo:
        if self.cfg.mode == "shadow":
            raise ReadOnlyError("read-only mode: no orders")
        self._next_order_id += 1
        oid = self._next_order_id
        margin = contracts * plan.margin_per_contract
        self.open_spread = OpenBwbSpread(
            trade_key=trade_key,
            symbol=plan.symbol,
            day=plan.day,
            plan=plan,
            contracts=contracts,
            entry_credit_pts=plan.net_credit_pts,
            margin_dollars=margin,
        )
        order = OrderInfo(
            order_id=oid,
            symbol=trade_key,
            action="SELL",
            order_type="BAG LMT",
            quantity=contracts,
            limit_price=plan.net_credit_pts,
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
                price=plan.net_credit_pts,
                day=plan.day,
                role="entry",
                commission=plan.fee_pts * plan.multiplier * contracts,
            )
        )
        return order

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

    async def place_bwb_spread(self, plan: BwbPlan, contracts: float, trade_key: str) -> OrderInfo:
        self._guard_write()
        from ib_async import ComboLeg, Contract, Option, Order

        expiry = plan.day.replace("-", "")
        und_sym = "XSP" if plan.symbol == "XSP" else "SPX"
        t_class = "XSP" if plan.symbol == "XSP" else "SPXW"
        step = 1.0 if plan.symbol == "XSP" else 5.0
        k_hi = round(plan.k_hi / step) * step
        k_mid = round(plan.k_mid / step) * step
        k_lo = round(plan.k_lo / step) * step

        opt_hi = Option(und_sym, expiry, k_hi, "P", "SMART", tradingClass=t_class)
        opt_mid = Option(und_sym, expiry, k_mid, "P", "SMART", tradingClass=t_class)
        opt_lo = Option(und_sym, expiry, k_lo, "P", "SMART", tradingClass=t_class)
        await self.ib.qualifyContractsAsync(opt_hi, opt_mid, opt_lo)

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
        lmt_credit = round(plan.net_credit_pts, 2)
        order = Order(
            action="BUY",
            totalQuantity=qty,
            orderType="LMT",
            lmtPrice=-lmt_credit,
            tif="DAY",
            transmit=True,
            orderRef="bwb-entry",
            account=self.account_id,
        )
        trade = self.ib.placeOrder(bag, order)
        return OrderInfo(
            order_id=order.orderId,
            symbol=trade_key,
            action="SELL",
            order_type="BAG LMT",
            quantity=float(qty),
            limit_price=lmt_credit,
            stop_price=k_lo,
            status=trade.orderStatus.status,
            role="entry",
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
