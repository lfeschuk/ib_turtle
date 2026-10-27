"""Broker connections behind one interface: IBKR TWS through ib_async, and a simulated broker for demo mode."""
from __future__ import annotations

import asyncio
import logging
import math
import zlib
from dataclasses import dataclass
from datetime import date, datetime, time as dtime

from . import market_calendar as mc
from .borrow import BorrowTable
from .config import LiveConfig

log = logging.getLogger(__name__)

DONE_STATES = {"Cancelled", "ApiCancelled", "Inactive", "Filled"}
ROLE_BY_REF = {"gs-entry": "entry", "gs-stop": "stop", "gs-target": "target", "gs-exit": "exit", "gs-manual": "manual"}


class ReadOnlyError(RuntimeError):
    """Raised when something tries to send or cancel an order in read-only (shadow) mode."""


@dataclass
class Bar:
    day: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    raw_close: float | None = None
    dollar_vol: float | None = None


@dataclass
class PositionInfo:
    symbol: str
    shares: float          # negative for a short
    avg_cost: float
    market_price: float
    unrealized_pnl: float


@dataclass
class OrderInfo:
    order_id: int
    symbol: str
    action: str
    order_type: str
    quantity: float
    limit_price: float | None
    stop_price: float | None
    status: str
    role: str
    parent_id: int = 0


@dataclass
class FillInfo:
    exec_id: str
    symbol: str
    side: str
    shares: float
    price: float
    day: str
    role: str
    commission: float = 0.0


@dataclass
class AccountInfo:
    account_id: str
    net_liquidation: float
    cash: float
    maint_margin: float
    excess_liquidity: float


def round_price(price: float) -> float:
    """US stock tick size: a cent at $1 and above, 1/100 cent below $1."""
    return round(price, 2) if price >= 1.0 else round(price, 4)


def _num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and abs(v) < 1e300 else None


def symbol_index(symbol: str) -> int:
    """Stable integer per symbol, used only to break exact score ties the same way every run."""
    return zlib.crc32(symbol.encode()) & 0x7FFFFFFF


