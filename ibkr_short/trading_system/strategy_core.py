"""Single-source-of-truth strategy evaluation & bracket execution logic.

Used identically by:
  - Stage 1 (`YahooReplayAdapter` -> `TradingEngine`): local day-by-day replay verification
  - Stage 2 (`IBKRShadowVerifier` -> `TradingEngine`): IBKR real-world vs Yahoo parity audit
  - Stage 3 (`IBKRLiveAdapter` -> `TradingEngine`): live/paper execution
"""
from __future__ import annotations

import math
from .models import (
    BarSnapshot,
    BorrowQuote,
    EngineConfig,
    OpenPosition,
    PreEventContext,
    SignalCandidate,
)


def evaluate_candidate(
    pre: PreEventContext,
    bar: BarSnapshot,
    borrow: BorrowQuote,
    cfg: EngineConfig,
) -> SignalCandidate | None:
    """Evaluate a single ticker's Day-1 snapshot against the S3a / S5b / I3b rules.

    Uses strictly causal information: `pre` (known at t-1 close) and `bar` (known at day t decision time).
    Returns `SignalCandidate` if any of S3a, S5b, I3b triggers and passes data/borrow gates; else `None`.
    """
    # 1. Basic finiteness & positive price check
    if not (
        math.isfinite(pre.prev_close)
        and pre.prev_close > 0
        and math.isfinite(pre.prev_raw_close)
        and math.isfinite(pre.prev_dv50)
        and math.isfinite(bar.open)
        and math.isfinite(bar.high)
        and math.isfinite(bar.low)
        and math.isfinite(bar.close)
        and bar.close > 0
        and math.isfinite(bar.dollar_vol)
    ):
        return None

    # 2. Universe & pre-event eligibility gates (strictly as of t-1)
    if pre.is_top500_prev:
        return None
    if not (0.50 <= pre.prev_raw_close <= 30.0):
        return None
    if pre.prev_dv50 >= 50_000_000.0:
        return None

    # 3. Split & Surgical Data-Hygiene Gates
    if pre.split_in_window:
        return None
    if cfg.enforce_clean_data:
        if pre.corrupt_vendor_bar:
            return None
        if pre.prev_raw_vol <= 100.0 or pre.prior_lifetime_bars < 5:
            return None

    # 4. Event-day liquidity & trading-range gates
    if bar.dollar_vol < 5_000_000.0:
        return None
    if bar.high <= bar.low * 1.05:
        return None

    # 5. Event-day ratios
    gap = bar.open / pre.prev_close - 1.0
    surge = bar.high / pre.prev_close - 1.0
    rc = bar.close / pre.prev_close - 1.0
    cir = (bar.close - bar.low) / max(bar.high - bar.low, 1e-6)

    # Pre-pump bagholder overhead supply condition (as of t-1)
    below_sma200 = math.isfinite(pre.sma200_prev) and (pre.prev_close < pre.sma200_prev)
    deep_off_high = math.isfinite(pre.high252_prev) and (pre.prev_close <= 0.50 * pre.high252_prev)
    bag = below_sma200 or deep_off_high

    # 6. The 3 Canonical Short Setups
    s3a = (gap >= 1.00) and (bar.close < bar.open)
    s5b = (surge >= 1.00) and (cir <= 0.50) and (rc >= 0.30) and bag
    i3b = (gap >= 0.75) and (surge >= 1.00) and (bar.high >= bar.open * 1.10) and (bar.close < bar.open) and (rc >= 0.30)

    if not (s3a or s5b or i3b):
        return None

    # 7. Point-in-time Share Turnover & Optional Split-Fixed Whale Gate (Bug 4 fixed)
    raw_vol_today = bar.dollar_vol / max(bar.raw_close, 1e-9) if bar.raw_close > 0 else 0.0
    if math.isfinite(pre.pit_shares_prev) and pre.pit_shares_prev > 0:
        share_turnover = raw_vol_today / pre.pit_shares_prev
    else:
        share_turnover = float("nan")

    if cfg.enforce_whale_gate:
        if math.isfinite(share_turnover) and math.isfinite(pre.pit_mcap_prev):
            if not (share_turnover >= 0.30 and 5_000_000.0 <= pre.pit_mcap_prev < 500_000_000.0):
                return None

    # 8. IBKR Borrow Availability & Fee Ceiling Gate
    if not borrow.shortable or borrow.available_shares <= 0:
        return None
    if cfg.use_live_borrow_rate and borrow.fee_rate_annual > cfg.max_borrow_annual:
        return None

    # 9. Priority ranking score (matches research engine exactly)
    score = (surge - rc) / max(surge, 0.50) + (2.0 if s3a else 0.0) + (1.0 if i3b else 0.0)

    return SignalCandidate(
        date=bar.date,
        day_idx=bar.day_idx,
        ticker=bar.ticker,
        ticker_idx=bar.ticker_idx,
        s3a=s3a,
        s5b=s5b,
        i3b=i3b,
        gap_pct=gap,
        surge_pct=surge,
        ret_close_pct=rc,
        cir=cir,
        bagholder=bag,
        share_turnover=share_turnover,
        pit_mcap_prev=pre.pit_mcap_prev,
        score=score,
        ref_close=bar.close,
        ref_high=bar.high,
        dollar_vol=bar.dollar_vol,
        borrow_quote=borrow,
    )


def compute_entry_and_brackets(
    ref_close: float,
    ref_high: float,
    cfg: EngineConfig,
) -> tuple[float, float, float]:
    """Compute effective entry fill price, server-side stop trigger price, and profit-target price."""
    entry_fill = ref_close * (1.0 - cfg.slip_per_side)
    stop_price = entry_fill * (1.0 + cfg.stop_cap)
    if cfg.use_hi_stop and math.isfinite(ref_high):
        stop_price = min(stop_price, max(ref_high * cfg.hi_mult, entry_fill * (1.0 + cfg.stop_floor)))
    target_price = entry_fill * (1.0 - cfg.target_pct) if cfg.target_pct > 0 else -1.0
    return entry_fill, stop_price, target_price


def evaluate_position_bar_exit(
    pos: OpenPosition,
    bar: BarSnapshot,
    cfg: EngineConfig,
) -> tuple[float | None, str | None]:
    """Check whether an open short position exits on today's bar (stop, target, or time exit).

    Conservative priority order:
      1. Stop-Loss (`bar.high >= pos.stop_price`): fills at `max(bar.open, pos.stop_price)` * (1 + slip + stop_slip).
      2. Take-Profit (`bar.low <= pos.target_price`): fills at `min(bar.open, pos.target_price)` * (1 + slip).
      3. Time Exit (`bar.day_idx - pos.entry_day_idx >= cfg.hold_days`): fills at `bar.close` * (1 + slip).
    """
    if not math.isfinite(bar.close):
        return None, None

    if bar.high >= pos.stop_price:
        base = max(bar.open, pos.stop_price)
        exit_fill = base * (1.0 + cfg.slip_per_side + cfg.stop_extra_slip)
        return exit_fill, "stop"

    if pos.target_price > 0 and bar.low <= pos.target_price:
        base = bar.open if bar.open < pos.target_price else pos.target_price
        exit_fill = base * (1.0 + cfg.slip_per_side)
        return exit_fill, "target"

    if bar.day_idx - pos.entry_day_idx >= cfg.hold_days:
        exit_fill = bar.close * (1.0 + cfg.slip_per_side)
        return exit_fill, "time"

    return None, None
