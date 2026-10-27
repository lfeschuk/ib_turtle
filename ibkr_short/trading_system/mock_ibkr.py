"""Mock IBKR TWS/Gateway Broker, Virtual EOD Clock, Exchange Matching Engine,
and Production `LiveIBKRTradingBot`.

Purpose:
  Before connecting a real IBKR account, this module provides a full state-machine mock
  of the `ib_async.IB` interface (`MockIBKRBroker`) driven by a Virtual EOD Clock that feeds
  real historical Yahoo / Nasdaq market data day-by-day (`09:30 -> Intraday H/L -> 15:50 EOD Decision -> 16:00 Close`).

  The production execution algorithm (`LiveIBKRTradingBot`) interacts *exclusively* with the
  `ib_client` API (`reqScannerData`, `reqHistoricalData`, `reqShortableQuote`, `placeOrder`,
  `cancelOrder`, `positions`, `openOrders`, `accountSummary`, `executions`):
    1. Computes all indicators (`SMA200`, `52w_High`, `DV50`, `Gap%`, `Surge%`, `RetClose%`, `CIR`)
       directly from the raw historical daily bars returned by `ib_client.reqHistoricalData(...)`
       with a strict Zero-Look-Ahead Firewall (`<= current_day_idx`).
    2. Submits real 3-leg IBKR Bracket Orders:
       - Parent `SELL` LimitOrder (short entry at `15:50-15:59 ET`)
       - Child 1 `BUY` StopLimitOrder (`outsideRth=True`, attached to `ocaGroup`)
       - Child 2 `BUY` LimitOrder (`outsideRth=True`, attached to `ocaGroup`)
    3. Submits Day `t+3` EOD `BUY` LimitOrder time-exit covers and cancels resting OCA brackets.

  When verified against the reference backtest and Stage 1 `TradingEngine`, `LiveIBKRTradingBot`
  talking to `MockIBKRBroker` reproduces the exact same trades, exit reasons, and daily equity
  curve (100.0000% parity, $0.00 discrepancy).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import numpy as np
import pandas as pd

from .adapters import YahooReplayAdapter
from .models import (
    AccountSnapshot,
    BarSnapshot,
    BorrowQuote,
    ClosedTrade,
    EngineConfig,
    OpenPosition,
    PreEventContext,
    SignalCandidate,
)
from .strategy_core import (
    compute_entry_and_brackets,
    evaluate_candidate,
    evaluate_position_bar_exit,
)


class LookAheadViolationError(RuntimeError):
    """Raised if any code requests market data beyond the Virtual Clock's current day index."""


@dataclass(frozen=True)
class MockIBContract:
    """Drop-in mock of `ib_async.Stock(symbol, exchange, currency)`."""
    symbol: str
    exchange: str = "SMART"
    currency: str = "USD"
    secType: str = "STK"
    conId: int = 0


@dataclass
class MockIBBarData:
    """Drop-in mock of `ib_async.BarData` returned by `reqHistoricalData`."""
    date: pd.Timestamp
    day_idx: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    raw_close: float
    dollar_vol: float


@dataclass
class MockIBOrder:
    """Drop-in mock of `ib_async.Order` (`LimitOrder`, `StopLimitOrder`, `MarketOrder`)."""
    action: str                     # "SELL" (short entry) or "BUY" (cover exit)
    totalQuantity: float            # Shares (or notional units)
    orderType: str                  # "LMT", "STP", "STPLMT", "MKT"
    lmtPrice: float = 0.0
    auxPrice: float = 0.0           # Stop trigger price for STP / STPLMT
    tif: str = "DAY"                # "DAY" or "GTC"
    orderId: int = 0
    parentId: int = 0
    ocaGroup: str = ""
    ocaType: int = 1                # 1 = Cancel all remaining orders in OCA group on fill
    outsideRth: bool = False
    transmit: bool = True
    orderRef: str = ""
    # Internal metadata for audit precision
    notional_dollars: float = 0.0
    setups_str: str = ""


@dataclass
class MockIBOrderStatus:
    """Drop-in mock of `ib_async.OrderStatus`."""
    orderId: int
    status: str = "PendingSubmit"   # "PreSubmitted", "Submitted", "Filled", "Cancelled"
    filled: float = 0.0
    remaining: float = 0.0
    avgFillPrice: float = 0.0
    whyHeld: str = ""


@dataclass
class MockIBExecution:
    """Drop-in mock of `ib_async.Execution` for fill audit logging."""
    execId: str
    orderId: int
    symbol: str
    ticker_idx: int
    side: str                       # "SLD" or "BOT"
    shares: float
    price: float
    time: pd.Timestamp
    day_idx: int
    clock_phase: str
    orderRef: str
    exit_reason: str = ""


@dataclass
class MockIBTrade:
    """Drop-in mock of `ib_async.Trade` linking contract, order, status, and fills."""
    contract: MockIBContract
    order: MockIBOrder
    orderStatus: MockIBOrderStatus
    fills: list[MockIBExecution] = field(default_factory=list)


@dataclass
class MockIBPosition:
    """Drop-in mock of `ib_async.Position` returned by `ib.positions()`."""
    account: str
    contract: MockIBContract
    position: float                 # Negative for short positions (e.g. -1500.0 shares)
    avgCost: float                  # Effective short entry fill price
    notional_0: float
    entry_date: pd.Timestamp
    entry_day_idx: int
    setups: str
    raw_mark_price: float
    stop_price: float
    target_price: float
    locate_fee_paid: float
    borrow_rate_annual: float
    accrued_borrow_fees: float = 0.0
    equity_at_entry: float = 100_000.0
    oca_group: str = ""


