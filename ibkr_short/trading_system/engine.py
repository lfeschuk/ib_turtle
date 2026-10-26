"""Event-driven TradingEngine that processes market snapshots day-by-day (or bar-by-bar)
with zero access to future data.

In Stage 1 (`YahooReplayAdapter`), historical bars are streamed day-by-day into `on_market_day()`,
reproducing the backtest trade-for-trade and penny-for-penny.
In Stage 2 (`IBKRShadowVerifier`), IBKR live/historical bars and SLB borrow quotes are fed into
the same engine and compared against Yahoo to verify real-world execution parity.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

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


class TradingEngine:
    """Strictly causal, event-driven short portfolio execution engine."""

    def __init__(self, cfg: EngineConfig, stacked_core: bool = False):
        self.cfg = cfg
        self.stacked_core = stacked_core
        self.cash: float = 0.0 if stacked_core else cfg.initial_capital
        self.core_value: float = cfg.initial_capital if stacked_core else 0.0
        self.core_basis: float = self.core_value
        self.open_positions: dict[int, OpenPosition] = {}
        self.last_exit_day: dict[int, int] = {}
        self.realized_ytd: float = 0.0
        self.loss_carryforward: float = 0.0
        self.prev_year: int | None = None
        self.prev_rate_daily: float = 0.0
        self.closed_trades: list[ClosedTrade] = []
        self.account_history: list[AccountSnapshot] = []
        self.signals_log: list[SignalCandidate] = []

    def current_unrealized_pnl(self) -> float:
        return sum(
            p.notional_0 * (1.0 - p.raw_mark_price / p.entry_fill_price)
            for p in self.open_positions.values()
        )

    def current_equity(self) -> float:
        return self.cash + self.core_value + self.current_unrealized_pnl()

    def position_notional(self, sig: SignalCandidate, day_idx: int, cur_eq: float) -> float:
        """Dollar notional for a new short: a fixed fraction of current equity.

        Subclasses override this to research other sizing policies without touching the
        signal, bracket and accounting logic.
        """
        return cur_eq * self.cfg.pos_pct

    def on_market_day(
        self,
        date: pd.Timestamp,
        day_idx: int,
        is_first_day: bool,
        allow_new_entries: bool,
        rate_daily: float,
        core_return_today: float,
        open_position_bars: dict[int, BarSnapshot],
        candidate_inputs: list[tuple[PreEventContext, BarSnapshot, BorrowQuote]],
    ) -> AccountSnapshot:
        """Process a single trading day's lifecycle in strict chronological order:
          1. Year-boundary tax settlement (if new calendar year).
          2. Overnight cash interest & core ETF return accrual.
          3. Daily borrow fee accrual & bracket exit check (Stop / Target / Time) on open positions.
          4. 15:50-15:59 ET decision window: evaluate today's candidates, rank by score, open new shorts.
          5. End-of-day mark-to-market snapshot.
        """
        cur_year = int(date.year)

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
                self.core_value *= 1.0 + core_return_today
            eff_rate = self.prev_rate_daily + (0.0 if self.cash >= 0 else 0.01 / 252.0)
            interest = self.cash * eff_rate
            self.cash += interest
            self.realized_ytd += interest

        self.prev_year = cur_year
        self.prev_rate_daily = rate_daily

        # 3. Manage open positions: accrue overnight borrow fee & check Stop / Target / Time exits
        for j in list(self.open_positions.keys()):
            pos = self.open_positions[j]
            borrow_fee = pos.notional_0 * (pos.raw_mark_price / pos.entry_fill_price) * (pos.borrow_rate_annual / 252.0)
            self.cash -= borrow_fee
            self.realized_ytd -= borrow_fee
            pos.accrued_borrow_fees += borrow_fee

            bar = open_position_bars.get(j)
            if bar is None or not math.isfinite(bar.close):
                continue

            exit_fill, exit_reason = evaluate_position_bar_exit(pos, bar, self.cfg)
            if exit_fill is not None and exit_reason is not None:
                gross_pnl = pos.notional_0 * (1.0 - exit_fill / pos.entry_fill_price)
                self.cash += gross_pnl
                self.realized_ytd += gross_pnl
                net_pnl = gross_pnl - pos.locate_fee_paid - pos.accrued_borrow_fees
                net_ret = net_pnl / pos.notional_0
                self.closed_trades.append(
                    ClosedTrade(
                        ticker=pos.ticker,
                        ticker_idx=pos.ticker_idx,
                        setups=pos.setups,
                        entry_date=pos.entry_date,
                        exit_date=date,
                        entry_day_idx=pos.entry_day_idx,
                        exit_day_idx=day_idx,
                        nights_held=day_idx - pos.entry_day_idx,
                        entry_fill_price=pos.entry_fill_price,
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
                self.last_exit_day[j] = day_idx
                del self.open_positions[j]
            else:
                pos.raw_mark_price = bar.close

        # 4. 15:50-15:59 ET Decision & Entry Window
        cur_eq = self.current_equity()
        if allow_new_entries and len(self.open_positions) < self.cfg.max_positions and cur_eq > 0:
            cands: list[SignalCandidate] = []
            for pre, bar, bq in candidate_inputs:
                sig = evaluate_candidate(pre, bar, bq, self.cfg)
                if sig is not None:
                    cands.append(sig)
                    self.signals_log.append(sig)

            if cands:
                # Sort descending by score, preserving ticker_idx order on ties (stable sort)
                cands.sort(key=lambda x: x.ticker_idx)
                cands.sort(key=lambda x: -x.score if math.isfinite(x.score) else 1e9)
                for sig in cands:
                    if len(self.open_positions) >= self.cfg.max_positions:
                        break
                    j = sig.ticker_idx
                    if j in self.open_positions:
                        continue
                    if day_idx - self.last_exit_day.get(j, -10**9) < self.cfg.cooldown_days:
                        continue

                    entry_fill, stop_px, tgt_px = compute_entry_and_brackets(sig.ref_close, sig.ref_high, self.cfg)
                    notional = self.position_notional(sig, day_idx, cur_eq)
                    locate_fee = notional * self.cfg.locate_fee_pct
                    self.cash -= locate_fee
                    self.realized_ytd -= locate_fee

                    eff_borrow_rate = (
                        sig.borrow_quote.fee_rate_annual
                        if self.cfg.use_live_borrow_rate
                        else self.cfg.borrow_annual
                    )

                    self.open_positions[j] = OpenPosition(
                        ticker=sig.ticker,
                        ticker_idx=j,
                        entry_date=date,
                        entry_day_idx=day_idx,
                        setups=sig.setups_str,
                        notional_0=notional,
                        equity_at_entry=cur_eq,
                        entry_fill_price=entry_fill,
                        raw_mark_price=sig.ref_close,
                        stop_price=stop_px,
                        target_price=tgt_px,
                        locate_fee_paid=locate_fee,
                        borrow_rate_annual=eff_borrow_rate,
                        accrued_borrow_fees=0.0,
                    )

        # 5. End-of-day mark-to-market snapshot
        eod_unreal = self.current_unrealized_pnl()
        eod_eq = max(0.0, self.cash + self.core_value + eod_unreal)
        snap = AccountSnapshot(
            date=date,
            day_idx=day_idx,
            cash=self.cash,
            core_value=self.core_value,
            unrealized_short_pnl=eod_unreal,
            total_equity=eod_eq,
            open_positions_count=len(self.open_positions),
            realized_ytd_taxable=self.realized_ytd,
            loss_carryforward=self.loss_carryforward,
        )
        self.account_history.append(snap)
        return snap

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
        }
