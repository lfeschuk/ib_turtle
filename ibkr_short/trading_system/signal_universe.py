"""Every clean-union signal (traded or not) replayed through the same bracket rules: the full
distribution of the setup's outcomes, which is what a Kelly bettor is really betting on."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .models import EngineConfig
from .strategy_core import compute_entry_and_brackets


def signal_outcomes(adapter, signal_mask: np.ndarray, score: np.ndarray, cfg: EngineConfig,
                    t_lo: int = 0) -> pd.DataFrame:
    """Hypothetical single-position result of every signal (t, j) with t >= t_lo, using the engine's
    exact entry, stop/target/time-exit, slippage, locate and borrow rules. Signals that cannot be
    resolved before the end of the data are dropped."""
    O, H, L, C = adapter.O, adapter.H, adapter.L, adapter.C
    T = adapter.T
    rate_daily = cfg.borrow_annual / 252.0
    rows = []
    ts, js = np.nonzero(signal_mask)
    for t, j in zip(ts, js):
        t, j = int(t), int(j)
        if t < t_lo:
            continue
        ref_close, ref_high = float(C[t, j]), float(H[t, j])
        e, stop, target = compute_entry_and_brackets(ref_close, ref_high, cfg)
        mark = ref_close
        borrow = 0.0
        exit_px, reason, exit_t = None, None, None
        for d in range(t + 1, T):
            borrow += (mark / e) * rate_daily
            c = float(C[d, j])
            if not math.isfinite(c):
                continue
            o, h, lo = float(O[d, j]), float(H[d, j]), float(L[d, j])
            if h >= stop:
                exit_px, reason = max(o, stop) * (1.0 + cfg.slip_per_side + cfg.stop_extra_slip), "stop"
            elif target > 0 and lo <= target:
                exit_px, reason = (o if o < target else target) * (1.0 + cfg.slip_per_side), "target"
            elif d - t >= cfg.hold_days:
                exit_px, reason = c * (1.0 + cfg.slip_per_side), "time"
            if exit_px is not None:
                exit_t = d
                break
            mark = c
        if exit_px is None:
            continue
        r = 1.0 - exit_px / e - cfg.locate_fee_pct - borrow
        rows.append(dict(entry_day_idx=t, ticker_idx=j, exit_day_idx=exit_t, score=float(score[t, j]),
                         entry_fill=e, stop=stop, exit_reason=reason, net_return_pct=r))
    return pd.DataFrame(rows)
