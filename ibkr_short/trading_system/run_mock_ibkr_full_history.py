"""Full-History (2001-2026, Train 2001-2018, OOS 2019-2026, Year-by-Year, and Ex-Boom Years)
Verification of `LiveIBKRTradingBot` + `MockIBKRBroker`.

Simulates the Virtual EOD Clock across all 6,487 trading days (2001-01-02 to 2026-10-16),
verifies 100.0000% parity against `TradingEngine` across every era and configuration,
audits all 1,632 historical signals (2001-2026) against Exchange Reference Bars (Nasdaq)
and IBKR SLB (`usa.txt`), and reports year-by-year and non-boom-year performance of the
Mock IBKR execution bot.
"""
from __future__ import annotations

import math
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

from trading_system.adapters import (  # noqa: E402
    IBKRShadowVerifier,
    YahooReplayAdapter,
    load_ibkr_slb_table,
)
from trading_system.mock_ibkr import MockIBKRBroker, MockIBKREODTestEngine  # noqa: E402
from trading_system.models import BorrowQuote, EngineConfig  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 30)


def run_bot_and_verify(
    label: str,
    adapter: YahooReplayAdapter,
    cfg: EngineConfig,
    start_date: str,
    end_date: str | None = None,
    borrow_quotes: dict[str, BorrowQuote] | None = None,
) -> tuple[dict, MockIBKRBroker]:
    """Run both `LiveIBKRTradingBot + MockIBKRBroker` and `TradingEngine` on `[start_date..end_date]`
    and verify 100.0000% parity.
    """
    ref_eng = adapter.run_replay(cfg, start_date=start_date, end_date=end_date, borrow_quotes=borrow_quotes)
    ref_res = ref_eng.summarize_performance()

    harness = MockIBKREODTestEngine(adapter=adapter)
    broker, bot = harness.run_simulation(cfg, start_date=start_date, end_date=end_date, borrow_quotes=borrow_quotes)
    bot_res = broker.summarize_performance()

    eq_diff = float(np.max(np.abs(bot_res["equity_series"].to_numpy() - ref_res["equity_series"].to_numpy())))
    n_bot = bot_res["n_trades"]
    n_ref = ref_res["n_trades"]

    t_bot = bot_res["trades_df"].sort_values(["entry_day_idx", "ticker_idx"]).reset_index(drop=True) if n_bot > 0 else pd.DataFrame()
    t_ref = ref_res["trades_df"].sort_values(["entry_day_idx", "ticker_idx"]).reset_index(drop=True) if n_ref > 0 else pd.DataFrame()
    ret_diff = (
        float(np.max(np.abs(t_bot["net_return_pct"].to_numpy() - t_ref["net_return_pct"].to_numpy())))
        if n_bot == n_ref and n_bot > 0
        else (0.0 if n_bot == 0 and n_ref == 0 else float("inf"))
    )

    n_stop = sum(
        1 for tr in broker._trades.values()
        if tr.order.orderRef == "BRACKET_STOP" and tr.orderStatus.status == "Filled"
    )
    n_tgt = sum(
        1 for tr in broker._trades.values()
        if tr.order.orderRef == "BRACKET_TARGET" and tr.orderStatus.status == "Filled"
    )
    n_time = sum(
        1 for tr in broker._trades.values()
        if tr.order.orderRef == "TIME_EXIT_T3" and tr.orderStatus.status == "Filled"
    )
    n_oca_cancel = sum(
        1 for tr in broker._trades.values()
        if tr.orderStatus.status == "Cancelled" and tr.orderStatus.whyHeld.startswith("OCA_CANCELLED_BY_")
    )

    # Also compute Pre-Tax CAGR from the pre-tax Config or from pre-tax run
    cfg_pretax = EngineConfig(**{**cfg.__dict__, "tax_rate": 0.0})
    pre_eng = adapter.run_replay(cfg_pretax, start_date=start_date, end_date=end_date, borrow_quotes=borrow_quotes)
    pre_res = pre_eng.summarize_performance()

    passed = (
        (n_bot == n_ref)
        and (len(bot.signals_log) == len(ref_eng.signals_log))
        and (eq_diff < 1e-6)
        and (ret_diff < 1e-9)
        and (len(bot_res["invariant_failures"]) == 0)
        and (bot_res["lookahead_violations"] == 0)
    )

    summary = dict(
        Scenario_Era=label,
        Sim_Days=bot_res["invariant_checks_passed"],
        RawBar_Signals=f"{len(bot.signals_log)}/{len(ref_eng.signals_log)}",
        Trades=f"{n_bot}/{n_ref}",
        Win_Rate=f"{bot_res['win_rate']*100:.2f}%" if math.isfinite(bot_res["win_rate"]) else "nan",
        Stop_Rate=f"{bot_res['stop_rate']*100:.2f}%" if math.isfinite(bot_res["stop_rate"]) else "nan",
        Net_Mean_Trade=f"{bot_res['mean_trade_net']*100:+.2f}%" if math.isfinite(bot_res["mean_trade_net"]) else "nan",
        Net_Med_Trade=f"{bot_res['median_trade_net']*100:+.2f}%" if math.isfinite(bot_res["median_trade_net"]) else "nan",
        PreTax_CAGR=f"{pre_res['cagr']*100:+.2f}%",
        AfterTax_CAGR=f"{bot_res['cagr']*100:+.2f}%",
        MaxDD=f"{bot_res['maxdd']*100:.2f}%",
        Sharpe=round(bot_res["sharpe"], 2),
        Orders_Placed=len(broker._trades),
        Stop_Tgt_Time=f"{n_stop}/{n_tgt}/{n_time}",
        OCA_Cancelled=n_oca_cancel,
        Max_Eq_Diff_USD=round(eq_diff, 8),
        Parity="PASS (100%)" if passed else "FAIL",
    )
    return summary, broker


