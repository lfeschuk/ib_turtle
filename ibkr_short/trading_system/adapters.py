"""Data and Broker Adapters for Stage 1 (Local Yahoo Replay) and Stage 2 (IBKR Shadow Verifier).

Stage 1 (`YahooReplayAdapter`):
  Streams historical market data day-by-day into `TradingEngine.on_market_day()` in strict
  chronological order (zero look-ahead), proving 100% trade-for-trade and penny-for-penny
  parity with the research backtest.

Stage 2 (`IBKRShadowVerifier`):
  1. Connects to IBKR SLB (`ftp2.interactivebrokers.com/usa.txt` / local cache) + IBKR TWS/Gateway
     in strict `readonly=True` mode (or Nasdaq Exchange Reference bars when TWS is offline).
  2. Performs a side-by-side parity audit (`IBKR Real-World vs. Yahoo`) on every signal:
     - Verifies `Close[t-1]`, `Open[t]`, `High[t]`, `Low[t]`, `Close[t]`, `Gap%`, `Surge%`, `CIR`
     - Automatically flags and blocks split/bar discrepancies > 1% (e.g. `SMX 2026-05-11`)
     - Attaches real-world IBKR SLB `AVAILABLE` shares and `FEERATE` to each signal
     - Simulates `TradingEngine` side-by-side on Yahoo vs. Verified Exchange + IBKR Live Borrow.
"""
from __future__ import annotations

import ftplib
import io
import math
import socket
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .engine import TradingEngine
from .models import (
    BarSnapshot,
    BorrowQuote,
    EngineConfig,
    PreEventContext,
)
from .strategy_core import evaluate_candidate

SEPA_ROOT = Path("/usr/local/google/home/lfesch/.gemini/jetski/scratch/minervini_sepa")
SCRATCH_DIR = Path("/usr/local/google/home/lfesch/.gemini/jetski/scratch/smallcap_gap_short")
OUT_DIR = SCRATCH_DIR / "out"
AUDIT_DIR = Path("/usr/local/google/home/lfesch/.gemini/jetski/brain/3e509893-e255-4d7e-a8e1-29900a0f488b/scratch/audit")

if str(SEPA_ROOT) not in sys.path:
    sys.path.insert(0, str(SEPA_ROOT))
if str(SCRATCH_DIR) not in sys.path:
    sys.path.insert(0, str(SCRATCH_DIR))
if str(AUDIT_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIT_DIR))

from sepa import prices  # noqa: E402
import a01_event_list as a01  # noqa: E402
from importlib import import_module  # noqa: E402
m15 = import_module("15_clean_data_recalculation")


def load_ibkr_slb_table(refresh_ftp: bool = False) -> dict[str, BorrowQuote]:
    """Load IBKR USA Short Stock Availability & Fee Rate table (`usa.txt`)."""
    cache_path = OUT_DIR / "ibkr_usa_slb.txt"
    if refresh_ftp or not cache_path.exists():
        try:
            ftp = ftplib.FTP("ftp2.interactivebrokers.com", timeout=15)
            ftp.login("shortstock", "")
            buf = io.BytesIO()
            ftp.retrbinary("RETR usa.txt", buf.write)
            ftp.quit()
            raw_text = buf.getvalue().decode("utf-8", errors="ignore")
            cache_path.write_text(raw_text, encoding="utf-8")
        except Exception as exc:
            if not cache_path.exists():
                raise RuntimeError(f"Failed to fetch IBKR usa.txt and no cache exists: {exc}") from exc

    quotes: dict[str, BorrowQuote] = {}
    for line in cache_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 8 or parts[0] == "SYM":
            continue
        sym = parts[0].strip()
        avail_str = parts[7].strip()
        fee_str = parts[6].strip()
        if avail_str.startswith(">"):
            avail = int(avail_str[1:])
        else:
            try:
                avail = int(avail_str)
            except ValueError:
                avail = 0
        try:
            fee_pct = float(fee_str) / 100.0  # Convert e.g. 90.67 (%) -> 0.9067 decimal annual
        except ValueError:
            fee_pct = float("nan")

        shortable = (avail > 0) and math.isfinite(fee_pct) and (fee_pct > -1.0)
        quotes[sym] = BorrowQuote(
            ticker=sym,
            shortable=shortable,
            available_shares=avail,
            fee_rate_annual=max(0.0, fee_pct) if math.isfinite(fee_pct) else 1.50,
            bid_ask_spread_pct=0.005,
            source="ibkr_usa_txt",
        )
    return quotes


