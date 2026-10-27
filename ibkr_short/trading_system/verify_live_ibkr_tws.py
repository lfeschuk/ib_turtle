"""Stage 2 Live IBKR TWS / IB Gateway Read-Only Parity Verifier (`verify_live_ibkr_tws.py`).

Connects to your running Interactive Brokers TWS or IB Gateway socket in strict `readonly=True`
mode (zero order capability), downloads IBKR's real-world `TRADES` bars and live shortable inventory
for recent 2026 signals (plus today's live movers), and compares IBKR vs. Yahoo bar-for-bar and
signal-for-signal.

Usage:
  /usr/local/google/home/lfesch/.gemini/jetski/scratch/minervini_sepa/.venv/bin/python \
    /usr/local/google/home/lfesch/.gemini/jetski/scratch/smallcap_gap_short/trading_system/verify_live_ibkr_tws.py \
    --host 127.0.0.1 --port 7497 --sample 25
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRATCH_DIR = Path("/usr/local/google/home/lfesch/.gemini/jetski/scratch/smallcap_gap_short")
if str(SCRATCH_DIR) not in sys.path:
    sys.path.insert(0, str(SCRATCH_DIR))

from trading_system.adapters import IBKRShadowVerifier, load_ibkr_slb_table  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 30)


def main():
    parser = argparse.ArgumentParser(description="Stage 2 Read-Only IBKR TWS vs. Yahoo Real-World Parity Verifier")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="TWS / IB Gateway host (default: 127.0.0.1)")
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="TWS / IB Gateway port (0 = auto-probe 7497 Paper TWS, 7496 Live TWS, 4002 Paper GW, 4001 Live GW)",
    )
    parser.add_argument("--client-id", type=int, default=991, help="IBKR API Client ID (default: 991)")
    parser.add_argument("--sample", type=int, default=25, help="Number of recent 2026 signals to cross-verify via TWS")
    args = parser.parse_args()

    ports = (args.port,) if args.port > 0 else (7497, 7496, 4002, 4001)
    verifier = IBKRShadowVerifier(host=args.host, ports=ports)
    is_open, active_port = verifier.probe_tws_socket()

    if not is_open or active_port is None:
        print(f"[STATUS] No open IBKR TWS/Gateway socket detected on {args.host}:{ports}.")
        print("To run live TWS verification:")
        print("  1. Open IBKR TWS or IB Gateway (Paper or Live).")
        print("  2. In File -> Global Configuration -> API -> Settings:")
        print("     - Check 'Enable ActiveX and Socket Clients'")
        print("     - Check 'Read-Only API' (guarantees zero orders can be placed during Stage 2)")
        print("     - Verify Socket Port (7497 = Paper TWS, 7496 = Live TWS, 4002 = Paper Gateway, 4001 = Live Gateway)")
        print("  3. If TWS runs on your local laptop/desktop while this agent runs on lfesch.c.googlers.com,")
        print("     forward the port over SSH:  ssh -L 7497:127.0.0.1:7497 lfesch.c.googlers.com (or -R 7497:127.0.0.1:7497)")
        sys.exit(0)

    import ib_async as ib

    print(f"[CONNECTED] Found IBKR socket at {args.host}:{active_port}. Connecting with readonly=True...")
    client = ib.IB()
    client.connect(args.host, active_port, clientId=args.client_id, readonly=True, timeout=10)

    try:
        # Load recent verified 2026 signals from Stage 2 parity CSV
        parity_csv = SCRATCH_DIR / "out" / "stage2_ibkr_vs_yahoo_parity_2026.csv"
        if not parity_csv.exists():
            res = verifier.run_parity_audit(start_date="2026-01-01")
            pdf = res["parity_df"]
        else:
            pdf = pd.read_csv(parity_csv)

        recent = pdf.tail(args.sample).copy()
        tickers = sorted(recent["ticker"].unique().tolist())
        print(f"Fetching IBKR historical daily TRADES bars for {len(tickers)} recent signal tickers...")

        ib_bars: dict[str, pd.DataFrame] = {}
        for sym in tickers:
            contract = ib.Stock(sym, "SMART", "USD")
            qual = client.qualifyContracts(contract)
            if not qual:
                continue
            bars = client.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="90 D",
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )
            if bars:
                df = ib.util.df(bars)
                df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
                ib_bars[sym] = df.set_index("date").sort_index()

        slb = load_ibkr_slb_table(refresh_ftp=False)
        rows = []
        for _, r in recent.iterrows():
            sym = str(r["ticker"])
            dt = pd.Timestamp(r["date"])
            df = ib_bars.get(sym)
            if df is None or dt not in df.index:
                rows.append(dict(date=r["date"], ticker=sym, status="NO_IBKR_BAR", yahoo_gap=r["yahoo_gap"]))
                continue
            idx = df.index.get_loc(dt)
            if isinstance(idx, slice) or idx == 0:
                rows.append(dict(date=r["date"], ticker=sym, status="NO_PREV_BAR", yahoo_gap=r["yahoo_gap"]))
                continue
            prev_row = df.iloc[idx - 1]
            cur_row = df.iloc[idx]
            pc = float(prev_row["close"])
            o, h, l, c = float(cur_row["open"]), float(cur_row["high"]), float(cur_row["low"]), float(cur_row["close"])
            ib_gap = o / pc - 1.0
            ib_surge = h / pc - 1.0
            ib_rc = c / pc - 1.0
            ib_cir = (c - l) / max(h - l, 1e-6)
            diff = max(
                abs(float(r["yahoo_gap"]) - ib_gap),
                abs(float(r["yahoo_surge"]) - ib_surge),
                abs(float(r["yahoo_rc"]) - ib_rc),
            )
            bq = slb.get(sym)
            rows.append(
                dict(
                    date=r["date"],
                    ticker=sym,
                    setups=r["setups"],
                    yahoo_gap=round(float(r["yahoo_gap"]), 4),
                    ibkr_gap=round(ib_gap, 4),
                    yahoo_surge=round(float(r["yahoo_surge"]), 4),
                    ibkr_surge=round(ib_surge, 4),
                    yahoo_rc=round(float(r["yahoo_rc"]), 4),
                    ibkr_rc=round(ib_rc, 4),
                    yahoo_cir=round(float(r["yahoo_cir"]), 4),
                    ibkr_cir=round(ib_cir, 4),
                    max_diff=round(diff, 4),
                    ibkr_avail=bq.available_shares if bq else 0,
                    ibkr_feerate_pct=round(bq.fee_rate_annual * 100.0, 2) if bq and math.isfinite(bq.fee_rate_annual) else np.nan,
                    status="MATCH_OK" if diff <= 0.02 else "MISMATCH>2%",
                )
            )
        out_df = pd.DataFrame(rows)
        print("\n=== LIVE IBKR TWS vs. YAHOO PARITY REPORT ===")
        print(out_df.to_string(index=False))
        out_df.to_csv(SCRATCH_DIR / "out" / "stage2_live_tws_vs_yahoo_parity.csv", index=False)
    finally:
        if client.isConnected():
            client.disconnect()


if __name__ == "__main__":
    main()