def compute_year_by_year_bot_table(
    brokers_by_config: dict[str, tuple[MockIBKRBroker, MockIBKRBroker]],
) -> pd.DataFrame:
    """Compute year-by-year (2019-2026) and Non-Boom (Ex-2023 & Ex-2025) metrics directly
    from the full OOS (2019-2026) `MockIBKRBroker` runs (both Pre-Tax and After-Tax equity curves & trades).
    """
    years = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
    non_boom_years = [2019, 2020, 2021, 2022, 2024, 2026]
    rows = []

    for cfg_name, (brk_pre, brk_tax) in brokers_by_config.items():
        eq_pre = pd.Series(
            [s.total_equity for s in brk_pre.account_history],
            index=pd.DatetimeIndex([s.date for s in brk_pre.account_history]),
        )
        eq_tax = pd.Series(
            [s.total_equity for s in brk_tax.account_history],
            index=pd.DatetimeIndex([s.date for s in brk_tax.account_history]),
        )
        tdf = pd.DataFrame([t.__dict__ for t in brk_tax.closed_trades])
        tdf["entry_year"] = pd.to_datetime(tdf["entry_date"]).dt.year

        prev_end_pre = brk_pre.cfg.initial_capital
        prev_end_tax = brk_tax.cfg.initial_capital

        for y in years:
            sub_pre = eq_pre[eq_pre.index.year == y]
            sub_tax = eq_tax[eq_tax.index.year == y]
            ty = tdf[tdf["entry_year"] == y]

            ret_pre = float(sub_pre.iloc[-1] / prev_end_pre - 1.0) if len(sub_pre) else 0.0
            ret_tax = float(sub_tax.iloc[-1] / prev_end_tax - 1.0) if len(sub_tax) else 0.0
            prev_end_pre = float(sub_pre.iloc[-1])
            prev_end_tax = float(sub_tax.iloc[-1])

            dd_y = float((sub_pre / sub_pre.cummax() - 1.0).min()) if len(sub_pre) else 0.0
            d_ret = sub_pre.pct_change().dropna()
            sh_y = float(d_ret.mean() / d_ret.std() * np.sqrt(252.0)) if len(d_ret) > 1 and d_ret.std() > 0 else float("nan")

            n_tr = len(ty)
            wr = float((ty["net_return_pct"] > 0).mean()) if n_tr else float("nan")
            sr = float((ty["exit_reason"] == "stop").mean()) if n_tr else float("nan")
            mn = float(ty["net_return_pct"].mean()) if n_tr else float("nan")
            md = float(ty["net_return_pct"].median()) if n_tr else float("nan")

            rows.append(
                dict(
                    Config=cfg_name,
                    Period=str(y) if y != 2026 else "2026 YTD",
                    Trades=n_tr,
                    Win_Rate=f"{wr*100:.1f}%" if math.isfinite(wr) else "nan",
                    Stop_Rate=f"{sr*100:.1f}%" if math.isfinite(sr) else "nan",
                    Net_Mean_Trade=f"{mn*100:+.2f}%" if math.isfinite(mn) else "nan",
                    Net_Med_Trade=f"{md*100:+.2f}%" if math.isfinite(md) else "nan",
                    PreTax_Return=f"{ret_pre*100:+.2f}%",
                    AfterTax_Return=f"{ret_tax*100:+.2f}%",
                    InYear_MaxDD=f"{dd_y*100:.2f}%",
                    Sharpe=round(sh_y, 2) if math.isfinite(sh_y) else np.nan,
                )
            )

        # Add Non-Boom 6 Years Combined (Ex-2023 & Ex-2025) row
        tnb = tdf[tdf["entry_year"].isin(non_boom_years)]
        n_nb = len(tnb)
        wr_nb = float((tnb["net_return_pct"] > 0).mean()) if n_nb else float("nan")
        sr_nb = float((tnb["exit_reason"] == "stop").mean()) if n_nb else float("nan")
        mn_nb = float(tnb["net_return_pct"].mean()) if n_nb else float("nan")
        md_nb = float(tnb["net_return_pct"].median()) if n_nb else float("nan")

        # Geometric annualized return across the 6 non-boom years
        y_rets_pre = []
        y_rets_tax = []
        p_pre = brk_pre.cfg.initial_capital
        p_tax = brk_tax.cfg.initial_capital
        for y in years:
            s_p = eq_pre[eq_pre.index.year == y]
            s_t = eq_tax[eq_tax.index.year == y]
            r_p = float(s_p.iloc[-1] / p_pre)
            r_t = float(s_t.iloc[-1] / p_tax)
            p_pre = float(s_p.iloc[-1])
            p_tax = float(s_t.iloc[-1])
            if y in non_boom_years:
                y_rets_pre.append(r_p)
                y_rets_tax.append(r_t)
        nb_years_elapsed = 5.0 + (eq_pre[eq_pre.index.year == 2026].index[-1] - pd.Timestamp("2026-01-02")).days / 365.25
        cagr_nb_pre = float(np.prod(y_rets_pre) ** (1.0 / nb_years_elapsed) - 1.0)
        cagr_nb_tax = float(np.prod(y_rets_tax) ** (1.0 / nb_years_elapsed) - 1.0)

        rows.append(
            dict(
                Config=cfg_name,
                Period="Ex-2023&2025 (6 Non-Boom Yrs)",
                Trades=n_nb,
                Win_Rate=f"{wr_nb*100:.1f}%",
                Stop_Rate=f"{sr_nb*100:.1f}%",
                Net_Mean_Trade=f"{mn_nb*100:+.2f}%",
                Net_Med_Trade=f"{md_nb*100:+.2f}%",
                PreTax_Return=f"{cagr_nb_pre*100:+.2f}%/yr",
                AfterTax_Return=f"{cagr_nb_tax*100:+.2f}%/yr",
                InYear_MaxDD=f"{float((eq_pre[eq_pre.index.year.isin(non_boom_years)] / eq_pre[eq_pre.index.year.isin(non_boom_years)].cummax() - 1.0).min())*100:.2f}%",
                Sharpe=np.nan,
            )
        )

    return pd.DataFrame(rows)


