"""IBKR TWS / Gateway and Historical Replay brokers for the 0DTE SPX Put BWB strategy."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time as dtime
from functools import lru_cache
import json
import logging
import math
from pathlib import Path
import time
import urllib.request

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


_YAHOO_INDEX_MAP = {
    "SPX": "%5EGSPC",
    "VIX": "%5EVIX",
    "VIX1D": "%5EVIX1D",
}

_INFO_ERROR_CODES = frozenset({2104, 2106, 2107, 2108, 2119, 2158})


def _yahoo_live_index(symbol: str, expected_day: str) -> float | None:
    """Last-resort backup: fetches real-time CBOE/S&P index value from Yahoo Finance, verified against expected_day (NY)."""
    tkr = _YAHOO_INDEX_MAP.get(symbol)
    if not tkr:
        return None
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{tkr}?interval=1m&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        meta = payload["chart"]["result"][0]["meta"]
        price = float(meta.get("regularMarketPrice") or math.nan)
        ts = int(meta.get("regularMarketTime") or 0)
        if not (math.isfinite(price) and price > 0.0 and ts > 0):
            return None
        bar_day = datetime.fromtimestamp(ts, tz=mc.NY).date().isoformat()
        if bar_day != expected_day:
            return None
        return price
    except Exception as exc:
        log.debug("Yahoo live index fallback failed for %s: %s", symbol, type(exc).__name__)
        return None


class IBKRBwbBroker:
    """Live / Paper / Shadow IBKR TWS connection for 0DTE SPX/XSP Put Broken-Wing Butterfly."""

    def __init__(self, cfg: LiveConfig, readonly: bool):
        self.cfg = cfg
        self.readonly = readonly
        self.ib = None
        self.account_id = ""
        self._error_hooked = False
        self._req_errors: dict[int, list[tuple[int, str]]] = {}
        self._global_errors: list[tuple[float, int, str]] = []
        self.last_quote_warning: str = ""
        self.last_data_source: dict[str, str] = {}

    def _on_ib_error(self, reqId: int, errorCode: int, errorString: str, contract=None) -> None:
        if errorCode in _INFO_ERROR_CODES:
            return
        clean = " ".join(str(errorString or "").split())[:180]
        now_m = time.monotonic()
        self._global_errors.append((now_m, int(errorCode), clean))
        if len(self._global_errors) > 60:
            self._global_errors = self._global_errors[-40:]
        if reqId is not None and int(reqId) >= 0:
            if len(self._req_errors) > 500:
                self._req_errors.clear()
            bucket = self._req_errors.setdefault(int(reqId), [])
            if len(bucket) < 8:
                bucket.append((int(errorCode), clean))

    def format_req_errors(self, req_id: int) -> str:
        items = self._req_errors.get(int(req_id), [])
        return "; ".join(f"[{c}] {m}" for c, m in items)

    def recent_errors_since(self, mono_ts: float, exclude_codes: tuple[int, ...] = ()) -> str:
        seen: list[str] = []
        for ts, code, msg in self._global_errors:
            if ts >= mono_ts and code not in exclude_codes:
                entry = f"[{code}] {msg}"
                if entry not in seen:
                    seen.append(entry)
        return "; ".join(seen[-3:])

    async def connect(self) -> None:
        from ib_async import IB

        if self.ib is None:
            self.ib = IB()
        if not self._error_hooked:
            self.ib.errorEvent += self._on_ib_error
            self._error_hooked = True
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
        return mc.now_ny()

    def today(self) -> date:
        return self.now().date()

    def trading_days_between(self, d0: str, d1: str) -> int:
        return mc.trading_days_between(date.fromisoformat(d0[:10]), date.fromisoformat(d1[:10]))

    async def _live_ib_index_mark(self, idx) -> float | None:
        """Polls IBKR streaming index tick for up to 2.0s; ignores stale prior-day close."""
        t0 = time.monotonic()
        tkr = self.ib.reqMktData(idx, "", False, False)
        try:
            for _ in range(10):
                await asyncio.sleep(0.2)
                last_px = float(getattr(tkr, "last", math.nan) or math.nan)
                if math.isfinite(last_px) and last_px > 0.0:
                    return last_px
                bid_px = float(getattr(tkr, "bid", math.nan) or math.nan)
                ask_px = float(getattr(tkr, "ask", math.nan) or math.nan)
                if math.isfinite(bid_px) and math.isfinite(ask_px) and ask_px > 0.0 and bid_px > 0.0:
                    return 0.5 * (bid_px + ask_px)
                err = self.recent_errors_since(t0)
                if any(code in err for code in ("[354]", "[10089]", "[10167]")):
                    break
            return None
        finally:
            try:
                self.ib.cancelMktData(idx)
            except Exception:
                pass

    async def _ib_intraday_1m_close(self, idx, expected_day: str, max_age_s: float | None = 240.0) -> float | None:
        """Latest 1-minute RTH index bar from IBKR verified for expected_day (rejects 15m-delayed bars intraday)."""
        try:
            ib_bars = await asyncio.wait_for(
                self.ib.reqHistoricalDataAsync(
                    idx,
                    endDateTime="",
                    durationStr="7200 S",
                    barSizeSetting="1 min",
                    whatToShow="TRADES",
                    useRTH=True,
                    formatDate=1,
                ),
                timeout=8.0,
            )
            if not ib_bars:
                return None
            b_last = ib_bars[-1]
            dt = b_last.date
            bar_ny: datetime | None = None
            if isinstance(dt, datetime):
                bar_ny = dt.astimezone(mc.NY) if dt.tzinfo else dt.replace(tzinfo=mc.NY)
                b_day = bar_ny.date().isoformat()
            else:
                s_dt = str(dt).strip()
                b_day = f"{s_dt[:4]}-{s_dt[4:6]}-{s_dt[6:8]}" if len(s_dt) >= 8 and s_dt[:8].isdigit() else s_dt[:10]
                if len(s_dt) >= 19 and s_dt[4:5] == "-":
                    try:
                        bar_ny = datetime.fromisoformat(s_dt[:19]).replace(tzinfo=mc.NY)
                    except ValueError:
                        bar_ny = None
            if max_age_s is not None and bar_ny is not None:
                if (self.now() - bar_ny).total_seconds() > max_age_s:
                    return None
            val = float(b_last.close)
            if b_day == expected_day and math.isfinite(val) and val > 0.0:
                return val
        except Exception as exc:
            log.debug("IBKR 1m index bar fallback failed for %s: %s", idx.symbol, type(exc).__name__)
        return None

    async def _index_bars(self, symbol: str) -> tuple[float, float, float]:
        """Returns (prev_close, current_or_open, last_mark) for a CBOE index (SPX, VIX, VIX1D).

        During intraday RTH (09:30-16:05 ET), current_or_open and last_mark reflect the
        LIVE current index level at decision time (10:30 AM ET), NOT the stale 9:30 AM open.
        After 16:05 ET, last_mark reflects today's official settlement close.
        """
        from ib_async import Index

        t0 = time.monotonic()
        idx = Index(symbol, "CBOE", "USD")
        await self.ib.qualifyContractsAsync(idx)
        bars = await asyncio.wait_for(
            self.ib.reqHistoricalDataAsync(
                idx,
                endDateTime="",
                durationStr="10 D",
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            ),
            timeout=15.0,
        )
        if not bars or len(bars) < 2:
            err = self.recent_errors_since(t0)
            raise RuntimeError(f"Insufficient daily index bars for {symbol}" + (f" ({err})" if err else ""))

        now_ny = self.now()
        today_d = now_ny.date()
        today_str = today_d.isoformat()
        last_bar = bars[-1]
        has_today_bar = str(last_bar.date)[:10] == today_str
        prev_close = float(bars[-2].close) if has_today_bar else float(last_bar.close)

        is_td = mc.is_trading_day(today_d)
        cur_t = now_ny.time()

        # Case 1: Intraday RTH (09:30 <= now < 16:05 ET on a trading day) -> 100% IBKR first (live tick -> 1m bar), Yahoo last-resort
        if is_td and dtime(9, 30) <= cur_t < dtime(16, 5):
            cur_val = await self._live_ib_index_mark(idx)
            if cur_val is not None:
                self.last_data_source[symbol] = "ibkr_live"
                return prev_close, cur_val, cur_val

            cur_val = await self._ib_intraday_1m_close(idx, today_str)
            if cur_val is not None:
                self.last_data_source[symbol] = "ibkr_1m"
                return prev_close, cur_val, cur_val

            cur_val = await asyncio.to_thread(_yahoo_live_index, symbol, today_str)
            if cur_val is not None:
                self.last_data_source[symbol] = "yahoo_realtime"
                return prev_close, cur_val, cur_val

            err = self.recent_errors_since(t0)
            raise RuntimeError(
                f"Cannot obtain live intraday {symbol} level for {today_str}" + (f" ({err})" if err else "")
            )

        # Case 2: Post-close settlement window (>= 16:05 ET on a trading day) -> require today's close
        if is_td and cur_t >= dtime(16, 5):
            if has_today_bar and math.isfinite(float(last_bar.close)) and float(last_bar.close) > 0:
                self.last_data_source[symbol] = "ibkr_daily_close"
                return prev_close, float(last_bar.open), float(last_bar.close)

            cur_val = await self._ib_intraday_1m_close(idx, today_str, max_age_s=None)
            if cur_val is None:
                cur_val = await asyncio.to_thread(_yahoo_live_index, symbol, today_str)
            if cur_val is not None:
                self.last_data_source[symbol] = "intraday_close_fallback"
                return prev_close, cur_val, cur_val

            err = self.recent_errors_since(t0)
            raise RuntimeError(
                f"Missing {today_str} settlement close for {symbol}" + (f" ({err})" if err else "")
            )

        # Case 3: Pre-market or weekend/holiday -> return most recent completed bar
        ref_open = float(last_bar.open) if has_today_bar else float(last_bar.close)
        ref_mark = float(last_bar.close)
        self.last_data_source[symbol] = "ibkr_prev_bar"
        return prev_close, ref_open, ref_mark

    async def market_snapshot(self) -> BwbMarketSnapshot:
        _, spx_spot, spx_mark = await self._index_bars("SPX")
        vix_prev, vix_now, _ = await self._index_bars("VIX")
        v1d_fallback_note = ""
        try:
            v1d_prev, v1d_now, _ = await self._index_bars("VIX1D")
        except Exception as exc:
            log.warning("VIX1D fetch degraded, using 0.85x VIX proxy: %s", exc)
            v1d_prev, v1d_now = vix_prev * 0.85, vix_now * 0.85
            self.last_data_source["VIX1D"] = "vix_proxy_0.85"
            v1d_fallback_note = " [VIX1D proxy]"

        iv1d = min(1.50, max(0.04, v1d_now / 100.0))
        f1_pass = (v1d_prev < vix_prev) and (v1d_now < vix_now)
        src_tag = self.last_data_source.get("SPX", "")
        src_suffix = f" [src:{src_tag}]{v1d_fallback_note}" if src_tag else v1d_fallback_note
        if f1_pass:
            reason = (
                f"F1 pass: prev VIX1D {v1d_prev:.1f} < VIX {vix_prev:.1f}, "
                f"10:30 VIX1D {v1d_now:.1f} < VIX {vix_now:.1f}{src_suffix}"
            )
        else:
            reason = (
                f"F1 gated: prev VIX1D {v1d_prev:.1f} vs VIX {vix_prev:.1f}, "
                f"10:30 VIX1D {v1d_now:.1f} vs VIX {vix_now:.1f}{src_suffix}"
            )
        day_str = self.today().isoformat()
        is_settled = mc.is_trading_day(self.today()) and self.now().time() >= dtime(16, 5)
        return BwbMarketSnapshot(
            day=day_str,
            spot_open=spx_spot,
            spot_close=spx_mark if is_settled else None,
            spot_mark=spx_mark,
            iv1d=iv1d,
            vix_open=vix_now,
            vix_prev_close=vix_prev,
            vix1d_prev_close=v1d_prev,
            iv1d_morning_pct=v1d_now,
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

    async def _qualify_single_put(self, und_sym: str, expiry: str, strike: float, t_class: str, candidates: list[float]):
        """Qualifies a CBOE put option at strike, snapping to nearest listed strike in candidates if needed."""
        from ib_async import Option

        tried: list[float] = []
        for k in [strike] + [c for c in candidates if abs(c - strike) > 1e-6]:
            tried.append(k)
            opt = Option(und_sym, expiry, float(k), "P", "CBOE", tradingClass=t_class)
            await self.ib.qualifyContractsAsync(opt)
            if getattr(opt, "conId", 0):
                return float(k), opt
        raise RuntimeError(
            f"Could not qualify CBOE {t_class} {expiry} put near strike {strike:.0f} (tried {tried})"
        )

    async def _qualify_bwb_legs(self, plan: BwbPlan):
        t0 = time.monotonic()
        expiry = plan.day.replace("-", "")
        und_sym = "XSP" if plan.symbol == "XSP" else "SPX"
        t_class = "XSP" if plan.symbol == "XSP" else "SPXW"
        step = 1.0 if plan.symbol == "XSP" else 5.0
        k_mid_target = round(plan.k_mid / step) * step
        k_hi_target = max(k_mid_target + step, round(plan.k_hi / step) * step)
        w1_target = k_hi_target - k_mid_target
        w2_target = max(w1_target + step, round((plan.k_mid - plan.k_lo) / step) * step)
        k_lo_target = k_mid_target - w2_target

        try:
            k_mid, opt_mid = await self._qualify_single_put(
                und_sym, expiry, k_mid_target, t_class,
                [k_mid_target - step, k_mid_target + step, round(k_mid_target / 10.0) * 10.0],
            )
            k_hi_pref = max(k_mid + step, k_hi_target)
            k_hi, opt_hi = await self._qualify_single_put(
                und_sym, expiry, k_hi_pref, t_class,
                [k_hi_pref + step, max(k_mid + step, k_hi_pref - step), round(k_hi_pref / 10.0) * 10.0],
            )
            w1_act = k_hi - k_mid
            k_lo_max = k_mid - (w1_act + step)
            k_lo_pref = min(k_lo_max, k_lo_target)
            lo_cands = [
                c for c in (
                    k_lo_pref - step,
                    k_lo_pref + step,
                    math.floor(k_lo_pref / 10.0) * 10.0,
                    math.ceil(k_lo_pref / 10.0) * 10.0,
                    math.floor(k_lo_pref / 25.0) * 25.0,
                )
                if c <= k_lo_max + 1e-6
            ]
            k_lo, opt_lo = await self._qualify_single_put(und_sym, expiry, k_lo_pref, t_class, lo_cands)
        except Exception as exc:
            err = self.recent_errors_since(t0)
            raise RuntimeError(f"{exc}" + (f" | IBKR: {err}" if err else "")) from exc

        return und_sym, step, k_hi, k_mid, k_lo, opt_hi, opt_mid, opt_lo

    async def _poll_option_legs(self, legs: list, mdt: int, wait_s: float) -> list[dict[str, float]]:
        """Subscribes option legs under MarketDataType=mdt, polls until bid/ask populate or wait_s elapses."""
        t0 = time.monotonic()
        self.ib.reqMarketDataType(mdt)
        tkrs = [self.ib.reqMktData(leg, "", False, False) for leg in legs]
        try:
            steps = max(1, int(round(wait_s / 0.25)))
            for i in range(steps):
                await asyncio.sleep(0.25)
                ready = 0
                for t in tkrs:
                    b = float(getattr(t, "bid", math.nan) or math.nan)
                    a = float(getattr(t, "ask", math.nan) or math.nan)
                    if mdt in (3, 4) and not (math.isfinite(b) and math.isfinite(a) and a > 0.0 and b >= 0.0):
                        b = float(getattr(t, "delayedBid", math.nan) or math.nan)
                        a = float(getattr(t, "delayedAsk", math.nan) or math.nan)
                    if math.isfinite(b) and math.isfinite(a) and a > 0.0 and b >= 0.0 and a >= b:
                        ready += 1
                if ready == len(tkrs):
                    break
                if mdt == 1 and i >= 3 and ready == 0:
                    err = self.recent_errors_since(t0)
                    if any(code in err for code in ("[354]", "[10089]", "[10167]")):
                        break

            out: list[dict[str, float]] = []
            for t in tkrs:
                b = float(getattr(t, "bid", math.nan) or math.nan)
                a = float(getattr(t, "ask", math.nan) or math.nan)
                if mdt in (3, 4) and not (math.isfinite(b) and math.isfinite(a) and a > 0.0 and b >= 0.0):
                    b = float(getattr(t, "delayedBid", math.nan) or math.nan)
                    a = float(getattr(t, "delayedAsk", math.nan) or math.nan)
                last_px = float(getattr(t, "last", math.nan) or math.nan)
                if mdt in (3, 4) and not (math.isfinite(last_px) and last_px > 0.0):
                    last_px = float(getattr(t, "delayedLast", math.nan) or math.nan)
                close_px = float(getattr(t, "close", math.nan) or math.nan)
                if mdt in (3, 4) and not (math.isfinite(close_px) and close_px > 0.0):
                    close_px = float(getattr(t, "delayedClose", math.nan) or math.nan)
                mg = getattr(t, "modelGreeks", None)
                mod_px = float(getattr(mg, "optPrice", math.nan) or math.nan) if mg else math.nan
                out.append(
                    {"bid": b, "ask": a, "last": last_px, "close": close_px, "model": mod_px}
                )
            return out
        finally:
            for leg in legs:
                try:
                    self.ib.cancelMktData(leg)
                except Exception:
                    pass

    async def quote_bwb_spread(self, plan: BwbPlan) -> BwbQuoteSnapshot:
        """Snapshots CBOE/OPRA NBBO bid/ask on all 3 BWB put strikes with delayed-OPRA fallback."""
        if not self.is_connected():
            raise ConnectionError("not connected to TWS")
        self.last_quote_warning = ""
        t0 = time.monotonic()
        _, step, k_hi, k_mid, k_lo, opt_hi, opt_mid, opt_lo = await self._qualify_bwb_legs(plan)
        legs = [opt_hi, opt_mid, opt_lo]
        strikes = [k_hi, k_mid, k_lo]
        scale = 0.1 if plan.symbol == "XSP" else 1.0

        def _valid_ba(d: dict[str, float]) -> bool:
            b, a = d["bid"], d["ask"]
            return math.isfinite(b) and math.isfinite(a) and a > 0.0 and b >= 0.0 and a >= b

        live_snaps = await self._poll_option_legs(legs, mdt=1, wait_s=3.5)
        n_live = sum(1 for d in live_snaps if _valid_ba(d))
        merged = list(live_snaps)
        used_delayed = 0

        if n_live < 3 and self.cfg.mode != "live":
            try:
                dly_snaps = await self._poll_option_legs(legs, mdt=3, wait_s=4.0)
                for i in range(3):
                    if not _valid_ba(merged[i]) and _valid_ba(dly_snaps[i]):
                        merged[i] = dly_snaps[i]
                        used_delayed += 1
                    elif not _valid_ba(merged[i]):
                        for k_f in ("model", "last", "close"):
                            if not (math.isfinite(merged[i][k_f]) and merged[i][k_f] > 0.0):
                                merged[i][k_f] = dly_snaps[i][k_f]
            finally:
                self.ib.reqMarketDataType(1)

        def _extract_ba(d: dict[str, float], k_strike: float) -> tuple[float, float, bool]:
            if _valid_ba(d):
                return d["bid"], d["ask"], True
            ref = math.nan
            for k_f in ("model", "last", "close"):
                v = d[k_f]
                if math.isfinite(v) and v > 0.0:
                    ref = v
                    break
            if not (math.isfinite(ref) and ref > 0.0):
                z = math.log(k_strike / plan.spot) / max(plan.iv1d * SQRT_T_0DTE, 1e-6)
                sig = plan.iv1d * float(iv_ratio_0dte(z))
                ref = bs_price_0dte(plan.spot, k_strike, T_0DTE, 0.045, sig, is_call=False)
            hs = half_spread_pts(ref) * scale
            return max(0.0, ref - hs), ref + hs, False

        b_hi, a_hi, ok_hi = _extract_ba(merged[0], strikes[0])
        b_m, a_m, ok_m = _extract_ba(merged[1], strikes[1])
        b_lo, a_lo, ok_lo = _extract_ba(merged[2], strikes[2])
        n_valid = int(ok_hi) + int(ok_m) + int(ok_lo)

        if n_live == 3:
            src = "ibkr_nbbo"
        elif n_valid == 3 and used_delayed > 0:
            src = "ibkr_delayed"
            err = self.recent_errors_since(t0)
            self.last_quote_warning = (
                f"Used delayed OPRA quotes on {used_delayed}/3 legs"
                + (f" ({err})" if err else " (live OPRA feed pending Gateway restart)")
            )
        elif n_valid >= 1:
            src = "ibkr_partial"
            err = self.recent_errors_since(t0)
            self.last_quote_warning = (
                f"Partial option quotes ({n_valid}/3 legs had bid/ask)"
                + (f" | IBKR: {err}" if err else "")
            )
        else:
            src = "model_fallback"
            err = self.recent_errors_since(t0)
            self.last_quote_warning = (
                "0/3 option legs returned IBKR bid/ask quotes"
                + (f" | IBKR: {err}" if err else " (check OPRA subscription / market hours)")
            )

        mid_hi = 0.5 * (b_hi + a_hi)
        mid_m = 0.5 * (b_m + a_m)
        mid_lo = 0.5 * (b_lo + a_lo)

        live_mid = 2.0 * mid_m - mid_hi - mid_lo
        nat_cred = 2.0 * b_m - a_hi - a_lo
        hs_sum = 0.5 * ((a_hi - b_hi) + 2.0 * (a_m - b_m) + (a_lo - b_lo))
        est_slip = max(0.05 * scale, 0.35 * hs_sum)
        est_net = live_mid - est_slip - plan.fee_pts
        w_risk = max(step, 2.0 * k_mid - k_hi - k_lo)

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

        if q.source == "model_fallback":
            warn_detail = self.last_quote_warning or "0/3 option legs quoted by IBKR"
            return BwbFillResult(
                filled=False,
                contracts=0.0,
                gross_credit_pts=0.0,
                commission_dollars=0.0,
                net_credit_pts=0.0,
                limit_credit_pts=floor_gross,
                order_id=0,
                status=f"Aborted: no IBKR option quotes ({warn_detail})",
            )

        if floor_net > 0.0 and q.live_mid_credit_pts < floor_gross - 1e-6:
            return BwbFillResult(
                filled=False,
                contracts=0.0,
                gross_credit_pts=0.0,
                commission_dollars=0.0,
                net_credit_pts=0.0,
                limit_credit_pts=floor_gross,
                order_id=0,
                status=(
                    f"Skipped: live mid {q.live_mid_credit_pts:.2f}pt < min gross floor "
                    f"{floor_gross:.2f}pt (src={q.source})"
                ),
            )

        und_sym, _, k_hi, k_mid, k_lo, opt_hi, opt_mid, opt_lo = await self._qualify_bwb_legs(plan)
        bag = Contract(
            symbol=und_sym,
            secType="BAG",
            currency="USD",
            exchange="CBOE",
            comboLegs=[
                ComboLeg(conId=opt_hi.conId, ratio=1, action="BUY", exchange="CBOE"),
                ComboLeg(conId=opt_mid.conId, ratio=2, action="SELL", exchange="CBOE"),
                ComboLeg(conId=opt_lo.conId, ratio=1, action="BUY", exchange="CBOE"),
            ],
        )
        qty = max(1, int(round(contracts)))
        tick = 0.01 if plan.symbol == "XSP" else 0.05

        def _snap_tick(val: float) -> float:
            return round(round(val / tick) * tick, 2)

        floor_tick = round(math.ceil((floor_gross - 1e-9) / tick) * tick, 2) if floor_gross > 0 else tick
        lmt_1 = max(floor_tick, _snap_tick(q.live_mid_credit_pts - 0.5 * q.est_slip_pts))
        lmt_2 = max(floor_tick, _snap_tick(q.est_net_credit_pts + plan.fee_pts))

        use_delayed_for_paper = self.cfg.mode == "paper" and q.source == "ibkr_delayed"
        if use_delayed_for_paper:
            self.ib.reqMarketDataType(3)

        t_order_start = time.monotonic()
        states_seen: list[str] = []
        why_held = ""
        cur_lmt = lmt_1

        try:
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

            timeout_s = max(5.0, float(self.cfg.bwb.entry_timeout_sec))
            half_s = timeout_s / 2.0
            t0 = asyncio.get_event_loop().time()
            stepped = False

            while not trade.isDone():
                st_cur = str(trade.orderStatus.status or "")
                if st_cur and (not states_seen or states_seen[-1] != st_cur):
                    states_seen.append(st_cur)
                if getattr(trade.orderStatus, "whyHeld", ""):
                    why_held = str(trade.orderStatus.whyHeld)[:80]
                if st_cur == "Inactive":
                    break

                elapsed = asyncio.get_event_loop().time() - t0
                if elapsed >= timeout_s:
                    break
                if (not stepped) and elapsed >= half_s and lmt_2 < lmt_1 - 1e-6:
                    stepped = True
                    cur_lmt = lmt_2
                    order.lmtPrice = -cur_lmt
                    trade = self.ib.placeOrder(bag, order)

                await asyncio.sleep(min(2.0, max(0.2, timeout_s - elapsed)))

            final_st = str(trade.orderStatus.status or "")
            if final_st and (not states_seen or states_seen[-1] != final_st):
                states_seen.append(final_st)
            if getattr(trade.orderStatus, "whyHeld", ""):
                why_held = str(trade.orderStatus.whyHeld)[:80]

            if not trade.isDone():
                self.ib.cancelOrder(order)
                for _ in range(12):
                    if trade.isDone():
                        break
                    await asyncio.sleep(0.25)
        finally:
            if use_delayed_for_paper:
                self.ib.reqMarketDataType(1)

        filled_qty = float(trade.orderStatus.filled or 0.0)
        if filled_qty <= 0.0:
            oid = int(order.orderId or 0)
            err_detail = self.format_req_errors(oid) or self.recent_errors_since(t_order_start)
            traj = "->".join(states_seen) if states_seen else str(trade.orderStatus.status or "Unknown")
            parts = [
                f"Unfilled ({traj})",
                f"lmt={cur_lmt:.2f}pt (initial {lmt_1:.2f}pt)",
                f"mid={q.live_mid_credit_pts:.2f}/nat={q.natural_credit_pts:.2f} ({q.source})",
            ]
            if why_held:
                parts.append(f"whyHeld={why_held}")
            if err_detail:
                parts.append(f"IBKR: {err_detail}")
            return BwbFillResult(
                filled=False,
                contracts=0.0,
                gross_credit_pts=0.0,
                commission_dollars=0.0,
                net_credit_pts=0.0,
                limit_credit_pts=cur_lmt,
                order_id=oid,
                status=" | ".join(parts)[:240],
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
        from ib_async import Contract, Order

        await self.ib.reqPositionsAsync()
        opt_items = [
            item
            for item in self.ib.portfolio(self.account_id)
            if item.position != 0
            and item.contract.secType == "OPT"
            and item.contract.symbol in ("SPX", "SPXW", "XSP")
        ]
        if not opt_items:
            raise LookupError(f"No open SPX/XSP option legs found to close for {trade_key}")

        # Close short legs (BUY to close) first so margin never spikes while flattening
        opt_items.sort(key=lambda it: 0 if it.position < 0 else 1)
        trades = []
        total_qty = 0.0
        t0 = time.monotonic()
        for item in opt_items:
            c = item.contract
            leg_contract = Contract(
                conId=c.conId,
                symbol=c.symbol,
                secType="OPT",
                exchange="CBOE",
                currency="USD",
            )
            action = "BUY" if item.position < 0 else "SELL"
            qty = abs(float(item.position))
            total_qty += qty
            order = Order(
                action=action,
                totalQuantity=qty,
                orderType=how,
                tif="DAY",
                transmit=True,
                orderRef="bwb-manual",
                account=self.account_id,
            )
            trades.append(self.ib.placeOrder(leg_contract, order))

        await asyncio.sleep(1.5)
        bad = [
            tr
            for tr in trades
            if str(tr.orderStatus.status or "") in ("Cancelled", "ApiCancelled", "Inactive")
        ]
        if bad:
            oid = int(bad[0].order.orderId or 0)
            err = self.format_req_errors(oid) or self.recent_errors_since(t0)
            raise RuntimeError(f"Close order {oid} rejected ({bad[0].orderStatus.status})" + (f": {err}" if err else ""))

        first = trades[0]
        return OrderInfo(
            order_id=int(first.order.orderId or 0),
            symbol=trade_key,
            action="CLOSE",
            order_type=how,
            quantity=total_qty,
            limit_price=None,
            stop_price=None,
            status=str(first.orderStatus.status or "Submitted"),
            role="manual",
        )
