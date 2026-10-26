"""Export the per-bet Kelly model (edge line + risk residuals + overlap haircut) for the live service.

Run on the research machine, where the price panel and research code live:
  python -m trading_system.live.export_model --out model_perbet.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRATCH_DIR = Path(__file__).resolve().parents[2]
AUDIT_DIR = Path("/usr/local/google/home/lfesch/.gemini/jetski/brain/3e509893-e255-4d7e-a8e1-29900a0f488b/scratch/audit")


def build_model() -> dict:
    sys.path.insert(0, str(AUDIT_DIR))
    import a01_event_list as a01

    from ..adapters import YahooReplayAdapter
    from ..models import EngineConfig
    from ..signal_universe import signal_outcomes
    from ..sizing import daily_unit_stream, fit_edge_model, kelly_fraction, position_day_rows

    adp = YahooReplayAdapter(use_nasdaq_verified_bars=True, include_edgar_pit=True)
    cfg = EngineConfig(pos_pct=0.035, locate_fee_pct=0.0, borrow_annual=1.50, slip_per_side=0.005, tax_rate=0.25,
                       enforce_clean_data=True, enforce_whale_gate=False)
    p = dict(open=adp.O, high=adp.H, low=adp.L, close=adp.C, volume=adp.V, raw_close=adp.RAW, dollar_vol=adp.DV,
             split_flag=adp.SPLIT)
    s = a01.signals(p)
    clean = (~adp.split_window_clean) & (~adp.bad_vendor_mask) & (adp.prev_raw_vol > 100.0) & (adp.prior_bars >= 5)
    t01 = int(np.searchsorted(adp.dates, pd.Timestamp("2001-01-01")))
    sig = signal_outcomes(adp, s["union"] & clean, s["score"], cfg, t_lo=t01)
    a, b, resid = fit_edge_model(sig["score"].to_numpy(), sig["net_return_pct"].to_numpy())

    # Overlap haircut: Kelly on the daily P&L of the traded portfolio vs Kelly on single trades
    eng = adp.run_replay(cfg, start_date="2001-01-01")
    trades = pd.DataFrame([t.__dict__ for t in eng.closed_trades])
    u = daily_unit_stream(position_day_rows(adp, trades), t01, adp.T)
    haircut = kelly_fraction(u[u != 0]) / kelly_fraction(trades["net_return_pct"].to_numpy())
    return {"a": a, "b": b, "haircut": float(haircut), "residuals": [round(float(x), 6) for x in resid],
            "n_signals": int(len(sig)), "last_day": str(adp.dates[-1].date()),
            "note": "edge = a + b*score; per-bet Kelly = haircut * kelly(edge + residuals)"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    model = build_model()
    Path(args.out).write_text(json.dumps(model))
    print(f"edge = {model['a']:+.4f} + {model['b']:+.4f} x score, haircut {model['haircut']:.3f}, "
          f"{model['n_signals']} signals through {model['last_day']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
