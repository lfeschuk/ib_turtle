"""Vol-Scaled 0DTE SPX Put Broken-Wing Butterfly (BWB) strategy and Earned-Money Kelly sizing."""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np

from .config import BwbSettings

FEE_PER_LEG_PTS = 0.0135   # $1.35 per contract per leg on IBKR SPXW ($100 multiplier)
SETTLE_FEE_PTS = 0.0100    # $1.00 per ITM contract at cash settlement
T_0DTE = 1.0 / 252.0
SQRT_T_0DTE = math.sqrt(T_0DTE)
_INV_SQRT2 = 1.0 / math.sqrt(2.0)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(float(x) * _INV_SQRT2))

# Expected net return per unit of W_risk collateral on F1-active days from historical calibration
EXPECTED_RET_BY_DELTA = {
    0.20: 0.01595,
    0.15: 0.01178,
}
SIGMA_RET_BY_DELTA = {
    0.20: 0.145,
    0.15: 0.125,
}

_Z_GRID_CACHE: dict[float, tuple[np.ndarray, np.ndarray]] = {}


def iv_ratio_0dte(z: float | np.ndarray) -> np.ndarray:
    """Empirical Cboe 0DTE SPX skew & smile multiplier relative to 1-day ATM IV."""
    z_arr = np.asarray(z, dtype=float)
    r = np.where(
        z_arr < 0.0,
        1.0 + 0.1903 * (-z_arr) + 0.0126 * (z_arr ** 2),
        1.0 - 0.1560 * z_arr + 0.0735 * (z_arr ** 2),
    )
    return np.clip(r, 0.70, 2.50)


