"""Stage 2 Verification Runner: IBKR Real-World vs. Yahoo Parity Verifier.

Connects to:
  1. IBKR TWS / IB Gateway (`127.0.0.1:7497` paper or `7496/4002/4001`) in strict `readonly=True` mode
     (zero order placement capability) if TWS/Gateway is open on localhost.
  2. Live IBKR USA Short Stock Availability & Fee Rate feed (`ftp2.interactivebrokers.com/usa.txt`).
  3. Exchange Reference Historical Bars (Nasdaq official bars) + Split-Adjusted SEC EDGAR Share Counts.

Audits every 2026 signal side-by-side (`Yahoo` vs. `Exchange/IBKR Verified`), flags all split/bar
discrepancies and borrow-fee violations, and compares portfolio performance through the exact same
`TradingEngine` used in Stage 1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

SCRATCH_DIR = Path("/usr/local/google/home/lfesch/.gemini/jetski/scratch/smallcap_gap_short")
if str(SCRATCH_DIR) not in sys.path:
    sys.path.insert(0, str(SCRATCH_DIR))

from trading_system.adapters import IBKRShadowVerifier  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 30)


def main():
    print("==================== STAGE 2: IBKR REAL-WORLD vs. YAHOO PARITY VERIFIER (2026 YTD) ====================")
    verifier = IBKRShadowVerifier()
    tws_open, port = verifier.probe_tws_socket()
    print(
        f"IBKR TWS/Gateway Socket Status: {'CONNECTED (Read-Only) on port ' + str(port) if tws_open else 'OFFLINE (Using Exchange Reference Bars + Live IBKR usa.txt SLB Feed)'}"
    )
    print(f"IBKR SLB (`usa.txt`) Symbols Loaded: {len(verifier.slb_quotes):,}")

    res = verifier.run_parity_audit(start_date="2026-01-01")
    pdf = res["parity_df"]
    pdf.to_csv(SCRATCH_DIR / "out" / "stage2_ibkr_vs_yahoo_parity_2026.csv", index=False)

    print("\n--- 1. 2026 Signal Gate Breakdown (IBKR Real-World / Exchange vs. Raw Yahoo) ---")
    print(pdf["gate_status"].value_counts().to_string())

    rejected = pdf[pdf["gate_status"].str.startswith("REJECT_")]
    print(f"\n--- 2. Bad-Data & Excess-Borrow Signals Automatically Caught & Blocked in 2026 ({len(rejected)} signals) ---")
    cols = [
        "date", "ticker", "setups", "yahoo_gap", "exch_gap", "yahoo_surge", "exch_surge",
        "max_ratio_diff", "ibkr_avail_shares", "ibkr_feerate_pct", "gate_status"
    ]
    print(rejected[cols].head(25).to_string(index=False))

    verified = pdf[pdf["gate_status"] == "PASS_VERIFIED"]
    print(f"\n--- 3. Verified & IBKR-Shortable 2026 Signals Summary ({len(verified)} signals) ---")
    print(
        f"  Median |Yahoo vs Exchange Ratio Diff|: {verified['max_ratio_diff'].median():.4f} "
        f"(95th pct: {verified['max_ratio_diff'].quantile(0.95):.4f})"
    )
    print(
        f"  Live IBKR Available Shares: Median = {int(verified['ibkr_avail_shares'].median()):,}, "
        f"P25 = {int(verified['ibkr_avail_shares'].quantile(0.25)):,}"
    )
    print(
        f"  Live IBKR Borrow FeeRate (%/yr): Median = {verified['ibkr_feerate_pct'].median():.2f}%/yr "
        f"({verified['ibkr_3d_borrow_drag_pct'].median():.3f}% for 3d hold), "
        f"Mean = {verified['ibkr_feerate_pct'].mean():.2f}%/yr "
        f"({verified['ibkr_3d_borrow_drag_pct'].mean():.3f}% for 3d hold)"
    )

    print("\n--- 4. Side-by-Side 2026 YTD TradingEngine Comparison (3.5%/short, After-25%-Tax & Pre-Tax) ---")
    comp_rows = []
    for label, key in [
        ("A. Raw Yahoo Feed (unfiltered, modeled 150% borrow)", "raw_yahoo"),
        ("B. Exchange-Verified Clean Feed (Bugs 1-3 fixed, modeled 150% borrow)", "clean_exchange"),
        ("C. Exchange-Verified + Split-Fixed Whale Gate (modeled 150% borrow)", "clean_whale"),
        ("D. IBKR Real-World Verified (Exchange Bars + Whale Gate + Live IBKR SLB FeeRate <= 300%)", "ibkr_live_verified"),
    ]:
        m = res[key]
        eq_s = m["equity_series"]
        ytd_pre = float(eq_s.iloc[-1] / 100_000.0 - 1.0)
        ytd_tax = float(m["final_equity"] / 100_000.0 - 1.0)
        comp_rows.append(
            dict(
                Configuration=label,
                Trades=m["n_trades"],
                Win_Rate=round(m["win_rate"], 4),
                Stop_Rate=round(m["stop_rate"], 4),
                Mean_Trade_Net=round(m["mean_trade_net"], 4),
                Median_Trade_Net=round(m["median_trade_net"], 4),
                YTD_PreTax=round(ytd_pre, 4),
                YTD_AfterTax=round(ytd_tax, 4),
                MaxDD=round(m["maxdd"], 4),
                Sharpe=round(m["sharpe"], 2),
            )
        )
    df_comp = pd.DataFrame(comp_rows)
    print(df_comp.to_string(index=False))
    df_comp.to_csv(SCRATCH_DIR / "out" / "stage2_ibkr_engine_comparison_2026.csv", index=False)


if __name__ == "__main__":
    main()
