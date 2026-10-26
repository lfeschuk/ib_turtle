"""Core domain models for the 2-Stage Small-Cap 100%+ Gap Short Trading System.

Identical models are used across:
  - Stage 1: Local Event-Driven Replay Simulator (fed day-by-day from Yahoo / Clean Nasdaq cache)
  - Stage 2: IBKR Read-Only Shadow Verifier (verifying IBKR real-world bars, signals, spreads & SLB borrow vs Yahoo)
  - Stage 3: IBKR Paper / Live Execution Engine (locked behind explicit readiness & risk gates)
"""
from __future__ import annotations

from dataclasses import dataclass, field
import pandas as pd


@dataclass(frozen=True)
class EngineConfig:
    """Immutable configuration for signal rules, execution frictions, and portfolio risk."""
    # Position sizing & concurrency
    initial_capital: float = 100_000.0
    pos_pct: float = 0.035          # 3.5% (or 5.0%) of current account equity per short
    max_positions: int = 6          # Max 6 concurrent shorts (21% gross at 3.5%, 30% at 5.0%)
    cooldown_days: int = 10         # Trading-day cooldown per ticker after exit
    hold_days: int = 3              # 3-trading-day time exit
    # Bracket stop & target parameters
    stop_cap: float = 0.25          # +25% max catastrophe stop above entry price
    use_hi_stop: bool = True        # Structural stop at min(+25%, max(Day1_High * 1.01, +8%))
    hi_mult: float = 1.01
    stop_floor: float = 0.08
    target_pct: float = 0.35        # +35% profit target (cover at Entry * 0.65)
    # Friction parameters (overridden by live IBKR SLB / spread quotes in Stage 2/3 when use_live_quotes=True)
    slip_per_side: float = 0.005    # 0.50%/side (or 1.00%/side)
    stop_extra_slip: float = 0.020  # +2.00% extra halt/gap stop-out slippage penalty
    locate_fee_pct: float = 0.0075  # 0.00% on IBKR SLB; 0.75% baseline
    borrow_annual: float = 0.50     # 50%/yr baseline or 150%/yr IBKR stress (or live FEERATE)
    max_borrow_annual: float = 3.00 # Hard gate: reject if live IBKR FEERATE > 300%/yr
    use_live_borrow_rate: bool = False
    # Tax & data-hygiene flags
    tax_rate: float = 0.25          # 25% annual realized short-term tax with loss carry-forward
    enforce_clean_data: bool = True # Enforce Bugs 1-3 surgical data hygiene
    enforce_whale_gate: bool = False # Optional Bug-4 split-fixed Turnover >= 30% & MCap $5M-$500M


@dataclass(frozen=True)
class PreEventContext:
    """Strictly causal pre-event state known at end of day t-1 (zero look-ahead into day t)."""
    ticker: str
    ticker_idx: int
    prev_close: float               # Split-adjusted Close[t-1] (same split basis as today's bars)
    prev_raw_close: float           # Unadjusted raw price Close[t-1]
    prev_raw_vol: float             # Unadjusted share volume Volume[t-1]
    prev_dv50: float                # 50-day avg dollar volume as of t-1
    sma200_prev: float              # 200-day SMA of Close as of t-1
    high252_prev: float             # 252-day rolling High as of t-1
    is_top500_prev: bool            # True if in Top-500 large caps as of t-1
    prior_lifetime_bars: int        # Count of valid trading days up to t-1
    split_in_window: bool           # True if a stock split occurred in [t-2..t+3]
    corrupt_vendor_bar: bool        # True if cross-vendor check flagged a corrupt bar on t
    pit_mcap_prev: float            # Split-adjusted point-in-time Market Cap ($) as of t-1 (NaN if unknown)
    pit_shares_prev: float          # Split-adjusted point-in-time Shares Out as of t-1 (NaN if unknown)


@dataclass(frozen=True)
class BarSnapshot:
    """Market OHLCV snapshot for a single ticker on trading day t."""
    date: pd.Timestamp
    day_idx: int
    ticker: str
    ticker_idx: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    raw_close: float
    dollar_vol: float
    source: str = "yahoo"


@dataclass(frozen=True)
class BorrowQuote:
    """Point-in-time or live IBKR SLB shortability and borrow fee quote."""
    ticker: str
    shortable: bool = True
    available_shares: int = 1_000_000
    fee_rate_annual: float = 0.50   # Annualized decimal rate (e.g. 1.50 = 150%/yr)
    bid_ask_spread_pct: float = 0.005
    source: str = "modeled"


@dataclass(frozen=True)
class SignalCandidate:
    """Verified short signal fired at the Day-1 decision window."""
    date: pd.Timestamp
    day_idx: int
    ticker: str
    ticker_idx: int
    s3a: bool
    s5b: bool
    i3b: bool
    gap_pct: float
    surge_pct: float
    ret_close_pct: float
    cir: float
    bagholder: bool
    share_turnover: float
    pit_mcap_prev: float
    score: float
    ref_close: float
    ref_high: float
    dollar_vol: float
    borrow_quote: BorrowQuote

    @property
    def setups_str(self) -> str:
        tags = []
        if self.s3a:
            tags.append("S3a")
        if self.s5b:
            tags.append("S5b")
        if self.i3b:
            tags.append("I3b")
        return "+".join(tags)


@dataclass
class OpenPosition:
    """Active short position managed by the event-driven TradingEngine."""
    ticker: str
    ticker_idx: int
    entry_date: pd.Timestamp
    entry_day_idx: int
    setups: str
    notional_0: float               # Initial dollar notional shorted
    equity_at_entry: float          # Portfolio equity when position was opened
    entry_fill_price: float         # Effective short entry price after entry slippage
    raw_mark_price: float           # Latest mark-to-market price
    stop_price: float               # Server-side stop trigger price
    target_price: float             # Server-side limit profit-target price
    locate_fee_paid: float
    borrow_rate_annual: float       # Locked or floating annualized borrow fee rate
    accrued_borrow_fees: float = 0.0


@dataclass(frozen=True)
class ClosedTrade:
    """Completed short trade record with full audit trail."""
    ticker: str
    ticker_idx: int
    setups: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_day_idx: int
    exit_day_idx: int
    nights_held: int
    entry_fill_price: float
    exit_fill_price: float
    stop_price: float
    target_price: float
    notional_0: float
    weight_at_entry: float
    gross_pnl_dollars: float
    locate_fee_dollars: float
    borrow_fee_dollars: float
    net_pnl_dollars: float
    net_return_pct: float
    exit_reason: str                # "stop", "target", or "time"


@dataclass(frozen=True)
class AccountSnapshot:
    """Daily end-of-day account state."""
    date: pd.Timestamp
    day_idx: int
    cash: float
    core_value: float
    unrealized_short_pnl: float
    total_equity: float
    open_positions_count: int
    realized_ytd_taxable: float
    loss_carryforward: float