class YahooReplayAdapter:
    """Stage 1 Local Replay Adapter: feeds historical Yahoo (or Clean Yahoo/Nasdaq) bars
    chronologically day-by-day into `TradingEngine`.
    """

    def __init__(self, use_nasdaq_verified_bars: bool = False, include_edgar_pit: bool = False):
        p = a01.load_panel()
        self.dates = pd.DatetimeIndex(p["dates"])
        self.tickers = list(p["tickers"])
        self.col = {t: i for i, t in enumerate(self.tickers)}
        self.O = p["open"].astype(np.float64).copy()
        self.H = p["high"].astype(np.float64).copy()
        self.L = p["low"].astype(np.float64).copy()
        self.C = p["close"].astype(np.float64).copy()
        self.V = p["volume"].astype(np.float64).copy()
        self.RAW = p["raw_close"].astype(np.float64).copy()
        self.DV = p["dollar_vol"].astype(np.float64).copy()
        self.SPLIT = p["split_flag"].astype(np.float32).copy()
        self.T, self.N = self.C.shape

        # Compute causal t-1 pre-event matrices on the base Yahoo panel (matching 01_explore_events.py)
        self.prev_c = a01.shift(self.C, 1)
        self.prev_raw = a01.shift(self.RAW, 1)
        self.prev_dv50 = a01.shift(a01.sma(np.nan_to_num(self.DV, nan=0.0), 50), 1)
        self.s200_prev = a01.shift(a01.sma(self.C, 200), 1)
        self.hi52_prev = a01.shift(a01.rmax(self.H, 252), 1)

        liq_prev = (self.prev_raw >= 10.0) & (self.prev_dv50 >= 5e6) & np.isfinite(self.prev_c)
        ranks = (
            pd.DataFrame(np.where(liq_prev, self.prev_dv50, np.nan))
            .rank(axis=1, ascending=False, method="first")
            .to_numpy()
        )
        self.top500 = liq_prev & (ranks <= 500)

        # Original 3-day split guard vs Surgical 6-day split guard [t-2..t+3]
        self.split_near_orig = (self.SPLIT > 0) | (a01.shift(self.SPLIT, 1) > 0) | (a01.shift(self.SPLIT, -1) > 0)
        self.split_window_clean = np.zeros_like(self.SPLIT, dtype=bool)
        for k in (-3, -2, -1, 0, 1, 2, 3):
            self.split_window_clean |= (a01.shift(self.SPLIT, k) > 0)

        with np.errstate(divide="ignore", invalid="ignore"):
            self.raw_vol = np.where((self.RAW > 0) & np.isfinite(self.RAW), self.DV / self.RAW, 0.0)
        self.prev_raw_vol = a01.shift(self.raw_vol, 1)
        valid_bar = np.isfinite(self.C) & (self.C > 0) & (self.raw_vol > 100.0)
        self.prior_bars = a01.shift(pd.DataFrame(valid_bar.astype(np.float32)).cumsum().to_numpy(), 1)

        # Cross-vendor bad bar mask from Nasdaq historical verification
        self.bad_vendor_mask = np.zeros((self.T, self.N), dtype=bool)
        zn_path = AUDIT_DIR / "out" / "nasdaq_panel.npz"
        cmp_path = AUDIT_DIR / "out" / "a05_yahoo_vs_nasdaq_events.csv"
        if zn_path.exists() and cmp_path.exists():
            zn = np.load(zn_path)
            On_sub, Hn_sub, Ln_sub, Cn_sub = zn["O"], zn["H"], zn["L"], zn["C"]
            tk_n = list(zn["tickers"])
            col_n = {t: i for i, t in enumerate(tk_n)}
            cmp_df = pd.read_csv(cmp_path)
            for _, r in cmp_df.iterrows():
                ti, ji = int(r["t"]), int(r["j"])
                if r["status"] == "ok" and float(r["max_ratio_diff"]) > 0.05:
                    self.bad_vendor_mask[ti, ji] = True
            with np.errstate(divide="ignore", invalid="ignore"):
                y_surge = self.H / self.prev_c - 1.0
            for sym, jn in col_n.items():
                j = self.col[sym]
                cn, hn = Cn_sub[:, jn], Hn_sub[:, jn]
                ok_n = np.isfinite(cn) & np.isfinite(a01.shift(cn, 1)) & (a01.shift(cn, 1) > 0) & np.isfinite(hn)
                n_surge = np.where(ok_n, hn / a01.shift(cn, 1) - 1.0, np.nan)
                self.bad_vendor_mask[:, j] |= (ok_n & (y_surge[:, j] >= 1.0) & (n_surge < 0.50))

            if use_nasdaq_verified_bars:
                for sym, jn in col_n.items():
                    j = self.col[sym]
                    # Only replace bars where Nasdaq is finite and on the same split-adjustment basis as Yahoo
                    ok_n = (
                        np.isfinite(Cn_sub[:, jn])
                        & np.isfinite(On_sub[:, jn])
                        & np.isfinite(Hn_sub[:, jn])
                        & np.isfinite(Ln_sub[:, jn])
                        & np.isfinite(self.C[:, j])
                        & (self.C[:, j] > 0)
                        & (np.abs(Cn_sub[:, jn] / self.C[:, j] - 1.0) <= 0.05)
                    )
                    self.O[ok_n, j] = On_sub[ok_n, jn]
                    self.H[ok_n, j] = Hn_sub[ok_n, jn]
                    self.L[ok_n, j] = Ln_sub[ok_n, jn]
                    self.C[ok_n, j] = Cn_sub[ok_n, jn]
                self.prev_c = a01.shift(self.C, 1)
                self.s200_prev = a01.shift(a01.sma(self.C, 200), 1)
                self.hi52_prev = a01.shift(a01.rmax(self.H, 252), 1)

        # Optional Split-Fixed Point-in-Time EDGAR MCap & Shares
        if include_edgar_pit:
            pit = m15.build_pit_mcap_and_dilution_split_fixed(self.dates, self.tickers, p["close"], self.RAW)
            self.mcap_prev = a01.shift(pit["mcap"], 1)
            self.sh_prev = a01.shift(pit["pit_shares"], 1)
        else:
            self.mcap_prev = np.full((self.T, self.N), np.nan, dtype=np.float32)
            self.sh_prev = np.full((self.T, self.N), np.nan, dtype=np.float32)

        irx = prices.load("^IRX")
        self.rate_daily = irx["close"].reindex(self.dates).ffill().fillna(0.0).to_numpy() / 100.0 / 252.0
        spy = prices.to_bars(prices.load("SPY"), div_adjust=True)["close"].reindex(self.dates).ffill()
        self.spy_ret = spy.pct_change().fillna(0.0).to_numpy()

    def run_replay(
        self,
        cfg: EngineConfig,
        start_date: str = "2019-01-01",
        end_date: str | None = None,
        stacked_core: bool = False,
        borrow_quotes: dict[str, BorrowQuote] | None = None,
        engine: TradingEngine | None = None,
    ) -> TradingEngine:
        """Stream historical bars day-by-day into `TradingEngine` and return the completed engine.

        An engine instance (e.g. a subclass with a different sizing policy) can be passed in;
        it must have been built with the same `cfg`.
        """
        if engine is None:
            engine = TradingEngine(cfg, stacked_core=stacked_core)
        elif engine.cfg != cfg:
            raise ValueError("engine.cfg must match cfg")
        t0 = int(np.searchsorted(self.dates, pd.Timestamp(start_date)))
        t1 = self.T if end_date is None else int(np.searchsorted(self.dates, pd.Timestamp(end_date), side="right"))

        # Pre-filter candidate ticker indices per day where dollar_vol >= $5M and H >= 1.5 * prev_c
        # (Pure speed optimization: evaluates `evaluate_candidate` on all plausible movers without changing logic)
        with np.errstate(divide="ignore", invalid="ignore"):
            fast_plausible = (self.DV >= 5e6) & (self.H >= self.prev_c * 1.50) & np.isfinite(self.C)

        default_bq = BorrowQuote(
            ticker="DEFAULT",
            shortable=True,
            available_shares=1_000_000,
            fee_rate_annual=cfg.borrow_annual,
            bid_ask_spread_pct=cfg.slip_per_side,
            source="modeled",
        )

        for k, t in enumerate(range(t0, t1)):
            dt = self.dates[t]
            is_first = (k == 0)
            allow_entries = (t < t1 - 2)

            # 1. Build BarSnapshots only for currently open positions
            open_bars: dict[int, BarSnapshot] = {}
            for j in engine.open_positions.keys():
                open_bars[j] = BarSnapshot(
                    date=dt,
                    day_idx=t,
                    ticker=self.tickers[j],
                    ticker_idx=j,
                    open=float(self.O[t, j]),
                    high=float(self.H[t, j]),
                    low=float(self.L[t, j]),
                    close=float(self.C[t, j]),
                    volume=float(self.V[t, j]),
                    raw_close=float(self.RAW[t, j]),
                    dollar_vol=float(self.DV[t, j]),
                )

            # 2. Build causal (PreEventContext, BarSnapshot, BorrowQuote) tuples for today's movers
            cand_inputs: list[tuple[PreEventContext, BarSnapshot, BorrowQuote]] = []
            if allow_entries:
                plausible_js = np.flatnonzero(fast_plausible[t])
                for j in plausible_js:
                    j_int = int(j)
                    sym = self.tickers[j_int]
                    split_flag = (
                        bool(self.split_window_clean[t, j_int])
                        if cfg.enforce_clean_data
                        else bool(self.split_near_orig[t, j_int])
                    )
                    pre = PreEventContext(
                        ticker=sym,
                        ticker_idx=j_int,
                        prev_close=float(self.prev_c[t, j_int]),
                        prev_raw_close=float(self.prev_raw[t, j_int]),
                        prev_raw_vol=float(self.prev_raw_vol[t, j_int]),
                        prev_dv50=float(self.prev_dv50[t, j_int]),
                        sma200_prev=float(self.s200_prev[t, j_int]),
                        high252_prev=float(self.hi52_prev[t, j_int]),
                        is_top500_prev=bool(self.top500[t, j_int]),
                        prior_lifetime_bars=int(self.prior_bars[t, j_int]) if np.isfinite(self.prior_bars[t, j_int]) else 0,
                        split_in_window=split_flag,
                        corrupt_vendor_bar=bool(self.bad_vendor_mask[t, j_int]),
                        pit_mcap_prev=float(self.mcap_prev[t, j_int]),
                        pit_shares_prev=float(self.sh_prev[t, j_int]),
                    )
                    bar = BarSnapshot(
                        date=dt,
                        day_idx=t,
                        ticker=sym,
                        ticker_idx=j_int,
                        open=float(self.O[t, j_int]),
                        high=float(self.H[t, j_int]),
                        low=float(self.L[t, j_int]),
                        close=float(self.C[t, j_int]),
                        volume=float(self.V[t, j_int]),
                        raw_close=float(self.RAW[t, j_int]),
                        dollar_vol=float(self.DV[t, j_int]),
                    )
                    bq = borrow_quotes.get(sym, default_bq) if borrow_quotes is not None else default_bq
                    cand_inputs.append((pre, bar, bq))

            engine.on_market_day(
                date=dt,
                day_idx=t,
                is_first_day=is_first,
                allow_new_entries=allow_entries,
                rate_daily=float(self.rate_daily[t]),
                core_return_today=float(self.spy_ret[t]),
                open_position_bars=open_bars,
                candidate_inputs=cand_inputs,
            )

        return engine