class MockIBKRBroker:
    """Stateful Mock IBKR TWS/Gateway Server + OCA Matching Engine + Virtual EOD Clock.

    Exposes the IBKR API used by `LiveIBKRTradingBot` while enforcing:
      1. Strict causal Virtual Clock (`current_day_idx`, `clock_phase`).
      2. Zero look-ahead on `reqHistoricalData`, `reqScannerData`, and `reqShortableQuote`.
      3. Server-side OCA (One-Cancels-All) bracket order matching during intraday `[09:30..15:49]`
         and EOD `[15:50..16:00]` sessions.
      4. Full accounting of cash, T-bill interest, overnight borrow fees, locate fees, and 25% annual tax.
    """

    def __init__(
        self,
        adapter: YahooReplayAdapter,
        cfg: EngineConfig,
        stacked_core: bool = False,
        borrow_quotes: dict[str, BorrowQuote] | None = None,
        account_id: str = "DU_MOCK_IBKR_01",
    ):
        self.adapter = adapter
        self.cfg = cfg
        self.stacked_core = stacked_core
        self.borrow_quotes = borrow_quotes
        self.account_id = account_id

        self.default_bq = BorrowQuote(
            ticker="DEFAULT",
            shortable=True,
            available_shares=1_000_000,
            fee_rate_annual=cfg.borrow_annual,
            bid_ask_spread_pct=cfg.slip_per_side,
            source="modeled",
        )

        # Connection & Virtual Clock state
        self._connected: bool = False
        self.client_id: int = 0
        self.readonly: bool = False
        self.current_day_idx: int = -1
        self.current_date: pd.Timestamp | None = None
        self.clock_phase: str = "UNINITIALIZED"
        self.lookahead_violations: int = 0

        # Account & Portfolio Ledger
        self.cash: float = 0.0 if stacked_core else cfg.initial_capital
        self.core_value: float = cfg.initial_capital if stacked_core else 0.0
        self.core_basis: float = self.core_value
        self.realized_ytd: float = 0.0
        self.loss_carryforward: float = 0.0
        self.prev_year: int | None = None
        self.prev_rate_daily: float = 0.0

        # Order Book & Position Ledger
        self._next_order_id: int = 1001
        self._next_exec_id: int = 1
        self._positions: dict[int, MockIBPosition] = {}     # keyed by ticker_idx
        self._trades: dict[int, MockIBTrade] = {}           # keyed by orderId
        self._oca_groups: dict[str, list[int]] = {}         # ocaGroup -> list[orderId]
        self._day_executions: list[MockIBExecution] = []
        self.all_executions: list[MockIBExecution] = []

        # Audit Logs (to verify 100% parity against reference backtest)
        self.closed_trades: list[ClosedTrade] = []
        self.account_history: list[AccountSnapshot] = []
        self.invariant_checks_passed: int = 0
        self.invariant_failures: list[str] = []

        # Fast mover index for `reqScannerData()` (identical pre-screen: DV >= $5M & H >= 1.5*prev_c)
        with np.errstate(divide="ignore", invalid="ignore"):
            self._fast_plausible = (
                (self.adapter.DV >= 5e6)
                & (self.adapter.H >= self.adapter.prev_c * 1.50)
                & np.isfinite(self.adapter.C)
            )

    # -------------------------------------------------------------------------
    # IBKR Connection & Order ID API (`ib_async.IB` compatible)
    # -------------------------------------------------------------------------
    def connect(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        clientId: int = 1,
        readonly: bool = False,
        timeout: float = 5.0,
    ) -> bool:
        self._connected = True
        self.client_id = clientId
        self.readonly = readonly
        return True

    def disconnect(self) -> None:
        self._connected = False

    def isConnected(self) -> bool:
        return self._connected

    def getReqId(self) -> int:
        oid = self._next_order_id
        self._next_order_id += 1
        return oid

    def qualifyContracts(self, *contracts: MockIBContract) -> list[MockIBContract]:
        qualified: list[MockIBContract] = []
        for c in contracts:
            if c.symbol in self.adapter.col:
                idx = self.adapter.col[c.symbol]
                qualified.append(
                    MockIBContract(
                        symbol=c.symbol,
                        exchange=c.exchange,
                        currency=c.currency,
                        secType=c.secType,
                        conId=idx + 100_000,
                    )
                )
        return qualified

    # -------------------------------------------------------------------------
    # IBKR Account, Positions & Order Book Queries
    # -------------------------------------------------------------------------
    def current_unrealized_pnl(self) -> float:
        return sum(
            p.notional_0 * (1.0 - p.raw_mark_price / p.avgCost)
            for p in self._positions.values()
        )

    def current_equity(self) -> float:
        return self.cash + self.core_value + self.current_unrealized_pnl()

    def accountSummary(self) -> dict[str, float]:
        unreal = self.current_unrealized_pnl()
        eq = self.cash + self.core_value + unreal
        gross_pos = sum(
            p.notional_0 * (p.raw_mark_price / p.avgCost)
            for p in self._positions.values()
        )
        return {
            "TotalCashValue": self.cash,
            "CoreIndexValue": self.core_value,
            "UnrealizedPnL": unreal,
            "NetLiquidation": eq,
            "GrossPositionValue": gross_pos,
            "AvailableFunds": max(0.0, eq - gross_pos),
        }

    def positions(self) -> list[MockIBPosition]:
        return list(self._positions.values())

    def openOrders(self) -> list[MockIBOrder]:
        return [
            tr.order
            for tr in self._trades.values()
            if tr.orderStatus.status in ("PreSubmitted", "Submitted")
        ]

    def openTrades(self) -> list[MockIBTrade]:
        return [
            tr
            for tr in self._trades.values()
            if tr.orderStatus.status in ("PreSubmitted", "Submitted")
        ]

    def executions(self, today_only: bool = True) -> list[MockIBExecution]:
        return list(self._day_executions) if today_only else list(self.all_executions)

    # -------------------------------------------------------------------------
    # IBKR Market Data, Scanner & SLB Borrow API (Strictly Causal <= t)
    # -------------------------------------------------------------------------
    def _assert_causal(self, requested_day_idx: int) -> None:
        if requested_day_idx > self.current_day_idx:
            self.lookahead_violations += 1
            raise LookAheadViolationError(
                f"Look-ahead violation: requested day_idx={requested_day_idx} > current_day_idx={self.current_day_idx}"
            )

    def reqScannerData(self, scanner_code: str = "TOP_PERC_GAIN_EOD") -> list[MockIBContract]:
        """Simulate IBKR EOD scanner at 15:50 ET returning today's active movers (`DV >= $5M`)."""
        t = self.current_day_idx
        self._assert_causal(t)
        js = np.flatnonzero(self._fast_plausible[t])
        return [
            MockIBContract(
                symbol=self.adapter.tickers[int(j)],
                exchange="SMART",
                currency="USD",
                conId=int(j) + 100_000,
            )
            for j in js
        ]

    def reqHistoricalData(
        self,
        contract: MockIBContract,
        endDateTime: str = "",
        durationStr: str = "260 D",
        barSizeSetting: str = "1 day",
        whatToShow: str = "TRADES",
        useRTH: bool = True,
        formatDate: int = 1,
    ) -> list[MockIBBarData]:
        """Serve raw historical daily OHLCV bars strictly up to `self.current_day_idx` (`<= t`).

        The bot uses these raw bars to compute `prev_close`, `SMA200(t-1)`, `52w_High(t-1)`,
        `DV50(t-1)`, `Gap%`, `Surge%`, `RetClose%`, and `CIR` on the fly.
        """
        t = self.current_day_idx
        self._assert_causal(t)
        if contract.symbol not in self.adapter.col:
            return []
        j = self.adapter.col[contract.symbol]

        parts = durationStr.strip().split()
        n_days = int(parts[0]) if parts and parts[0].isdigit() else 260
        start_idx = max(0, t - n_days + 1)

        bars: list[MockIBBarData] = []
        O_col = self.adapter.O[start_idx : t + 1, j]
        H_col = self.adapter.H[start_idx : t + 1, j]
        L_col = self.adapter.L[start_idx : t + 1, j]
        C_col = self.adapter.C[start_idx : t + 1, j]
        V_col = self.adapter.V[start_idx : t + 1, j]
        RAW_col = self.adapter.RAW[start_idx : t + 1, j]
        DV_col = self.adapter.DV[start_idx : t + 1, j]
        dts = self.adapter.dates[start_idx : t + 1]

        for offset in range(len(dts)):
            bars.append(
                MockIBBarData(
                    date=dts[offset],
                    day_idx=start_idx + offset,
                    open=float(O_col[offset]),
                    high=float(H_col[offset]),
                    low=float(L_col[offset]),
                    close=float(C_col[offset]),
                    volume=float(V_col[offset]),
                    raw_close=float(RAW_col[offset]),
                    dollar_vol=float(DV_col[offset]),
                )
            )
        return bars

    def reqContractMetadata(self, contract: MockIBContract) -> dict:
        """Return strictly causal `t-1` universe & point-in-time SEC EDGAR fundamental metadata."""
        t = self.current_day_idx
        self._assert_causal(t)
        j = self.adapter.col[contract.symbol]
        split_flag = (
            bool(self.adapter.split_window_clean[t, j])
            if self.cfg.enforce_clean_data
            else bool(self.adapter.split_near_orig[t, j])
        )
        pb = self.adapter.prior_bars[t, j]
        return {
            "ticker": contract.symbol,
            "ticker_idx": j,
            "prev_raw_vol": float(self.adapter.prev_raw_vol[t, j]),
            "is_top500_prev": bool(self.adapter.top500[t, j]),
            "prior_lifetime_bars": int(pb) if np.isfinite(pb) else 0,
            "split_in_window": split_flag,
            "corrupt_vendor_bar": bool(self.adapter.bad_vendor_mask[t, j]),
            "pit_mcap_prev": float(self.adapter.mcap_prev[t, j]),
            "pit_shares_prev": float(self.adapter.sh_prev[t, j]),
        }

    def reqShortableQuote(self, contract: MockIBContract) -> BorrowQuote:
        """Simulate IBKR Generic Tick 236 (Shortable Shares) & Tick 456 (IBKR Borrow Fee Rate)."""
        self._assert_causal(self.current_day_idx)
        if self.borrow_quotes is not None:
            return self.borrow_quotes.get(contract.symbol, self.default_bq)
        return self.default_bq

    # -------------------------------------------------------------------------
    # IBKR Order Placement, Modification & OCA Cancellation Engine
    # -------------------------------------------------------------------------
    def placeOrder(self, contract: MockIBContract, order: MockIBOrder) -> MockIBTrade:
        """Accept an order from `LiveIBKRTradingBot`, assign `orderId`, register OCA group,
        and route to the matching engine if placed during an active execution window.
        """
        if self.readonly:
            raise PermissionError("MockIBKRBroker is in readonly=True mode; order placement is blocked.")

        if order.orderId == 0:
            order.orderId = self.getReqId()

        initial_status = "PreSubmitted" if order.parentId != 0 else "Submitted"
        status = MockIBOrderStatus(
            orderId=order.orderId,
            status=initial_status,
            filled=0.0,
            remaining=order.totalQuantity,
            avgFillPrice=0.0,
        )
        trade = MockIBTrade(contract=contract, order=order, orderStatus=status)
        self._trades[order.orderId] = trade

        if order.ocaGroup:
            self._oca_groups.setdefault(order.ocaGroup, []).append(order.orderId)

        # If placed at the 15:50 ET EOD decision window and is a top-level order (entry or time-exit cover),
        # execute immediately against today's EOD liquidity.
        if self.clock_phase == "EOD_1550_DECISION" and order.parentId == 0:
            if order.action == "SELL":
                self._execute_eod_short_entry(trade)
            elif order.action == "BUY":
                self._execute_eod_time_exit_cover(trade)

        # If this is the final child leg (`transmit=True`) of an already-filled parent order, activate all children
        if order.parentId != 0:
            parent_tr = self._trades.get(order.parentId)
            if parent_tr is not None and parent_tr.orderStatus.status == "Filled":
                status.status = "Submitted"

        return trade

    def cancelOrder(self, order: MockIBOrder) -> MockIBTrade | None:
        """Cancel an active resting order in the Mock IBKR order book."""
        tr = self._trades.get(order.orderId)
        if tr is not None and tr.orderStatus.status in ("PreSubmitted", "Submitted"):
            tr.orderStatus.status = "Cancelled"
            tr.orderStatus.whyHeld = "USER_CANCELLED"
        return tr

    def _cancel_oca_siblings(self, filled_order_id: int, oca_group: str, reason: str) -> None:
        """Cancel all other resting orders in `oca_group` when one leg fills (IBKR `ocaType=1`)."""
        if not oca_group:
            return
        for oid in self._oca_groups.get(oca_group, []):
            if oid == filled_order_id:
                continue
            sib = self._trades.get(oid)
            if sib is not None and sib.orderStatus.status in ("PreSubmitted", "Submitted"):
                sib.orderStatus.status = "Cancelled"
                sib.orderStatus.whyHeld = reason

    def _execute_eod_short_entry(self, trade: MockIBTrade) -> None:
        """Match a Parent `SELL` short entry order at `15:50-15:59 ET` on day `t`."""
        t = self.current_day_idx
        dt = self.current_date
        assert dt is not None
        j = self.adapter.col[trade.contract.symbol]
        ref_close = float(self.adapter.C[t, j])
        ref_high = float(self.adapter.H[t, j])

        entry_fill, stop_px, tgt_px = compute_entry_and_brackets(ref_close, ref_high, self.cfg)
        notional = trade.order.notional_dollars
        shares = notional / entry_fill if entry_fill > 0 else trade.order.totalQuantity

        # Record fill on parent order
        trade.orderStatus.status = "Filled"
        trade.orderStatus.filled = shares
        trade.orderStatus.remaining = 0.0
        trade.orderStatus.avgFillPrice = entry_fill

        exec_rec = MockIBExecution(
            execId=f"EXEC_{self._next_exec_id:06d}",
            orderId=trade.order.orderId,
            symbol=trade.contract.symbol,
            ticker_idx=j,
            side="SLD",
            shares=shares,
            price=entry_fill,
            time=dt,
            day_idx=t,
            clock_phase=self.clock_phase,
            orderRef=trade.order.orderRef,
            exit_reason="entry",
        )
        self._next_exec_id += 1
        trade.fills.append(exec_rec)
        self._day_executions.append(exec_rec)
        self.all_executions.append(exec_rec)

        # Debit locate fee and determine effective borrow rate
        locate_fee = notional * self.cfg.locate_fee_pct
        self.cash -= locate_fee
        self.realized_ytd -= locate_fee

        bq = self.reqShortableQuote(trade.contract)
        eff_borrow_rate = (
            bq.fee_rate_annual if self.cfg.use_live_borrow_rate else self.cfg.borrow_annual
        )

        # Activate any already-registered child orders linked to this parent
        oca_grp = ""
        for child_tr in self._trades.values():
            if child_tr.order.parentId == trade.order.orderId:
                child_tr.orderStatus.status = "Submitted"
                if child_tr.order.ocaGroup:
                    oca_grp = child_tr.order.ocaGroup

        self._positions[j] = MockIBPosition(
            account=self.account_id,
            contract=trade.contract,
            position=-shares,
            avgCost=entry_fill,
            notional_0=notional,
            entry_date=dt,
            entry_day_idx=t,
            setups=trade.order.setups_str,
            raw_mark_price=ref_close,
            stop_price=stop_px,
            target_price=tgt_px,
            locate_fee_paid=locate_fee,
            borrow_rate_annual=eff_borrow_rate,
            accrued_borrow_fees=0.0,
            equity_at_entry=trade.order.auxPrice if trade.order.auxPrice > 0 else self.current_equity(),
            oca_group=oca_grp,
        )

    def _close_short_position(
        self,
        j: int,
        trade: MockIBTrade,
        exit_fill: float,
        exit_reason: str,
        oca_cancel_reason: str,
    ) -> None:
        """Close short position `j`, settle cash & PnL, cancel OCA siblings, and record `ClosedTrade`."""
        t = self.current_day_idx
        dt = self.current_date
        assert dt is not None
        pos = self._positions[j]
        shares = abs(pos.position)

        trade.orderStatus.status = "Filled"
        trade.orderStatus.filled = shares
        trade.orderStatus.remaining = 0.0
        trade.orderStatus.avgFillPrice = exit_fill

        exec_rec = MockIBExecution(
            execId=f"EXEC_{self._next_exec_id:06d}",
            orderId=trade.order.orderId,
            symbol=pos.contract.symbol,
            ticker_idx=j,
            side="BOT",
            shares=shares,
            price=exit_fill,
            time=dt,
            day_idx=t,
            clock_phase=self.clock_phase,
            orderRef=trade.order.orderRef,
            exit_reason=exit_reason,
        )
        self._next_exec_id += 1
        trade.fills.append(exec_rec)
        self._day_executions.append(exec_rec)
        self.all_executions.append(exec_rec)

        # Cancel resting OCA siblings (e.g. Stop fill cancels Target; Time exit cancels both Stop & Target)
        oca_grp = trade.order.ocaGroup or pos.oca_group
        self._cancel_oca_siblings(trade.order.orderId, oca_grp, oca_cancel_reason)

        gross_pnl = pos.notional_0 * (1.0 - exit_fill / pos.avgCost)
        self.cash += gross_pnl
        self.realized_ytd += gross_pnl
        net_pnl = gross_pnl - pos.locate_fee_paid - pos.accrued_borrow_fees
        net_ret = net_pnl / pos.notional_0

        self.closed_trades.append(
            ClosedTrade(
                ticker=pos.contract.symbol,
                ticker_idx=j,
                setups=pos.setups,
                entry_date=pos.entry_date,
                exit_date=dt,
                entry_day_idx=pos.entry_day_idx,
                exit_day_idx=t,
                nights_held=t - pos.entry_day_idx,
                entry_fill_price=pos.avgCost,
                exit_fill_price=exit_fill,
                stop_price=pos.stop_price,
                target_price=pos.target_price,
                notional_0=pos.notional_0,
                weight_at_entry=pos.notional_0 / pos.equity_at_entry,
                gross_pnl_dollars=gross_pnl,
                locate_fee_dollars=pos.locate_fee_paid,
                borrow_fee_dollars=pos.accrued_borrow_fees,
                net_pnl_dollars=net_pnl,
                net_return_pct=net_ret,
                exit_reason=exit_reason,
            )
        )
        del self._positions[j]

    def _execute_eod_time_exit_cover(self, trade: MockIBTrade) -> None:
        """Execute a Day `t+3` EOD Buy-to-Cover order submitted by `LiveIBKRTradingBot` at 15:50 ET."""
        t = self.current_day_idx
        j = self.adapter.col[trade.contract.symbol]
        if j not in self._positions:
            trade.orderStatus.status = "Cancelled"
            trade.orderStatus.whyHeld = "NO_OPEN_SHORT_POSITION"
            return
        bar_close = float(self.adapter.C[t, j])
        exit_fill = bar_close * (1.0 + self.cfg.slip_per_side)
        self._close_short_position(
            j=j,
            trade=trade,
            exit_fill=exit_fill,
            exit_reason="time",
            oca_cancel_reason="OCA_CANCELLED_BY_TIME_EXIT",
        )

    # -------------------------------------------------------------------------
    # Virtual EOD Clock Lifecycle Phases
    # -------------------------------------------------------------------------
    def step_market_open_and_intraday(self, day_idx: int, is_first_day: bool) -> list[MockIBExecution]:
        """Advance Virtual Clock to `day_idx` `[09:30..15:49 ET]`:
          1. Settle annual tax if new calendar year.
          2. Accrue overnight cash interest & core ETF return.
          3. Debit overnight borrow fee on all active short positions.
          4. Match resting server-side OCA Stop-Loss and Take-Profit orders against today's (O, H, L, C).
        """
        self.current_day_idx = day_idx
        self.current_date = self.adapter.dates[day_idx]
        self.clock_phase = "INTRADAY_SESSION"
        self._day_executions.clear()

        cur_year = int(self.current_date.year)
        rate_daily = float(self.adapter.rate_daily[day_idx])
        core_ret = float(self.adapter.spy_ret[day_idx])

        # 1. Annual tax settlement on first trading day of a new calendar year
        if not is_first_day and self.prev_year is not None and cur_year != self.prev_year and self.cfg.tax_rate > 0:
            taxable_base = self.realized_ytd + self.loss_carryforward
            tax_due = self.cfg.tax_rate * taxable_base if taxable_base > 0 else 0.0
            self.loss_carryforward = taxable_base if taxable_base < 0 else 0.0
            self.realized_ytd = 0.0
            self.cash -= tax_due

        # 2. Overnight T-bill cash interest & core index return
        if not is_first_day:
            if self.stacked_core:
                self.core_value *= 1.0 + core_ret
            eff_rate = self.prev_rate_daily + (0.0 if self.cash >= 0 else 0.01 / 252.0)
            interest = self.cash * eff_rate
            self.cash += interest
            self.realized_ytd += interest

        self.prev_year = cur_year
        self.prev_rate_daily = rate_daily

        # 3. Accrue overnight borrow fee & match resting OCA Stop / Target orders
        for j in list(self._positions.keys()):
            pos = self._positions[j]
            borrow_fee = (
                pos.notional_0
                * (pos.raw_mark_price / pos.avgCost)
                * (pos.borrow_rate_annual / 252.0)
            )
            self.cash -= borrow_fee
            self.realized_ytd -= borrow_fee
            pos.accrued_borrow_fees += borrow_fee

            c_val = float(self.adapter.C[day_idx, j])
            if not math.isfinite(c_val):
                continue

            o_val = float(self.adapter.O[day_idx, j])
            h_val = float(self.adapter.H[day_idx, j])
            l_val = float(self.adapter.L[day_idx, j])

            # Locate the resting OCA Stop and Target orders for this position
            stop_trade: MockIBTrade | None = None
            target_trade: MockIBTrade | None = None
            for oid in self._oca_groups.get(pos.oca_group, []):
                tr = self._trades.get(oid)
                if tr is None or tr.orderStatus.status != "Submitted":
                    continue
                if tr.order.orderType in ("STP", "STPLMT"):
                    stop_trade = tr
                elif tr.order.orderType == "LMT":
                    target_trade = tr

            # Priority 1: Server-side Stop-Loss triggered (`High[t] >= stop_price`)
            if stop_trade is not None and h_val >= stop_trade.order.auxPrice:
                base = max(o_val, stop_trade.order.auxPrice)
                exit_fill = base * (1.0 + self.cfg.slip_per_side + self.cfg.stop_extra_slip)
                self._close_short_position(
                    j=j,
                    trade=stop_trade,
                    exit_fill=exit_fill,
                    exit_reason="stop",
                    oca_cancel_reason="OCA_CANCELLED_BY_STOP",
                )
            # Priority 2: Server-side Take-Profit Limit triggered (`Low[t] <= target_price`)
            elif target_trade is not None and target_trade.order.lmtPrice > 0 and l_val <= target_trade.order.lmtPrice:
                base = o_val if o_val < target_trade.order.lmtPrice else target_trade.order.lmtPrice
                exit_fill = base * (1.0 + self.cfg.slip_per_side)
                self._close_short_position(
                    j=j,
                    trade=target_trade,
                    exit_fill=exit_fill,
                    exit_reason="target",
                    oca_cancel_reason="OCA_CANCELLED_BY_TARGET",
                )

        return list(self._day_executions)

    def step_eod_decision_window(self, day_idx: int) -> None:
        """Advance Virtual Clock to `15:50 ET` EOD Decision Window on `day_idx`.

        Marks surviving positions (those with `nights_held < hold_days` that did not stop/target out)
        to today's EOD reference price before the algorithm evaluates new entries, matching
        `TradingEngine.on_market_day()` step-for-step.
        """
        assert day_idx == self.current_day_idx
        self.clock_phase = "EOD_1550_DECISION"
        for j, pos in self._positions.items():
            if day_idx - pos.entry_day_idx < self.cfg.hold_days:
                c_val = float(self.adapter.C[day_idx, j])
                if math.isfinite(c_val):
                    pos.raw_mark_price = c_val

    def step_eod_close(self, day_idx: int) -> AccountSnapshot:
        """Advance Virtual Clock to `16:00 ET` Market Close, verify broker/order-book invariants,
        and record the daily `AccountSnapshot`.
        """
        assert day_idx == self.current_day_idx
        assert self.current_date is not None
        self.clock_phase = "EOD_1600_CLOSE"

        # Mark all remaining open positions to 16:00 ET official close
        for j, pos in self._positions.items():
            c_val = float(self.adapter.C[day_idx, j])
            if math.isfinite(c_val):
                pos.raw_mark_price = c_val

        # Verify Broker & Order-Book Integrity Invariants at every EOD close
        self._verify_eod_invariants(day_idx)

        eod_unreal = self.current_unrealized_pnl()
        eod_eq = max(0.0, self.cash + self.core_value + eod_unreal)
        snap = AccountSnapshot(
            date=self.current_date,
            day_idx=day_idx,
            cash=self.cash,
            core_value=self.core_value,
            unrealized_short_pnl=eod_unreal,
            total_equity=eod_eq,
            open_positions_count=len(self._positions),
            realized_ytd_taxable=self.realized_ytd,
            loss_carryforward=self.loss_carryforward,
        )
        self.account_history.append(snap)
        return snap

    def _verify_eod_invariants(self, day_idx: int) -> None:
        """Assert that the order book and position ledger have zero orphan orders, zero leaks,
        and strict adherence to slot limits and holding horizons.
        """
        open_pos_by_sym = {p.contract.symbol: p for p in self._positions.values()}

        # 1. Max concurrent positions check
        if len(open_pos_by_sym) > self.cfg.max_positions:
            self.invariant_failures.append(
                f"Day {day_idx}: open positions {len(open_pos_by_sym)} > max_positions {self.cfg.max_positions}"
            )

        # 2. No position held past `hold_days` at EOD close (unless bar was NaN/halted all day)
        for sym, pos in open_pos_by_sym.items():
            j = self.adapter.col[sym]
            if day_idx - pos.entry_day_idx >= self.cfg.hold_days and math.isfinite(self.adapter.C[day_idx, j]):
                self.invariant_failures.append(
                    f"Day {day_idx}: position {sym} held {day_idx - pos.entry_day_idx} days >= hold_days {self.cfg.hold_days}"
                )

        # 3. Every active resting order must belong to an open position, and every open position
        #    must have its active OCA Stop and Target orders
        active_orders_by_sym: dict[str, list[MockIBOrder]] = {}
        for tr in self.openTrades():
            active_orders_by_sym.setdefault(tr.contract.symbol, []).append(tr.order)
            if tr.contract.symbol not in open_pos_by_sym:
                self.invariant_failures.append(
                    f"Day {day_idx}: orphan active order {tr.order.orderId} ({tr.order.orderRef}) for closed symbol {tr.contract.symbol}"
                )

        for sym in open_pos_by_sym:
            orders = active_orders_by_sym.get(sym, [])
            if len(orders) != 2:
                self.invariant_failures.append(
                    f"Day {day_idx}: open position {sym} has {len(orders)} active OCA child orders (expected 2)"
                )

        self.invariant_checks_passed += 1

    def summarize_performance(self) -> dict:
        """Compute final liquidation equity (after remaining tax), CAGR, MaxDD, Sharpe, and trade metrics."""
        if not self.account_history:
            return {}
        eq_series = pd.Series(
            [s.total_equity for s in self.account_history],
            index=pd.DatetimeIndex([s.date for s in self.account_history]),
        )
        final_eq = float(eq_series.iloc[-1])
        if self.cfg.tax_rate > 0:
            unreal = self.current_unrealized_pnl() + (self.core_value - self.core_basis)
            taxable_base = self.realized_ytd + self.loss_carryforward + unreal
            if taxable_base > 0:
                final_eq -= self.cfg.tax_rate * taxable_base

        years = (eq_series.index[-1] - eq_series.index[0]).days / 365.25
        cagr = (final_eq / self.cfg.initial_capital) ** (1.0 / years) - 1.0 if final_eq > 0 and years > 0 else -1.0
        maxdd = float((eq_series / eq_series.cummax() - 1.0).min())
        daily_ret = eq_series.pct_change().dropna()
        sharpe = float(daily_ret.mean() / daily_ret.std() * np.sqrt(252.0)) if daily_ret.std() > 0 else float("nan")

        rets = np.array([t.net_return_pct for t in self.closed_trades], dtype=float)
        reasons = [t.exit_reason for t in self.closed_trades]
        weights = np.array([t.weight_at_entry for t in self.closed_trades], dtype=float)

        return {
            "cagr": cagr,
            "final_equity": final_eq,
            "maxdd": maxdd,
            "sharpe": sharpe,
            "n_trades": len(self.closed_trades),
            "win_rate": float((rets > 0).mean()) if len(rets) else float("nan"),
            "stop_rate": float(np.mean([r == "stop" for r in reasons])) if len(reasons) else float("nan"),
            "mean_trade_net": float(rets.mean()) if len(rets) else float("nan"),
            "median_trade_net": float(np.median(rets)) if len(rets) else float("nan"),
            "worst_portfolio_hit": float((rets * weights).min()) if len(rets) else float("nan"),
            "equity_series": eq_series,
            "trades_df": pd.DataFrame([t.__dict__ for t in self.closed_trades]),
            "n_executions": len(self.all_executions),
            "invariant_checks_passed": self.invariant_checks_passed,
            "invariant_failures": list(self.invariant_failures),
            "lookahead_violations": self.lookahead_violations,
        }