class IBKRBroker:
    """TWS or IB Gateway through ib_async. In read-only mode it never sends or cancels orders."""

    def __init__(self, cfg: LiveConfig, readonly: bool, borrow: BorrowTable):
        self.cfg = cfg
        self.readonly = readonly
        self.borrow = borrow
        self.ib = None
        self.account_id = ""
        self._contracts: dict = {}

    async def connect(self) -> None:
        from ib_async import IB  # imported here so demo mode runs without TWS

        if self.ib is None:
            self.ib = IB()
        if self.ib.isConnected():
            return
        await self.ib.connectAsync(self.cfg.tws_host, self.cfg.tws_port, clientId=self.cfg.client_id,
                                   readonly=self.readonly, timeout=20)
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
        return mc.trading_days_between(date.fromisoformat(d0), date.fromisoformat(d1))

    async def account(self) -> AccountInfo:
        values = await self.ib.accountSummaryAsync(self.account_id)
        d: dict[str, float] = {}
        for v in values:
            if v.account == self.account_id and v.currency in ("USD", "BASE", ""):
                val = _num(v.value)
                if val is not None:
                    d[v.tag] = val
        nan = float("nan")
        return AccountInfo(self.account_id, d.get("NetLiquidation", nan), d.get("TotalCashValue", nan),
                           d.get("MaintMarginReq", nan), d.get("ExcessLiquidity", nan))

    async def positions(self) -> list[PositionInfo]:
        out = []
        for item in self.ib.portfolio(self.account_id):
            if item.contract.secType != "STK" or not item.position:
                continue
            out.append(PositionInfo(item.contract.symbol, float(item.position), float(item.averageCost),
                                    float(item.marketPrice), float(item.unrealizedPNL)))
        return out

    async def open_orders(self) -> list[OrderInfo]:
        out = []
        for tr in self.ib.openTrades():
            o = tr.order
            out.append(OrderInfo(o.orderId, tr.contract.symbol, o.action, o.orderType, float(o.totalQuantity),
                                 _num(o.lmtPrice), _num(o.auxPrice), tr.orderStatus.status,
                                 ROLE_BY_REF.get(o.orderRef, "other"), o.parentId))
        return out

    async def fills_today(self) -> list[FillInfo]:
        today = self.today().isoformat()
        out = []
        for f in self.ib.fills():
            ex = f.execution
            day = ex.time.astimezone(mc.NY).date().isoformat() if ex.time else today
            if day == today:
                report = getattr(f, "commissionReport", None)
                commission = _num(getattr(report, "commission", None)) or 0.0
                out.append(FillInfo(ex.execId, f.contract.symbol, ex.side, float(ex.shares), float(ex.price), day,
                                    ROLE_BY_REF.get(ex.orderRef, "other"), commission))
        return out

    async def movers(self) -> list[str]:
        from ib_async import ScannerSubscription, TagValue

        filters = [TagValue("priceAbove", "0.5"), TagValue("priceBelow", "100"), TagValue("volumeAbove", "100000")]
        symbols: list[str] = []
        for code in ("TOP_PERC_GAIN", "HOT_BY_VOLUME"):
            sub = ScannerSubscription(instrument="STK", locationCode="STK.US.MAJOR", scanCode=code, numberOfRows=50)
            for row in await self.ib.reqScannerDataAsync(sub, [], filters):
                sym = row.contractDetails.contract.symbol
                if sym not in symbols:
                    symbols.append(sym)
        return symbols

    async def _contract(self, symbol: str):
        from ib_async import Stock

        if symbol not in self._contracts:
            qualified = await self.ib.qualifyContractsAsync(Stock(symbol, "SMART", "USD"))
            if not qualified:
                raise LookupError(symbol)
            self._contracts[symbol] = qualified[0]
        return self._contracts[symbol]

    async def daily_bars(self, symbol: str, days: int = 280) -> list[Bar]:
        contract = await self._contract(symbol)
        # a long history for the signal rules; a short window (in calendar days) for the daily position update
        duration = "14 M" if days > 60 else f"{days * 2 + 5} D"
        bars = await self.ib.reqHistoricalDataAsync(contract, endDateTime="", durationStr=duration,
                                                    barSizeSetting="1 day", whatToShow="TRADES", useRTH=True,
                                                    formatDate=1, timeout=30)
        await asyncio.sleep(0.4)  # stay well inside IBKR's history request pacing
        out = [Bar(str(b.date), float(b.open), float(b.high), float(b.low), float(b.close), float(b.volume))
               for b in bars]
        return out[-days:]

    async def gate_info(self, symbol: str, bars: list[Bar]) -> dict:
        prior = bars[:-1]
        nan = float("nan")
        return dict(ticker_idx=symbol_index(symbol), prev_raw_vol=prior[-1].volume if prior else 0.0,
                    is_top500_prev=False,  # irrelevant here: candidates must trade under $50M/day on average
                    prior_lifetime_bars=sum(1 for b in prior if b.close > 0 and b.volume > 100),
                    split_in_window=False, corrupt_vendor_bar=False, pit_mcap_prev=nan, pit_shares_prev=nan)

    async def borrow_check(self, symbol: str, bars: list[Bar]) -> dict:
        """Shortable shares from TWS, borrow fee from IBKR's daily file, and a split sanity check."""
        contract = await self._contract(symbol)
        ticker = self.ib.reqMktData(contract, "236", False, False)
        try:
            for _ in range(24):
                await asyncio.sleep(0.25)
                if _num(ticker.shortableShares) is not None and _num(ticker.close) is not None:
                    break
        finally:
            self.ib.cancelMktData(contract)
        shares = _num(ticker.shortableShares) or 0.0
        prev_close = _num(ticker.close)
        # Yesterday's close from the quote should match the history; a mismatch usually means a split today.
        split_flag = prev_close is not None and len(bars) >= 2 and abs(prev_close / bars[-2].close - 1.0) > 0.05
        return {"shortable": shares > 0, "available": shares, "fee": self.borrow.fee(symbol), "split_flag": split_flag}

    def _guard_write(self) -> None:
        if self.readonly or self.cfg.mode == "shadow":
            raise ReadOnlyError("read-only mode: no orders")
        if not self.is_connected():
            raise ConnectionError("not connected to TWS")

    async def place_short_bracket(self, symbol: str, shares: float, notional: float, limit_price: float,
                                  stop_price: float, target_price: float, tag: str, equity: float) -> OrderInfo:
        self._guard_write()
        from ib_async import Order

        contract = await self._contract(symbol)
        qty = int(shares)
        if qty <= 0:
            raise ValueError("order size rounds to zero shares")
        acct = self.account_id
        parent = Order(action="SELL", totalQuantity=qty, orderType="LOC", lmtPrice=round_price(limit_price),
                       tif="DAY", transmit=False, orderRef="gs-entry", account=acct)
        parent.orderId = self.ib.client.getReqId()
        oca = f"gs-{symbol}-{self.today().isoformat()}"
        stop = Order(action="BUY", totalQuantity=qty, orderType="STP", auxPrice=round_price(stop_price), tif="GTC",
                     parentId=parent.orderId, ocaGroup=oca, ocaType=1, transmit=False, orderRef="gs-stop",
                     account=acct)
        target = Order(action="BUY", totalQuantity=qty, orderType="LMT", lmtPrice=round_price(target_price),
                       tif="GTC", parentId=parent.orderId, ocaGroup=oca, ocaType=1, transmit=True,
                       orderRef="gs-target", account=acct)
        trade = self.ib.placeOrder(contract, parent)
        self.ib.placeOrder(contract, stop)
        self.ib.placeOrder(contract, target)
        return OrderInfo(parent.orderId, symbol, "SELL", "LOC", qty, parent.lmtPrice, None, trade.orderStatus.status,
                         "entry")

    async def cancel_brackets(self, symbol: str) -> int:
        self._guard_write()
        trades = [t for t in self.ib.openTrades()
                  if t.contract.symbol == symbol and t.order.orderRef in ("gs-entry", "gs-stop", "gs-target")]
        for t in trades:
            self.ib.cancelOrder(t.order)
        for _ in range(40):
            if all(t.orderStatus.status in DONE_STATES for t in trades):
                break
            await asyncio.sleep(0.25)
        return len(trades)

    async def cover(self, symbol: str, shares: float, how: str) -> OrderInfo:
        self._guard_write()
        from ib_async import Order

        contract = await self._contract(symbol)
        qty = int(round(abs(shares)))
        if how == "MOC":
            order = Order(action="BUY", totalQuantity=qty, orderType="MOC", tif="DAY", orderRef="gs-exit",
                          account=self.account_id)
        elif how == "MKT":
            order = Order(action="BUY", totalQuantity=qty, orderType="MKT", tif="DAY", orderRef="gs-manual",
                          account=self.account_id)
        elif how == "OPG":
            order = Order(action="BUY", totalQuantity=qty, orderType="MKT", tif="OPG", orderRef="gs-manual",
                          account=self.account_id)
        else:
            raise ValueError(how)
        trade = self.ib.placeOrder(contract, order)
        return OrderInfo(order.orderId, symbol, "BUY", order.orderType, qty, None, None, trade.orderStatus.status,
                         ROLE_BY_REF[order.orderRef])