def solve_z_for_delta(target_abs_delta: float, is_call: bool = False, atm_iv_ref: float = 0.115) -> float:
    """Finds log-moneyness in 1D SD units matching the target option delta under the 0DTE smile."""
    def obj(z: float) -> float:
        sig = atm_iv_ref * float(iv_ratio_0dte(z))
        d1 = (-z * atm_iv_ref * SQRT_T_0DTE + 0.5 * (sig ** 2) * T_0DTE) / (sig * SQRT_T_0DTE)
        delta = _norm_cdf(d1) if is_call else (1.0 - _norm_cdf(d1))
        return delta - target_abs_delta

    lo, hi = (-0.5, 4.0) if is_call else (-4.0, 0.5)
    f_lo = obj(lo)
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if abs(hi - lo) < 1e-9:
            return mid
        f_mid = obj(mid)
        if f_mid == 0.0:
            return mid
        if (f_lo < 0.0 and f_mid < 0.0) or (f_lo > 0.0 and f_mid > 0.0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _interp_z_for_delta(delta_mid: float, iv1d: float) -> float:
    key = round(float(delta_mid), 4)
    if key not in _Z_GRID_CACHE:
        iv_grid = np.linspace(0.04, 1.50, 300)
        z_grid = np.array([solve_z_for_delta(key, False, float(v)) for v in iv_grid])
        _Z_GRID_CACHE[key] = (iv_grid, z_grid)
    iv_grid, z_grid = _Z_GRID_CACHE[key]
    return float(np.interp(float(iv1d), iv_grid, z_grid))


def bs_price_0dte(F: float | np.ndarray, K: float | np.ndarray, T: float, r: float,
                  sigma: float | np.ndarray, is_call: bool = False) -> float:
    """Black-Scholes option price in index points."""
    t_eff = max(float(T), 1e-9)
    sq_t = math.sqrt(t_eff)
    sig = max(float(sigma), 1e-4)
    d1 = (math.log(float(F) / float(K)) + 0.5 * (sig ** 2) * t_eff) / (sig * sq_t)
    d2 = d1 - sig * sq_t
    disc = math.exp(-float(r) * t_eff)
    if is_call:
        return float(disc * (float(F) * _norm_cdf(d1) - float(K) * _norm_cdf(d2)))
    return float(disc * (float(K) * _norm_cdf(-d2) - float(F) * _norm_cdf(-d1)))


def half_spread_pts(mid: float) -> float:
    """Single-leg half bid-ask spread in index points on SPXW."""
    return max(0.05, 0.035 + 0.0055 * float(mid))


@dataclass(frozen=True)
class BwbMarketSnapshot:
    """Strictly causal market state at morning decision window ( plus settlement close once available)."""
    day: str
    spot_open: float
    spot_close: float | None
    spot_mark: float
    iv1d: float                # decimal 1D ATM IV (e.g. 0.115 for 11.5%)
    vix_open: float            # VIX index points (e.g. 15.2)
    vix_prev_close: float      # prior day VIX close
    vix1d_prev_close: float    # prior day VIX1D (or VIX9D pre-2022) close
    iv1d_morning_pct: float    # morning 1D IV in vol points (e.g. 11.5)
    rf_annual: float           # annualized T-bill rate (decimal)
    rf_daily: float            # daily T-bill rate (rf_annual / 252)
    f1_pass: bool              # True when causal F1 contango gate passes
    f1_reason: str


@dataclass(frozen=True)
class BwbPlan:
    """4-leg 0DTE Put Broken-Wing Butterfly (+1 K_hi Put, -2 K_mid Put, +1 K_lo Put)."""
    day: str
    symbol: str
    multiplier: float
    spot: float
    iv1d: float
    sd_pts: float
    delta_mid: float
    k_hi: float
    k_mid: float
    k_lo: float
    k_be: float
    w1_pts: float
    w2_pts: float
    w_risk_pts: float
    mid_credit_pts: float
    slip_pts: float
    fee_pts: float
    net_credit_pts: float
    margin_per_contract: float
    expected_ret_on_risk: float
    sigma_ret_on_risk: float


@dataclass(frozen=True)
class BwbSizeDecision:
    """Position sizing output from the Earned-Money ("House-Money") Kelly Ramp."""
    collat_fraction: float
    collat_budget: float
    contracts: float
    margin_dollars: float
    house_cushion_dollars: float
    house_cushion_pct: float
    ramp_progress_pct: float
    sizing_mode: str
    note: str


@dataclass(frozen=True)
class BwbSettlement:
    """4:00 PM ET cash-settlement result for an open 0DTE Put BWB."""
    close_spot: float
    intr_hi_pts: float
    intr_mid_pts: float
    intr_lo_pts: float
    payoff_pts: float
    n_itm_legs: float
    settle_fee_pts: float
    net_pnl_pts: float
    ret_on_risk: float
    pnl_dollars: float
    zone: str


def build_bwb_plan(snap: BwbMarketSnapshot, cfg_bwb: BwbSettings, equity: float = 100_000.0,
                   force_continuous: bool = False) -> BwbPlan:
    """Constructs the vol-scaled 0DTE Put BWB strikes and net credit for today's market snapshot."""
    use_xsp = (cfg_bwb.symbol.upper() == "XSP") or (equity < cfg_bwb.use_xsp_below_nlv)
    scale = 0.1 if use_xsp and snap.spot_open > 1000.0 else 1.0
    sym = "XSP" if use_xsp else "SPXW"
    mult = 100.0

    spot = snap.spot_open * scale
    iv = snap.iv1d
    sd_pts = spot * iv * SQRT_T_0DTE
    z_m = _interp_z_for_delta(cfg_bwb.delta_mid, iv)

    k_m = spot * math.exp(z_m * iv * SQRT_T_0DTE)
    w1 = cfg_bwb.w1_sd * sd_pts
    w_risk = cfg_bwb.w_risk_sd * sd_pts
    k_hi = min(spot, k_m + w1)
    w1_act = k_hi - k_m
    w2_act = w1_act + w_risk
    k_lo = k_m - w2_act

    if cfg_bwb.discrete_strikes and not force_continuous:
        step = 1.0 if sym == "XSP" else 5.0
        k_m = round(k_m / step) * step
        k_hi = max(k_m + step, round(min(spot, k_m + w1) / step) * step)
        w1_act = k_hi - k_m
        w2_act = max(w1_act + step, round((w1_act + w_risk) / step) * step)
        k_lo = k_m - w2_act
        w_risk = w2_act - w1_act

    k_be = 2.0 * k_m - k_hi

    def leg_price(k: float) -> tuple[float, float]:
        z = math.log(k / spot) / (iv * SQRT_T_0DTE)
        sig = iv * float(iv_ratio_0dte(z))
        m = bs_price_0dte(spot, k, T_0DTE, snap.rf_annual, sig, is_call=False)
        return m, half_spread_pts(m) * scale

    m_hi, hs_hi = leg_price(k_hi)
    m_m, hs_m = leg_price(k_m)
    m_lo, hs_lo = leg_price(k_lo)

    cmid = (2.0 * m_m - m_hi - m_lo) - (cfg_bwb.real_curv_bps * 1e-4 * w_risk)
    slip = max(0.05 * scale, 0.65 * (hs_hi + 2.0 * hs_m + hs_lo))
    fee_pts = 4.0 * FEE_PER_LEG_PTS * scale
    cnet = cmid - slip - fee_pts

    d_key = 0.15 if abs(cfg_bwb.delta_mid - 0.15) < 0.025 else 0.20
    exp_ret = EXPECTED_RET_BY_DELTA[d_key]
    sig_ret = SIGMA_RET_BY_DELTA[d_key]

    return BwbPlan(
        day=snap.day,
        symbol=sym,
        multiplier=mult,
        spot=spot,
        iv1d=iv,
        sd_pts=sd_pts,
        delta_mid=cfg_bwb.delta_mid,
        k_hi=k_hi,
        k_mid=k_m,
        k_lo=k_lo,
        k_be=k_be,
        w1_pts=w1_act,
        w2_pts=w2_act,
        w_risk_pts=w_risk,
        mid_credit_pts=cmid,
        slip_pts=slip,
        fee_pts=fee_pts,
        net_credit_pts=cnet,
        margin_per_contract=w_risk * mult,
        expected_ret_on_risk=exp_ret,
        sigma_ret_on_risk=sig_ret,
    )


def compute_earned_kelly_fraction(equity: float, initial_capital: float, hwm: float,
                                  cfg_bwb: BwbSettings, year_start_equity: float | None = None) -> float:
    """Computes daily collateral fraction f_t under the configured Kelly rule."""
    mode = cfg_bwb.sizing_mode
    if mode == "yearly_house" and year_start_equity is not None and year_start_equity > 0:
        w0 = max(float(initial_capital), float(year_start_equity))
    else:
        w0 = max(float(initial_capital), 1.0)
    w = max(float(equity), 0.0) / w0
    hwm_r = max(float(hwm), float(equity), w0) / w0

    if mode == "fixed_7.5":
        return 0.075
    if mode == "fixed_12.5":
        return 0.125
    if mode == "fixed_20":
        return 0.200
    if mode == "hwm_brake":
        cur_dd = 1.0 - (w / hwm_r) if hwm_r > 0 else 0.0
        return float(0.20 - 0.15 * np.clip(cur_dd / 0.30, 0.0, 1.0))
    if mode == "earned_ramp_strict":
        if w <= 1.0:
            return float(cfg_bwb.floor_collat_pct
                         + (cfg_bwb.base_collat_pct - cfg_bwb.floor_collat_pct)
                         * np.clip((w - 0.90) / 0.10, 0.0, 1.0))
        return float(min(
            cfg_bwb.max_collat_pct,
            cfg_bwb.base_collat_pct
            + (cfg_bwb.max_collat_pct - cfg_bwb.base_collat_pct) * np.clip((w - 1.0) / 0.30, 0.0, 1.0),
        ))
    # Default: "earned_ramp" or "yearly_house" (7.5% base + 50% of earned profit above W_0 up to 20.0% cap)
    if w <= 1.0:
        return float(cfg_bwb.floor_collat_pct
                     + (cfg_bwb.base_collat_pct - cfg_bwb.floor_collat_pct)
                     * np.clip((w - 0.85) / 0.15, 0.0, 1.0))
    return float(min(
        cfg_bwb.max_collat_pct,
        (cfg_bwb.base_collat_pct * 1.0 + cfg_bwb.profit_share * (w - 1.0)) / w,
    ))


def size_bwb_bet(equity: float, hwm: float, plan: BwbPlan, cfg_bwb: BwbSettings,
                 discrete_contracts: bool = False, year_start_equity: float | None = None,
                 other_margin_used_pct: float = 0.0) -> BwbSizeDecision:
    """Computes target collateral budget and contract count from the Earned-Money Kelly Ramp."""
    if cfg_bwb.sizing_mode == "yearly_house" and year_start_equity is not None and year_start_equity > 0:
        w0 = max(float(cfg_bwb.initial_capital), float(year_start_equity))
    else:
        w0 = float(cfg_bwb.initial_capital)

    f_raw = compute_earned_kelly_fraction(equity, cfg_bwb.initial_capital, hwm, cfg_bwb,
                                          year_start_equity=year_start_equity)
    f_t = f_raw
    guard_clipped = False
    if (not cfg_bwb.isolated_capital) or other_margin_used_pct > 0.0:
        avail_pct = max(0.0, float(cfg_bwb.max_combined_margin_pct) - float(other_margin_used_pct))
        if f_raw > avail_pct + 1e-6:
            f_t = avail_pct
            guard_clipped = True

    budget = f_t * equity
    if discrete_contracts and plan.margin_per_contract > 0:
        if budget < 0.5 * plan.margin_per_contract:
            contracts = 0.0
        else:
            contracts = float(max(1, round(budget / plan.margin_per_contract)))
        margin_dollars = contracts * plan.margin_per_contract
    else:
        contracts = budget / plan.margin_per_contract if plan.margin_per_contract > 0 else 0.0
        margin_dollars = budget

    house_dollars = max(0.0, equity - w0)
    house_pct = (house_dollars / w0) * 100.0 if w0 > 0 else 0.0
    span = max(1e-9, cfg_bwb.max_collat_pct - cfg_bwb.base_collat_pct)
    ramp_pct = float(np.clip((f_t - cfg_bwb.base_collat_pct) / span, 0.0, 1.0) * 100.0)

    anchor_lbl = "Jan-1 lock" if cfg_bwb.sizing_mode == "yearly_house" else "base"
    if equity <= w0:
        note = f"Principal shield active ({f_t:.2%} collateral, protecting ${w0:,.0f} {anchor_lbl})"
    elif f_t >= cfg_bwb.max_collat_pct - 1e-6:
        note = f"Full House-Money Kelly ({f_t:.1%} collateral, +${house_dollars:,.0f} earned above {anchor_lbl})"
    else:
        note = f"House-Money Ramp ({f_t:.2%} collateral, {ramp_pct:.0f}% to {cfg_bwb.max_collat_pct:.0%} cap)"
    if guard_clipped:
        note += f" [95% shared-margin guard: Gap Short using {other_margin_used_pct:.1%}]"

    return BwbSizeDecision(
        collat_fraction=f_t,
        collat_budget=budget,
        contracts=contracts,
        margin_dollars=margin_dollars,
        house_cushion_dollars=house_dollars,
        house_cushion_pct=house_pct,
        ramp_progress_pct=ramp_pct,
        sizing_mode=cfg_bwb.sizing_mode,
        note=note,
    )


def settle_bwb(plan: BwbPlan, close_spot: float, contracts: float) -> BwbSettlement:
    """Computes exact 4:00 PM ET cash settlement for an open 0DTE Put BWB."""
    scale = 0.1 if plan.symbol == "XSP" and close_spot > 1000.0 else 1.0
    c_spot = float(close_spot) * scale
    intr_hi = max(0.0, plan.k_hi - c_spot)
    intr_mid = max(0.0, plan.k_mid - c_spot)
    intr_lo = max(0.0, plan.k_lo - c_spot)
    payoff = intr_hi - 2.0 * intr_mid + intr_lo
    n_itm = (1.0 if intr_hi > 0 else 0.0) + (2.0 if intr_mid > 0 else 0.0) + (1.0 if intr_lo > 0 else 0.0)
    settle_fee = n_itm * SETTLE_FEE_PTS * scale
    net_pnl_pts = plan.net_credit_pts + payoff - settle_fee
    ret_on_risk = net_pnl_pts / plan.w_risk_pts if plan.w_risk_pts > 0 else 0.0
    pnl_dollars = net_pnl_pts * plan.multiplier * float(contracts)

    if c_spot >= plan.k_hi:
        zone = "FLAT_PROFIT"
    elif c_spot >= plan.k_be:
        zone = "TENT_PROFIT"
    elif c_spot > plan.k_lo:
        zone = "RAMP_LOSS"
    else:
        zone = "MAX_LOSS_FLOOR"

    return BwbSettlement(
        close_spot=c_spot,
        intr_hi_pts=intr_hi,
        intr_mid_pts=intr_mid,
        intr_lo_pts=intr_lo,
        payoff_pts=payoff,
        n_itm_legs=n_itm,
        settle_fee_pts=settle_fee,
        net_pnl_pts=net_pnl_pts,
        ret_on_risk=ret_on_risk,
        pnl_dollars=pnl_dollars,
        zone=zone,
    )
