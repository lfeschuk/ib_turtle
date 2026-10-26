"""Broker bars -> the backtest's signal inputs, and bet sizing for the live service."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..models import BarSnapshot, PreEventContext, SignalCandidate
from ..sizing import kelly_fraction, short_initial_per_share
from .broker import AccountInfo, Bar
from .config import LiveConfig


def _dv(b: Bar) -> float:
    return b.dollar_vol if b.dollar_vol is not None else b.close * b.volume


def _raw(b: Bar) -> float:
    return b.raw_close if b.raw_close is not None else b.close


def build_inputs(symbol: str, bars: list[Bar], gate: dict) -> tuple[PreEventContext, BarSnapshot] | None:
    """Same calculations as the backtest (and the mock-IBKR bot): yesterday's context plus today's bar."""
    if len(bars) < 2:
        return None
    today, prior = bars[-1], bars[:-1]
    prev = prior[-1]
    if len(prior) >= 50:
        dvs = [_dv(b) for b in prior[-50:]]
        prev_dv50 = float(np.float32(np.mean([v if math.isfinite(v) else 0.0 for v in dvs])))
    else:
        prev_dv50 = math.nan
    c200 = np.array([b.close for b in prior[-200:]], dtype=np.float64)
    sma200 = float(np.float32(c200.mean())) if len(prior) >= 200 and np.all(np.isfinite(c200)) else math.nan
    h252 = np.array([b.high for b in prior[-252:]], dtype=np.float64)
    high252 = float(np.float32(h252.max())) if len(prior) >= 252 and np.all(np.isfinite(h252)) else math.nan
    idx = int(gate["ticker_idx"])
    pre = PreEventContext(
        ticker=symbol, ticker_idx=idx, prev_close=float(prev.close), prev_raw_close=float(_raw(prev)),
        prev_raw_vol=float(gate["prev_raw_vol"]), prev_dv50=prev_dv50, sma200_prev=sma200, high252_prev=high252,
        is_top500_prev=bool(gate["is_top500_prev"]), prior_lifetime_bars=int(gate["prior_lifetime_bars"]),
        split_in_window=bool(gate["split_in_window"]), corrupt_vendor_bar=bool(gate["corrupt_vendor_bar"]),
        pit_mcap_prev=float(gate["pit_mcap_prev"]), pit_shares_prev=float(gate["pit_shares_prev"]))
    bar = BarSnapshot(date=pd.Timestamp(today.day), day_idx=-1, ticker=symbol, ticker_idx=idx,
                      open=float(today.open), high=float(today.high), low=float(today.low), close=float(today.close),
                      volume=float(today.volume), raw_close=float(_raw(today)), dollar_vol=float(_dv(today)),
                      source="broker")
    return pre, bar


class PerBetModel:
    """Per-bet Kelly from the research: expected edge = a + b * score, risk = past outcomes around that line."""

    def __init__(self, path: str | Path):
        data = json.loads(Path(path).expanduser().read_text())
        self.a = float(data["a"])
        self.b = float(data["b"])
        self.haircut = float(data["haircut"])
        self.residuals = np.asarray(data["residuals"], dtype=np.float64)
        self._sorted = np.sort(self.residuals)
        self.sigma = float(self.residuals.std()) if len(self.residuals) else 0.30
        self._cache: dict[float, float] = {}
        self._drop_cache: dict[float, float] = {}

    def fraction(self, score: float) -> float:
        key = round(float(score), 4)
        if key not in self._cache:
            self._cache[key] = self.haircut * kelly_fraction(self.a + self.b * key + self.residuals)
        return self._cache[key]

    def expected(self, score: float) -> float:
        """Average net return per trade the backtest expects for a signal with this score."""
        return self.a + self.b * float(score)

    def rank(self, score: float, net_return: float) -> float:
        """Where a trade's net return falls among the backtest's outcomes for its score: 0 worst, 0.5 typical, 1 best."""
        z = float(net_return) - self.expected(score)
        lo = np.searchsorted(self._sorted, z, side="left")
        hi = np.searchsorted(self._sorted, z, side="right")
        return float(lo + hi) / (2.0 * len(self._sorted))

    def rank_drop_without_edge(self, mean_edge: float) -> float:
        """How far the average rank falls if the edge disappears (returns shift down by the expected edge)."""
        key = round(float(mean_edge), 4)
        if key not in self._drop_cache:
            x = self._sorted
            beats = len(x) - np.searchsorted(x, x + key, side="left")
            self._drop_cache[key] = 0.5 - float(beats.mean()) / len(x)
        return self._drop_cache[key]


@dataclass
class SizeDecision:
    notional: float
    fraction: float
    capped_by: str


def size_bet(cfg: LiveConfig, sig: SignalCandidate, entry_price: float, account: AccountInfo,
             peak_adj: float | None, realized_ytd: float, model: PerBetModel | None,
             year_start_adj: float | None = None) -> SizeDecision:
    nlv = account.net_liquidation
    if not math.isfinite(nlv) or nlv <= 0:
        return SizeDecision(0.0, 0.0, "no equity")
    s = cfg.sizing
    if s.mode == "static":
        f = s.static_pct
    elif s.mode == "perbet":
        f = model.fraction(sig.score) * s.kelly_mult if model is not None else 0.0
    elif s.mode == "perbet_house":
        # The money the year started with is bet at kelly_mult and this year's profit at profit_kelly_mult, so bets
        # grow with the profit and fall back to kelly_mult (never lower) as the profit is given back.
        adj = nlv - s.tax_rate * max(0.0, realized_ytd)  # the yearly tax bill is not profit to bet with
        start = year_start_adj if year_start_adj is not None else adj
        mult = s.kelly_mult + (s.profit_kelly_mult - s.kelly_mult) * max(0.0, adj - start) / nlv
        f = model.fraction(sig.score) * mult if model is not None else 0.0
    else:
        adj = nlv - s.tax_rate * max(0.0, realized_ytd)  # the yearly tax bill is not a trading loss
        peak = max(peak_adj if peak_adj is not None else adj, adj)
        cushion = max(0.0, adj - (1.0 - s.dd_limit) * peak) / nlv
        f = model.fraction(sig.score) * cushion if model is not None else 0.0
    capped_by = "none"
    if f > s.max_position_pct:
        f, capped_by = s.max_position_pct, "max per short"
    notional = f * nlv
    liquidity = s.liquidity_cap_pct * sig.dollar_vol
    if notional > liquidity:
        notional, capped_by = liquidity, "liquidity"
    if math.isfinite(account.excess_liquidity):
        req_per_dollar = short_initial_per_share(sig.ref_close) / max(entry_price, 1e-9)
        room = max(0.0, 0.8 * account.excess_liquidity) / req_per_dollar
        if notional > room:
            notional, capped_by = room, "margin"
    return SizeDecision(notional, notional / nlv, capped_by)