class SimBroker:
    """Demo mode: replays history through the mock IBKR broker, one trading day per step."""

    def __init__(self, cfg: LiveConfig):
        import numpy as np
        import pandas as pd

        from ..adapters import YahooReplayAdapter
        from ..models import EngineConfig

        self._np, self._pd = np, pd
        self.cfg = cfg
        self.adp = YahooReplayAdapter(use_nasdaq_verified_bars=True, include_edgar_pit=True)
        self.engine_cfg = EngineConfig(initial_capital=cfg.initial_capital,
                                       pos_pct=cfg.sizing.static_pct, locate_fee_pct=0.0,
                                       borrow_annual=cfg.borrow_annual, max_borrow_annual=cfg.max_borrow_annual,
                                       slip_per_side=cfg.slip_per_side, tax_rate=0.25, enforce_clean_data=True,
                                       enforce_whale_gate=False, max_positions=cfg.max_positions,
                                       hold_days=cfg.hold_days, cooldown_days=cfg.cooldown_days)
        self.t0 = int(np.searchsorted(self.adp.dates, pd.Timestamp(cfg.demo_start)))
        self.reset()

    def reset(self) -> None:
        from ..mock_ibkr import MockIBKRBroker

        self.mock = MockIBKRBroker(self.adp, self.engine_cfg, account_id="DU-DEMO-0001")
        self.mock.connect()
        self.account_id = self.mock.account_id
        self.t = self.t0 - 1

    @property
    def finished(self) -> bool:
        return self.t >= self.adp.T - 1

    def days_left(self) -> int:
        return self.adp.T - 1 - self.t

    def progress(self) -> dict:
        return {"day": self.today().isoformat(), "done": self.t - self.t0 + 1, "total": self.adp.T - self.t0}

    def begin_day(self) -> None:
        self.t += 1
        self.mock.step_market_open_and_intraday(self.t, is_first_day=(self.t == self.t0))
        self.mock.step_eod_decision_window(self.t)

    def end_day(self) -> None:
        self.mock.step_eod_close(self.t)

    async def connect(self) -> None:
        return None

    def is_connected(self) -> bool:
        return True

    async def disconnect(self) -> None:
        return None

    def today(self) -> date:
        return self.adp.dates[max(self.t, self.t0)].date()

    def now(self) -> datetime:
        return datetime.combine(self.today(), dtime(15, 45), tzinfo=mc.NY)

    def _index(self, day: str) -> int:
        return int(self._np.searchsorted(self.adp.dates, self._pd.Timestamp(day)))

    def trading_days_between(self, d0: str, d1: str) -> int:
        return max(0, self._index(d1) - self._index(d0))

    async def account(self) -> AccountInfo:
        from ..sizing import short_maintenance_per_share

        s = self.mock.accountSummary()
        maint = sum(short_maintenance_per_share(p.raw_mark_price) * abs(p.position) for p in self.mock.positions())
        return AccountInfo(self.account_id, s["NetLiquidation"], s["TotalCashValue"], maint,
                           s["NetLiquidation"] - maint)

    async def positions(self) -> list[PositionInfo]:
        return [PositionInfo(p.contract.symbol, p.position, p.avgCost, p.raw_mark_price,
                             p.notional_0 * (1.0 - p.raw_mark_price / p.avgCost)) for p in self.mock.positions()]

    async def open_orders(self) -> list[OrderInfo]:
        role = {"BRACKET_STOP": "stop", "BRACKET_TARGET": "target"}
        return [OrderInfo(tr.order.orderId, tr.contract.symbol, tr.order.action, tr.order.orderType,
                          tr.order.totalQuantity, tr.order.lmtPrice or None, tr.order.auxPrice or None,
                          tr.orderStatus.status, role.get(tr.order.orderRef, "other"), tr.order.parentId)
                for tr in self.mock.openTrades()]

    async def fills_today(self) -> list[FillInfo]:
        role = {"entry": "entry", "stop": "stop", "target": "target", "time": "exit"}
        out = []
        for ex in self.mock.executions(today_only=True):
            r = "manual" if ex.orderRef == "MANUAL_COVER" else role.get(ex.exit_reason, "other")
            out.append(FillInfo(ex.execId, ex.symbol, ex.side, ex.shares, ex.price, str(ex.time.date()), r))
        return out

    async def movers(self) -> list[str]:
        return [c.symbol for c in self.mock.reqScannerData()]

    async def daily_bars(self, symbol: str, days: int = 260) -> list[Bar]:
        from ..mock_ibkr import MockIBContract

        bars = self.mock.reqHistoricalData(MockIBContract(symbol), durationStr=f"{days} D")
        return [Bar(str(b.date.date()), b.open, b.high, b.low, b.close, b.volume, b.raw_close, b.dollar_vol)
                for b in bars]

    async def gate_info(self, symbol: str, bars: list[Bar]) -> dict:
        from ..mock_ibkr import MockIBContract

        return self.mock.reqContractMetadata(MockIBContract(symbol))

    async def borrow_check(self, symbol: str, bars: list[Bar]) -> dict:
        from ..mock_ibkr import MockIBContract

        q = self.mock.reqShortableQuote(MockIBContract(symbol))
        return {"shortable": q.shortable, "available": q.available_shares, "fee": q.fee_rate_annual,
                "split_flag": False}

    async def place_short_bracket(self, symbol: str, shares: float, notional: float, limit_price: float,
                                  stop_price: float, target_price: float, tag: str, equity: float) -> OrderInfo:
        from ..mock_ibkr import MockIBContract, MockIBOrder

        contract = self.mock.qualifyContracts(MockIBContract(symbol))[0]
        pid, sid, tid = self.mock.getReqId(), self.mock.getReqId(), self.mock.getReqId()
        oca = f"OCA_{symbol}_{self.t}_{pid}"
        extra = self.engine_cfg.slip_per_side + self.engine_cfg.stop_extra_slip
        stop = MockIBOrder(orderId=sid, parentId=pid, action="BUY", totalQuantity=shares, orderType="STPLMT",
                           auxPrice=stop_price, lmtPrice=stop_price * (1.0 + extra), tif="GTC", ocaGroup=oca,
                           ocaType=1, outsideRth=True, transmit=False, orderRef="BRACKET_STOP")
        target = MockIBOrder(orderId=tid, parentId=pid, action="BUY", totalQuantity=shares, orderType="LMT",
                             lmtPrice=target_price, tif="GTC", ocaGroup=oca, ocaType=1, outsideRth=True,
                             transmit=True, orderRef="BRACKET_TARGET")
        parent = MockIBOrder(orderId=pid, action="SELL", totalQuantity=shares, orderType="LMT", lmtPrice=limit_price,
                             auxPrice=equity, tif="DAY", transmit=False, orderRef=f"ENTRY_SHORT_{tag}",
                             notional_dollars=notional, setups_str=tag)
        # children first, then the parent, as the mock (and IBKR's transmit flag) expects
        self.mock.placeOrder(contract, stop)
        self.mock.placeOrder(contract, target)
        trade = self.mock.placeOrder(contract, parent)
        return OrderInfo(pid, symbol, "SELL", "LOC", shares, limit_price, None, trade.orderStatus.status, "entry")

    async def cancel_brackets(self, symbol: str) -> int:
        n = 0
        for tr in self.mock.openTrades():
            if tr.contract.symbol == symbol:
                self.mock.cancelOrder(tr.order)
                n += 1
        return n

    async def cover(self, symbol: str, shares: float, how: str) -> OrderInfo:
        from ..mock_ibkr import MockIBOrder

        pos = next((p for p in self.mock.positions() if p.contract.symbol == symbol), None)
        if pos is None:
            raise LookupError(symbol)
        phase = self.mock.clock_phase
        self.mock.clock_phase = "EOD_1550_DECISION"  # the mock fills covers at the day's close
        try:
            order = MockIBOrder(action="BUY", totalQuantity=abs(pos.position), orderType="LMT", tif="DAY",
                                ocaGroup=pos.oca_group, ocaType=1, transmit=True,
                                orderRef="TIME_EXIT_T3" if how == "MOC" else "MANUAL_COVER")
            trade = self.mock.placeOrder(pos.contract, order)
        finally:
            self.mock.clock_phase = phase
        return OrderInfo(order.orderId, symbol, "BUY", how, abs(pos.position), None, None, trade.orderStatus.status,
                         "exit" if how == "MOC" else "manual")
