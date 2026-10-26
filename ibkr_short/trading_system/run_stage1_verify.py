"""Stage 1 Verification Runner:
Feeds historical market data day-by-day into the event-driven `TradingEngine` via `YahooReplayAdapter`
and verifies 100.0000% trade-for-trade and penny-for-penny parity against the research backtest.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRATCH_DIR = Path("/usr/local/google/home/lfesch/.gemini/jetski/scratch/smallcap_gap_short")
AUDIT_DIR = Path("/usr/local/google/home/lfesch/.gemini/jetski/brain/3e509893-e255-4d7e-a8e1-29900a0f488b/scratch/audit")
if str(SCRATCH_DIR) not in sys.path:
    sys.path.insert(0, str(SCRATCH_DIR))
if str(AUDIT_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIT_DIR))

import a01_event_list as a01  # noqa: E402
import eng  # noqa: E402
from trading_system.adapters import YahooReplayAdapter  # noqa: E402
from trading_system.models import EngineConfig  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 30)


def verify_scenario(
    name: str,
    adapter: YahooReplayAdapter,
    cfg: EngineConfig,
    ref_sig_mask: np.ndarray,
    ref_score: np.ndarray,
) -> dict:
    """Run event-driven TradingEngine day-by-day and compare against vectorized research `eng.portfolio`."""
    live_eng = adapter.run_replay(cfg, start_date="2019-01-01")
    live_res = live_eng.summarize_performance()

    ref_res = eng.portfolio(
        adapter.O,
        adapter.H,
        adapter.L,
        adapter.C,
        adapter.dates,
        ref_sig_mask,
        ref_score,
        adapter.rate_daily,
        pos_pct=cfg.pos_pct,
        max_pos=cfg.max_positions,
        hold=cfg.hold_days,
        stop_cap=cfg.stop_cap,
        use_hi_stop=cfg.use_hi_stop,
        target=cfg.target_pct,
        slip=cfg.slip_per_side,
        stop_slip=cfg.stop_extra_slip,
        locate=cfg.locate_fee_pct,
        borrow=cfg.borrow_annual,
        cooldown=cfg.cooldown_days,
        tax=cfg.tax_rate,
        start="2019-01-01",
    )

    eq_diff = float(np.max(np.abs(live_res["equity_series"].to_numpy() - ref_res["equity"].to_numpy())))
    cagr_diff = abs(live_res["cagr"] - ref_res["cagr"])
    n_live = live_res["n_trades"]
    n_ref = ref_res["n"]

    # Trade-by-trade comparison
    t_live = live_res["trades_df"]
    t_ref = ref_res["trades"]
    trade_ret_diff = (
        float(np.max(np.abs(t_live["net_return_pct"].to_numpy() - t_ref["net"].to_numpy())))
        if n_live == n_ref and n_live > 0
        else float("inf")
    )
    exact_tickers_match = (
        bool(np.array_equal(t_live["ticker_idx"].to_numpy(), t_ref["j"].to_numpy()))
        and bool(np.array_equal(t_live["entry_day_idx"].to_numpy(), t_ref["t"].to_numpy()))
        if n_live == n_ref
        else False
    )

    passed = (n_live == n_ref) and exact_tickers_match and (eq_diff < 1e-6) and (trade_ret_diff < 1e-9)

    return dict(
        Scenario=name,
        Trades_Engine=n_live,
        Trades_Research=n_ref,
        CAGR_Engine=round(live_res["cagr"], 6),
        CAGR_Research=round(ref_res["cagr"], 6),
        MaxDD_Engine=round(live_res["maxdd"], 6),
        Max_Daily_Equity_Diff_USD=round(eq_diff, 8),
        Max_Trade_Ret_Diff=round(trade_ret_diff, 10),
        Exact_Parity="PASS (100.0000%)" if passed else "FAIL",
    )


def main():
    print("==================== STAGE 1: LOCAL EVENT-DRIVEN REPLAY PARITY VERIFICATION ====================")
    p = a01.load_panel()
    s_orig = a01.signals(p)

    raw_adapter = YahooReplayAdapter(use_nasdaq_verified_bars=False, include_edgar_pit=False)
    clean_adapter = YahooReplayAdapter(use_nasdaq_verified_bars=True, include_edgar_pit=True)

    # Reconstruct reference masks on clean_adapter's exact price arrays
    p_clean = dict(
        open=clean_adapter.O,
        high=clean_adapter.H,
        low=clean_adapter.L,
        close=clean_adapter.C,
        volume=clean_adapter.V,
        raw_close=clean_adapter.RAW,
        dollar_vol=clean_adapter.DV,
        split_flag=clean_adapter.SPLIT,
    )
    s_clean = a01.signals(p_clean)
    surgical_clean = (
        (~clean_adapter.split_window_clean)
        & (~clean_adapter.bad_vendor_mask)
        & (clean_adapter.prev_raw_vol > 100.0)
        & (clean_adapter.prior_bars >= 5)
    )
    u_clean = s_clean["union"] & surgical_clean

    with np.errstate(divide="ignore", invalid="ignore"):
        to_fixed = clean_adapter.raw_vol / clean_adapter.sh_prev
    whale_gate = (~np.isfinite(to_fixed)) | (
        (to_fixed >= 0.30) & (clean_adapter.mcap_prev >= 5e6) & (clean_adapter.mcap_prev < 500e6)
    )
    u_whale = u_clean & whale_gate

    scenarios = [
        (
            "1. Raw Yahoo Union (3.5%, Baseline Costs, After-Tax)",
            raw_adapter,
            EngineConfig(pos_pct=0.035, locate_fee_pct=0.0075, borrow_annual=0.50, slip_per_side=0.005,
                         tax_rate=0.25, enforce_clean_data=False, enforce_whale_gate=False),
            s_orig["union"],
            s_orig["score"],
        ),
        (
            "2. Raw Yahoo Union (3.5%, IBKR Limit Costs, Pre-Tax)",
            raw_adapter,
            EngineConfig(pos_pct=0.035, locate_fee_pct=0.0, borrow_annual=1.50, slip_per_side=0.005,
                         tax_rate=0.0, enforce_clean_data=False, enforce_whale_gate=False),
            s_orig["union"],
            s_orig["score"],
        ),
        (
            "3. Surgical Clean Union (3.5%, IBKR Limit Costs, After-Tax)",
            clean_adapter,
            EngineConfig(pos_pct=0.035, locate_fee_pct=0.0, borrow_annual=1.50, slip_per_side=0.005,
                         tax_rate=0.25, enforce_clean_data=True, enforce_whale_gate=False),
            u_clean,
            s_clean["score"],
        ),
        (
            "4. Surgical Clean Union (5.0%, IBKR Harsh Mkt Costs, After-Tax)",
            clean_adapter,
            EngineConfig(pos_pct=0.050, locate_fee_pct=0.0, borrow_annual=1.50, slip_per_side=0.010,
                         tax_rate=0.25, enforce_clean_data=True, enforce_whale_gate=False),
            u_clean,
            s_clean["score"],
        ),
        (
            "5. Clean Union + Split-Fixed Whale Gate (3.5%, IBKR Limit, After-Tax)",
            clean_adapter,
            EngineConfig(pos_pct=0.035, locate_fee_pct=0.0, borrow_annual=1.50, slip_per_side=0.005,
                         tax_rate=0.25, enforce_clean_data=True, enforce_whale_gate=True),
            u_whale,
            s_clean["score"],
        ),
    ]

    results = []
    for name, adp, cfg, mask, sc_mat in scenarios:
        res = verify_scenario(name, adp, cfg, mask, sc_mat)
        results.append(res)

    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))
    df_res.to_csv(SCRATCH_DIR / "out" / "stage1_replay_parity_verification.csv", index=False)


if __name__ == "__main__":
    main()