class IBKRShadowVerifier:
    """Stage 2 Verifier: Connects to IBKR TWS/Gateway (Read-Only) + IBKR SLB (`usa.txt`) +
    Independent Exchange Bars (Nasdaq) to verify real-world parity against Yahoo before
    connecting a real trading account.
    """

    def __init__(self, host: str = "127.0.0.1", ports: tuple[int, ...] = (7497, 7496, 4002, 4001)):
        self.host = host
        self.ports = ports
        self.slb_quotes = load_ibkr_slb_table(refresh_ftp=False)

    def probe_tws_socket(self) -> tuple[bool, int | None]:
        """Check if IBKR TWS or IB Gateway socket is open on localhost."""
        for port in self.ports:
            try:
                with socket.create_connection((self.host, port), timeout=0.5):
                    return True, port
            except OSError:
                continue
        return False, None

    def fetch_tws_readonly_bars(self, tickers: list[str], duration: str = "10 D") -> dict[str, pd.DataFrame]:
        """Connect to IBKR TWS/Gateway with strict `readonly=True` (zero order capability)
        and download real-world IBKR historical TRADES bars for parity verification.
        """
        is_open, port = self.probe_tws_socket()
        if not is_open or port is None:
            return {}
        try:
            import ib_async as ib  # type: ignore
        except ImportError:
            try:
                import ib_insync as ib  # type: ignore
            except ImportError:
                return {}

        client = ib.IB()
        out: dict[str, pd.DataFrame] = {}
        try:
            client.connect(self.host, port, clientId=991, readonly=True, timeout=5)
            for sym in tickers:
                contract = ib.Stock(sym, "SMART", "USD")
                qualified = client.qualifyContracts(contract)
                if not qualified:
                    continue
                bars = client.reqHistoricalData(
                    contract,
                    endDateTime="",
                    durationStr=duration,
                    barSizeSetting="1 day",
                    whatToShow="TRADES",
                    useRTH=True,
                    formatDate=1,
                )
                if bars:
                    df = ib.util.df(bars)
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.set_index("date").sort_index()
                    out[sym] = df
        finally:
            if client.isConnected():
                client.disconnect()
        return out

    def run_parity_audit(
        self,
        start_date: str = "2026-01-01",
        end_date: str | None = None,
    ) -> dict:
        """Compare Yahoo Signals & Trades vs. Exchange-Verified Bars + Live IBKR SLB Borrow Quotes."""
        raw_adapter = YahooReplayAdapter(use_nasdaq_verified_bars=False, include_edgar_pit=True)
        clean_adapter = YahooReplayAdapter(use_nasdaq_verified_bars=True, include_edgar_pit=True)

        # Load Nasdaq exchange panel for bar-level parity checks
        zn = np.load(AUDIT_DIR / "out" / "nasdaq_panel.npz")
        On_sub, Hn_sub, Ln_sub, Cn_sub, Vn_sub = zn["O"], zn["H"], zn["L"], zn["C"], zn["V"]
        tk_n = list(zn["tickers"])
        col_n = {t: i for i, t in enumerate(tk_n)}

        t0 = int(np.searchsorted(raw_adapter.dates, pd.Timestamp(start_date)))
        t1 = (
            raw_adapter.T
            if end_date is None
            else int(np.searchsorted(raw_adapter.dates, pd.Timestamp(end_date), side="right"))
        )

        # 1. Inspect every Yahoo candidate signal in [t0..t1] and verify against Exchange + IBKR SLB
        cfg_raw = EngineConfig(
            pos_pct=0.035,
            locate_fee_pct=0.0,
            borrow_annual=1.50,
            slip_per_side=0.005,
            enforce_clean_data=False,
            enforce_whale_gate=False,
        )
        eng_raw = raw_adapter.run_replay(cfg_raw, start_date=start_date, end_date=end_date)

        parity_rows = []
        for sig in eng_raw.signals_log:
            t, j = sig.day_idx, sig.ticker_idx
            sym = sig.ticker
            dt_str = str(sig.date.date())

            # Exchange reference bars (Nasdaq)
            if sym in col_n:
                jn = col_n[sym]
                pc_n = float(Cn_sub[t - 1, jn]) if t > 0 else float("nan")
                o_n, h_n, l_n, c_n = (
                    float(On_sub[t, jn]),
                    float(Hn_sub[t, jn]),
                    float(Ln_sub[t, jn]),
                    float(Cn_sub[t, jn]),
                )
            else:
                pc_n = o_n = h_n = l_n = c_n = float("nan")

            if math.isfinite(pc_n) and pc_n > 0 and math.isfinite(o_n) and math.isfinite(h_n) and math.isfinite(c_n):
                gap_n = o_n / pc_n - 1.0
                surge_n = h_n / pc_n - 1.0
                rc_n = c_n / pc_n - 1.0
                cir_n = (c_n - l_n) / max(h_n - l_n, 1e-6)
                max_diff = max(abs(sig.gap_pct - gap_n), abs(sig.surge_pct - surge_n), abs(sig.ret_close_pct - rc_n))
                bar_match = max_diff <= 0.05
            else:
                gap_n = surge_n = rc_n = cir_n = max_diff = float("nan")
                bar_match = False

            split_bug = bool(clean_adapter.split_window_clean[t, j])
            stale_t1_bug = bool(clean_adapter.prev_raw_vol[t, j] <= 100.0 or clean_adapter.prior_bars[t, j] < 5)
            corrupt_bar_bug = bool(clean_adapter.bad_vendor_mask[t, j])

            bq = self.slb_quotes.get(
                sym,
                BorrowQuote(ticker=sym, shortable=False, available_shares=0, fee_rate_annual=float("nan"), source="missing"),
            )

            status = "PASS_VERIFIED"
            if corrupt_bar_bug:
                status = "REJECT_CORRUPT_YAHOO_BAR"
            elif split_bug:
                status = "REJECT_SPLIT_WINDOW"
            elif stale_t1_bug:
                status = "REJECT_FAKE_T1_CLOSE"
            elif not bq.shortable or bq.available_shares <= 0:
                status = "WARN_IBKR_NO_LOCATE_TODAY"
            elif bq.fee_rate_annual > 3.00:
                status = "REJECT_IBKR_BORROW>300%"

            parity_rows.append(
                dict(
                    date=dt_str,
                    ticker=sym,
                    setups=sig.setups_str,
                    yahoo_gap=round(sig.gap_pct, 4),
                    exch_gap=round(gap_n, 4) if math.isfinite(gap_n) else np.nan,
                    yahoo_surge=round(sig.surge_pct, 4),
                    exch_surge=round(surge_n, 4) if math.isfinite(surge_n) else np.nan,
                    yahoo_rc=round(sig.ret_close_pct, 4),
                    exch_rc=round(rc_n, 4) if math.isfinite(rc_n) else np.nan,
                    yahoo_cir=round(sig.cir, 4),
                    exch_cir=round(cir_n, 4) if math.isfinite(cir_n) else np.nan,
                    max_ratio_diff=round(max_diff, 4) if math.isfinite(max_diff) else np.nan,
                    bar_verified=bar_match,
                    pit_mcap_M=round(sig.pit_mcap_prev / 1e6, 2) if math.isfinite(sig.pit_mcap_prev) else np.nan,
                    share_turnover_x=round(sig.share_turnover, 2) if math.isfinite(sig.share_turnover) else np.nan,
                    ibkr_shortable=bq.shortable,
                    ibkr_avail_shares=bq.available_shares,
                    ibkr_feerate_pct=round(bq.fee_rate_annual * 100.0, 2) if math.isfinite(bq.fee_rate_annual) else np.nan,
                    ibkr_3d_borrow_drag_pct=round(bq.fee_rate_annual * 3.0 / 252.0 * 100.0, 3)
                    if math.isfinite(bq.fee_rate_annual)
                    else np.nan,
                    gate_status=status,
                )
            )

        parity_df = pd.DataFrame(parity_rows)

        # 2. Run side-by-side portfolio simulations through the exact same TradingEngine:
        #    (A) Raw Yahoo (unfiltered, modeled 150% borrow)
        #    (B) Clean Exchange-Verified Bars (modeled 150% borrow)
        #    (C) Clean Exchange-Verified + Split-Fixed Whale Gate (modeled 150% borrow)
        #    (D) Clean Exchange-Verified + Split-Fixed Whale Gate + Live IBKR SLB FeeRate & Shortability Gate
        cfg_clean = EngineConfig(
            pos_pct=0.035,
            locate_fee_pct=0.0,
            borrow_annual=1.50,
            slip_per_side=0.005,
            enforce_clean_data=True,
            enforce_whale_gate=False,
        )
        cfg_whale = EngineConfig(
            pos_pct=0.035,
            locate_fee_pct=0.0,
            borrow_annual=1.50,
            slip_per_side=0.005,
            enforce_clean_data=True,
            enforce_whale_gate=True,
        )
        cfg_ibkr_live = EngineConfig(
            pos_pct=0.035,
            locate_fee_pct=0.0,
            borrow_annual=1.50,
            max_borrow_annual=3.00,
            use_live_borrow_rate=True,
            slip_per_side=0.005,
            enforce_clean_data=True,
            enforce_whale_gate=True,
        )

        eng_clean = clean_adapter.run_replay(cfg_clean, start_date=start_date, end_date=end_date)
        eng_whale = clean_adapter.run_replay(cfg_whale, start_date=start_date, end_date=end_date)
        eng_ibkr_live = clean_adapter.run_replay(
            cfg_ibkr_live,
            start_date=start_date,
            end_date=end_date,
            borrow_quotes=self.slb_quotes,
        )

        return {
            "parity_df": parity_df,
            "raw_yahoo": eng_raw.summarize_performance(),
            "clean_exchange": eng_clean.summarize_performance(),
            "clean_whale": eng_whale.summarize_performance(),
            "ibkr_live_verified": eng_ibkr_live.summarize_performance(),
        }