def main():
    print("==================== MOCK IBKR EOD TESTING ENGINE: FULL HISTORY (2001-2026) & YEAR-BY-YEAR ====================")
    raw_adapter = YahooReplayAdapter(use_nasdaq_verified_bars=False, include_edgar_pit=False)
    clean_adapter = YahooReplayAdapter(use_nasdaq_verified_bars=True, include_edgar_pit=True)
    slb_quotes = load_ibkr_slb_table(refresh_ftp=False)

    # 1. Multi-Era Summary Table (2001-2026 Full 26 Yrs, 2001-2018 Train 18 Yrs, 2019-2026 OOS 8 Yrs)
    cfg_raw = EngineConfig(
        pos_pct=0.035, locate_fee_pct=0.0, borrow_annual=1.50, slip_per_side=0.005,
        tax_rate=0.25, enforce_clean_data=False, enforce_whale_gate=False,
    )
    cfg_clean = EngineConfig(
        pos_pct=0.035, locate_fee_pct=0.0, borrow_annual=1.50, slip_per_side=0.005,
        tax_rate=0.25, enforce_clean_data=True, enforce_whale_gate=False,
    )
    cfg_whale = EngineConfig(
        pos_pct=0.035, locate_fee_pct=0.0, borrow_annual=1.50, slip_per_side=0.005,
        tax_rate=0.25, enforce_clean_data=True, enforce_whale_gate=True,
    )
    cfg_ibkr_live = EngineConfig(
        pos_pct=0.035, locate_fee_pct=0.0, borrow_annual=1.50, max_borrow_annual=3.00,
        use_live_borrow_rate=True, slip_per_side=0.005, tax_rate=0.25,
        enforce_clean_data=True, enforce_whale_gate=True,
    )
    cfg_clean_5pct_harsh = EngineConfig(
        pos_pct=0.050, locate_fee_pct=0.0, borrow_annual=1.50, slip_per_side=0.010,
        tax_rate=0.25, enforce_clean_data=True, enforce_whale_gate=False,
    )

    multi_era_runs = [
        # Full 26-Year Span (2001-2026, 6,487 trading days)
        ("1. Full 2001-2026 (26y): Raw Yahoo (3.5%, IBKR 150% Bor)", raw_adapter, cfg_raw, "2001-01-01", None, None),
        ("2. Full 2001-2026 (26y): Surgical Clean (3.5%, IBKR 150% Bor)", clean_adapter, cfg_clean, "2001-01-01", None, None),
        ("3. Full 2001-2026 (26y): Clean + Whale Gate (3.5%, IBKR 150% Bor)", clean_adapter, cfg_whale, "2001-01-01", None, None),
        ("4. Full 2001-2026 (26y): Clean + Whale + Live IBKR SLB Gate (3.5%)", clean_adapter, cfg_ibkr_live, "2001-01-01", None, slb_quotes),
        # Train Era (2001-2018, 4,528 trading days)
        ("5. Train 2001-2018 (18y): Surgical Clean (3.5%, IBKR 150% Bor)", clean_adapter, cfg_clean, "2001-01-01", "2018-12-31", None),
        ("6. Train 2001-2018 (18y): Clean + Whale Gate (3.5%, IBKR 150% Bor)", clean_adapter, cfg_whale, "2001-01-01", "2018-12-31", None),
        # Full Out-of-Sample (2019-2026, 1,959 trading days)
        ("7. OOS 2019-2026 (8y): Raw Yahoo (3.5%, IBKR 150% Bor)", raw_adapter, cfg_raw, "2019-01-01", None, None),
        ("8. OOS 2019-2026 (8y): Surgical Clean (3.5%, IBKR 150% Bor)", clean_adapter, cfg_clean, "2019-01-01", None, None),
        ("9. OOS 2019-2026 (8y): Surgical Clean (5.0%, Harsh 1% Slip, 150% Bor)", clean_adapter, cfg_clean_5pct_harsh, "2019-01-01", None, None),
        ("10. OOS 2019-2026 (8y): Clean + Whale Gate (3.5%, IBKR 150% Bor)", clean_adapter, cfg_whale, "2019-01-01", None, None),
        ("11. OOS 2019-2026 (8y): Clean + Whale + Live IBKR SLB Gate (3.5%)", clean_adapter, cfg_ibkr_live, "2019-01-01", None, slb_quotes),
    ]

    era_rows = []
    oos_brokers: dict[str, tuple[MockIBKRBroker, MockIBKRBroker]] = {}
    harness_raw = MockIBKREODTestEngine(raw_adapter)
    harness_clean = MockIBKREODTestEngine(clean_adapter)

    for label, adp, cfg, s_dt, e_dt, bq in multi_era_runs:
        row, brk_tax = run_bot_and_verify(label, adp, cfg, start_date=s_dt, end_date=e_dt, borrow_quotes=bq)
        era_rows.append(row)
        if s_dt == "2019-01-01" and e_dt is None:
            cfg_pre = EngineConfig(**{**cfg.__dict__, "tax_rate": 0.0})
            h = harness_raw if adp is raw_adapter else harness_clean
            brk_pre, _ = h.run_simulation(cfg_pre, start_date=s_dt, end_date=e_dt, borrow_quotes=bq)
            oos_brokers[label] = (brk_pre, brk_tax)

    df_era = pd.DataFrame(era_rows)
    print("\n--- 1. MULTI-ERA (2001-2026, TRAIN 2001-2018, OOS 2019-2026) MOCK IBKR BOT PARITY & PERFORMANCE ---")
    print(df_era.to_string(index=False))
    df_era.to_csv(SCRATCH_DIR / "out" / "mock_ibkr_multi_era_summary.csv", index=False)

    # 2. Year-by-Year (2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026 YTD, and Ex-2023&2025) Breakdown
    yby_configs = {
        "A. Raw Yahoo (3.5%, 150% Bor)": oos_brokers["7. OOS 2019-2026 (8y): Raw Yahoo (3.5%, IBKR 150% Bor)"],
        "B. Surgical Clean Union (3.5%, 150% Bor)": oos_brokers["8. OOS 2019-2026 (8y): Surgical Clean (3.5%, IBKR 150% Bor)"],
        "C. Clean + Split-Fixed Whale Gate (3.5%, 150% Bor)": oos_brokers["10. OOS 2019-2026 (8y): Clean + Whale Gate (3.5%, IBKR 150% Bor)"],
        "D. Clean + Whale + Live IBKR SLB Gate (3.5%)": oos_brokers["11. OOS 2019-2026 (8y): Clean + Whale + Live IBKR SLB Gate (3.5%)"],
    }
    df_yby = compute_year_by_year_bot_table(yby_configs)
    print("\n--- 2. YEAR-BY-YEAR (2019-2026) & NON-BOOM (EX-2023 & EX-2025) MOCK IBKR BOT PERFORMANCE ---")
    print(df_yby.to_string(index=False))
    df_yby.to_csv(SCRATCH_DIR / "out" / "mock_ibkr_year_by_year_comparison.csv", index=False)

    # 3. Full OOS (2019-2026, 1,501 signals) Stage-2 Signal Gate Breakdown by Year
    verifier = IBKRShadowVerifier()
    audit_oos = verifier.run_parity_audit(start_date="2019-01-01")
    pdf = audit_oos["parity_df"]
    pdf["year"] = pd.to_datetime(pdf["date"]).dt.year
    gate_by_year = pd.crosstab(pdf["year"], pdf["gate_status"], margins=True)
    print("\n--- 3. FULL OOS (2019-2026) PRE-TRADE SIGNAL GATE AUDIT BY YEAR (1,501 RAW YAHOO SIGNALS) ---")
    print(gate_by_year.to_string())
    pdf.to_csv(SCRATCH_DIR / "out" / "stage2_ibkr_vs_yahoo_parity_2019_2026.csv", index=False)
    gate_by_year.to_csv(SCRATCH_DIR / "out" / "stage2_signal_gate_breakdown_by_year.csv")


if __name__ == "__main__":
    main()