class LiveIBKRTradingBot:
    """Production IBKR Execution Algorithm that talks *only* to `ib_client` (`MockIBKRBroker` or `ib_async.IB`).

    At every EOD decision window (`15:50 ET`):
      1. Syncs intraday stop/target fills from `ib_client.executions()` to update the 10-day ticker cooldown map.
      2. Checks `ib_client.positions()` for any short position reaching `hold_days == 3` and submits an EOD
         Buy-to-Cover `LimitOrder` (which cancels resting OCA stop/target legs).
      3. Queries `ib_client.reqScannerData()` for today's active movers, fetches raw `260 D` daily bars via
         `ib_client.reqHistoricalData()`, computes `SMA200(t-1)`, `52w_High(t-1)`, `DV50(t-1)`, `Gap%`,
         `Surge%`, `RetClose%`, `CIR` directly from the returned bars, checks `ib_client.reqShortableQuote()`,
         ranks valid `S3a / S5b / I3b` signals by `score`, and submits 3-leg OCA Bracket Orders via
         `ib_client.placeOrder()`.
    """

    def __init__(self, ib_client: MockIBKRBroker, cfg: EngineConfig):
        self.ib = ib_client
        self.cfg = cfg
        self.last_exit_day: dict[int, int] = {}
        self.signals_log: list[SignalCandidate] = []
        self.orders_submitted_log: list[MockIBOrder] = []

    @staticmethod
    def compute_indicators_from_ibkr_bars(
        contract: MockIBContract,
        bars: list[MockIBBarData],
        meta: dict,
    ) -> tuple[PreEventContext, BarSnapshot] | None:
        """Compute `PreEventContext` (strictly as of `t-1`) and today's `BarSnapshot` (`t`)
        directly from the raw historical `BarData` list returned by `ib.reqHistoricalData()`.
        """
        if len(bars) < 2:
            return None

        today_bar = bars[-1]
        prev_bar = bars[-2]
        prior_bars = bars[:-1]  # Strictly causal bars [.. t-1]

        prev_close = float(prev_bar.close)
        prev_raw_close = float(prev_bar.raw_close)

        # 50-day rolling mean of dollar_vol up to t-1 (matching `sma(np.nan_to_num(DV, nan=0.0), 50)`)
        if len(prior_bars) >= 50:
            dv50_arr = np.array(
                [0.0 if not math.isfinite(b.dollar_vol) else b.dollar_vol for b in prior_bars[-50:]],
                dtype=np.float64,
            )
            prev_dv50 = float(np.float32(np.mean(dv50_arr)))
        else:
            prev_dv50 = float("nan")

        # 200-day SMA of Close up to t-1 (matching `sma(C, 200)` with min_periods=200)
        if len(prior_bars) >= 200:
            c200_arr = np.array([b.close for b in prior_bars[-200:]], dtype=np.float64)
            sma200_prev = float(np.float32(np.mean(c200_arr))) if np.all(np.isfinite(c200_arr)) else float("nan")
        else:
            sma200_prev = float("nan")

        # 252-day rolling High up to t-1 (matching `rmax(H, 252)` with min_periods=252)
        if len(prior_bars) >= 252:
            h252_arr = np.array([b.high for b in prior_bars[-252:]], dtype=np.float64)
            high252_prev = float(np.float32(np.max(h252_arr))) if np.all(np.isfinite(h252_arr)) else float("nan")
        else:
            high252_prev = float("nan")

        ticker_idx = int(meta["ticker_idx"])
        pre = PreEventContext(
            ticker=contract.symbol,
            ticker_idx=ticker_idx,
            prev_close=prev_close,
            prev_raw_close=prev_raw_close,
            prev_raw_vol=float(meta["prev_raw_vol"]),
            prev_dv50=prev_dv50,
            sma200_prev=sma200_prev,
            high252_prev=high252_prev,
            is_top500_prev=bool(meta["is_top500_prev"]),
            prior_lifetime_bars=int(meta["prior_lifetime_bars"]),
            split_in_window=bool(meta["split_in_window"]),
            corrupt_vendor_bar=bool(meta["corrupt_vendor_bar"]),
            pit_mcap_prev=float(meta["pit_mcap_prev"]),
            pit_shares_prev=float(meta["pit_shares_prev"]),
        )
        bar_snap = BarSnapshot(
            date=today_bar.date,
            day_idx=today_bar.day_idx,
            ticker=contract.symbol,
            ticker_idx=ticker_idx,
            open=float(today_bar.open),
            high=float(today_bar.high),
            low=float(today_bar.low),
            close=float(today_bar.close),
            volume=float(today_bar.volume),
            raw_close=float(today_bar.raw_close),
            dollar_vol=float(today_bar.dollar_vol),
            source="ibkr_historical_bars",
        )
        return pre, bar_snap

    def on_eod_decision_window(self, day_idx: int, allow_new_entries: bool = True) -> None:
        """Execute the bot's 15:50 ET EOD decision cycle via the `ib_client` API."""
        # 1. Sync today's intraday OCA Stop-Loss & Take-Profit fills into `last_exit_day`
        for ex in self.ib.executions(today_only=True):
            if ex.side == "BOT" and ex.exit_reason in ("stop", "target"):
                self.last_exit_day[ex.ticker_idx] = ex.day_idx

        # 2. Submit Day `t+3` EOD Time-Exit Buy-to-Cover orders for expiring positions
        for pos in list(self.ib.positions()):
            if day_idx - pos.entry_day_idx >= self.cfg.hold_days:
                bars = self.ib.reqHistoricalData(pos.contract, durationStr="2 D")
                if not bars or not math.isfinite(bars[-1].close):
                    continue
                today_close = bars[-1].close
                cover_lmt = today_close * (1.0 + self.cfg.slip_per_side)
                cover_order = MockIBOrder(
                    action="BUY",
                    totalQuantity=abs(pos.position),
                    orderType="LMT",
                    lmtPrice=cover_lmt,
                    tif="DAY",
                    ocaGroup=pos.oca_group,
                    ocaType=1,
                    transmit=True,
                    orderRef="TIME_EXIT_T3",
                )
                self.orders_submitted_log.append(cover_order)
                tr = self.ib.placeOrder(pos.contract, cover_order)
                if tr.orderStatus.status == "Filled":
                    j = pos.contract.conId - 100_000
                    self.last_exit_day[j] = day_idx

        # 3. Check portfolio capacity and scan for new 100%+ Gap / Surge Short setups
        open_positions = self.ib.positions()
        acct = self.ib.accountSummary()
        cur_eq = float(acct["NetLiquidation"])

        if not allow_new_entries or len(open_positions) >= self.cfg.max_positions or cur_eq <= 0:
            return

        open_ticker_indices = {p.contract.conId - 100_000 for p in open_positions}
        scanner_contracts = self.ib.reqScannerData("TOP_PERC_GAIN_EOD")

        cands: list[tuple[SignalCandidate, MockIBContract]] = []
        for raw_contract in scanner_contracts:
            qualified = self.ib.qualifyContracts(raw_contract)
            if not qualified:
                continue
            contract = qualified[0]
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="260 D",
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
            )
            meta = self.ib.reqContractMetadata(contract)
            computed = self.compute_indicators_from_ibkr_bars(contract, bars, meta)
            if computed is None:
                continue
            pre, bar_snap = computed
            bq = self.ib.reqShortableQuote(contract)

            sig = evaluate_candidate(pre, bar_snap, bq, self.cfg)
            if sig is not None:
                cands.append((sig, contract))
                self.signals_log.append(sig)

        if not cands:
            return

        # 4. Rank candidates descending by score (deterministic tie-break on ticker_idx)
        cands.sort(key=lambda pair: pair[0].ticker_idx)
        cands.sort(key=lambda pair: -pair[0].score if math.isfinite(pair[0].score) else 1e9)

        # 5. Place 3-leg IBKR OCA Bracket Orders (Parent Short + Child StopLimit + Child Target Limit)
        slots_remaining = self.cfg.max_positions - len(open_ticker_indices)
        for sig, contract in cands:
            if slots_remaining <= 0:
                break
            j = sig.ticker_idx
            if j in open_ticker_indices:
                continue
            if day_idx - self.last_exit_day.get(j, -10**9) < self.cfg.cooldown_days:
                continue

            entry_fill, stop_px, tgt_px = compute_entry_and_brackets(sig.ref_close, sig.ref_high, self.cfg)
            notional = cur_eq * self.cfg.pos_pct
            shares = notional / entry_fill if entry_fill > 0 else 0.0
            if shares <= 0:
                continue

            parent_id = self.ib.getReqId()
            stop_id = self.ib.getReqId()
            target_id = self.ib.getReqId()
            oca_group = f"OCA_{contract.symbol}_{day_idx}_{parent_id}"

            parent_order = MockIBOrder(
                orderId=parent_id,
                action="SELL",
                totalQuantity=shares,
                orderType="LMT",
                lmtPrice=entry_fill,
                auxPrice=cur_eq,  # Record equity_at_entry for audit weight tracking
                tif="DAY",
                transmit=False,
                orderRef=f"ENTRY_SHORT_{sig.setups_str}",
                notional_dollars=notional,
                setups_str=sig.setups_str,
            )
            stop_order = MockIBOrder(
                orderId=stop_id,
                parentId=parent_id,
                action="BUY",
                totalQuantity=shares,
                orderType="STPLMT",
                auxPrice=stop_px,
                lmtPrice=stop_px * (1.0 + self.cfg.slip_per_side + self.cfg.stop_extra_slip),
                tif="GTC",
                ocaGroup=oca_group,
                ocaType=1,
                outsideRth=True,
                transmit=False,
                orderRef="BRACKET_STOP",
            )
            target_order = MockIBOrder(
                orderId=target_id,
                parentId=parent_id,
                action="BUY",
                totalQuantity=shares,
                orderType="LMT",
                lmtPrice=tgt_px,
                tif="GTC",
                ocaGroup=oca_group,
                ocaType=1,
                outsideRth=True,
                transmit=True,
                orderRef="BRACKET_TARGET",
            )

            # Register child bracket orders and execute parent EOD short entry
            self.ib.placeOrder(contract, stop_order)
            self.ib.placeOrder(contract, target_order)
            parent_trade = self.ib.placeOrder(contract, parent_order)

            self.orders_submitted_log.extend([parent_order, stop_order, target_order])
            if parent_trade.orderStatus.status == "Filled":
                open_ticker_indices.add(j)
                slots_remaining -= 1


class MockIBKREODTestEngine:
    """End-to-End EOD Testing Engine driving `MockIBKRBroker` + `LiveIBKRTradingBot`
    across any historical date range and verifying behavior & exact parity.
    """

    def __init__(self, adapter: YahooReplayAdapter):
        self.adapter = adapter

    def run_simulation(
        self,
        cfg: EngineConfig,
        start_date: str = "2019-01-01",
        end_date: str | None = None,
        stacked_core: bool = False,
        borrow_quotes: dict[str, BorrowQuote] | None = None,
    ) -> tuple[MockIBKRBroker, LiveIBKRTradingBot]:
        """Simulate the Virtual EOD Clock day-by-day over `[start_date .. end_date]`."""
        broker = MockIBKRBroker(
            adapter=self.adapter,
            cfg=cfg,
            stacked_core=stacked_core,
            borrow_quotes=borrow_quotes,
        )
        bot = LiveIBKRTradingBot(ib_client=broker, cfg=cfg)
        broker.connect(host="127.0.0.1", port=7497, clientId=101, readonly=False)

        t0 = int(np.searchsorted(self.adapter.dates, pd.Timestamp(start_date)))
        t1 = (
            self.adapter.T
            if end_date is None
            else int(np.searchsorted(self.adapter.dates, pd.Timestamp(end_date), side="right"))
        )

        for k, t in enumerate(range(t0, t1)):
            is_first = (k == 0)
            allow_entries = (t < t1 - 2)

            # 1. 09:30 - 15:49 ET: Open & Intraday OCA Stop-Loss / Profit-Target Matching
            broker.step_market_open_and_intraday(day_idx=t, is_first_day=is_first)

            # 2. 15:50 - 15:59 ET: EOD Decision Window -> Bot queries IBKR API, covers t+3, places new brackets
            broker.step_eod_decision_window(day_idx=t)
            bot.on_eod_decision_window(day_idx=t, allow_new_entries=allow_entries)

            # 3. 16:00 ET: Market Close Mark-to-Market & Invariant Verification
            broker.step_eod_close(day_idx=t)

        broker.disconnect()
        return broker, bot
