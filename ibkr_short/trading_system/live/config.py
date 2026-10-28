"""Settings for the live service, read from a TOML file, plus secrets from a private JSON file."""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass, field, fields
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 (Ubuntu 22.04)
    import tomli as tomllib

MODES = ("demo", "shadow", "paper", "live")
SIZING_MODES = ("static", "perbet", "perbet_house", "perbet_dd")
BWB_SIZING_MODES = ("earned_ramp", "yearly_house", "earned_ramp_strict", "fixed_7.5", "fixed_12.5", "fixed_20", "hwm_brake")


@dataclass
class SizingSettings:
    mode: str = "static"            # "static", "perbet" (share of per-bet Kelly), "perbet_house" (bigger share for this
                                    # year's profit) or "perbet_dd" (per-bet Kelly with a drawdown limit)
    static_pct: float = 0.035       # fraction of net liquidation per short in static mode
    kelly_mult: float = 1 / 6       # share of the per-bet Kelly size; in "perbet_house", for the money the year started with
    profit_kelly_mult: float = 1 / 3  # share of the per-bet Kelly size for this year's profit in "perbet_house" mode
    dd_limit: float = 0.20          # drawdown limit for per-bet Kelly with drawdown control
    model_path: str = ""            # per-bet Kelly model exported from the research code
    max_position_pct: float = 0.10  # hard cap per short, any mode
    liquidity_cap_pct: float = 0.01 # max notional as a share of today's dollar volume
    tax_rate: float = 0.25          # used only to keep the yearly tax bill out of the drawdown measure


@dataclass
class BwbSettings:
    enabled: bool = True
    initial_capital: float = 100_000.0   # independent $100k paper allocation for Strategy 2 (0DTE Put BWB)
    isolated_capital: bool = True        # track strategy's own $100k ledger independently of shared IBKR account
    delta_mid: float = 0.20              # 20-delta (0.20) or 15-delta (0.15) middle short put strike
    w1_sd: float = 0.32                  # upper wing width in 1D SD units (0.32 for 20d, 0.28 for 15d)
    w_risk_sd: float = 1.30              # lower net risk width in 1D SD units
    real_curv_bps: float = 27.0          # empirical Cboe 0DTE wing curvature haircut in bps of W_risk
    sizing_mode: str = "earned_ramp"     # "earned_ramp" (from W_0) or "yearly_house" (locks in Jan-1 equity each year)
    base_collat_pct: float = 0.075       # 7.5% collateral risk at initial/Jan-1 capital W_0
    floor_collat_pct: float = 0.050      # 5.0% floor if equity dips below W_0
    max_collat_pct: float = 0.200        # 20.0% maximum collateral cap on earned profits
    profit_share: float = 0.50           # 50% of earned profits (W - W_0) allocated to Kelly ramp
    max_combined_margin_pct: float = 0.95  # 95% combined IBKR maintenance margin ceiling when sharing capital
    symbol: str = "SPX"                  # "SPX" (SPXW $100 mult) or "XSP" (Mini-SPX $100 mult, 1/10th notional)
    use_xsp_below_nlv: float = 25_000.0  # auto-select XSP if account equity < $25k
    discrete_strikes: bool = False       # False = continuous backtest parity; True = round to $5 (SPXW) / $1 (XSP)
    min_net_credit_pct: float = 0.0      # 0.0 = auto positive-edge floor (1.85% on 20d, 1.50% on 15d in shadow/paper/live)
    entry_timeout_sec: int = 90          # seconds to work 10:30 AM BAG limit order before cancelling (no hanging limits)
    entry_minutes_after_open: int = 60   # 10:30 AM ET post-initial-balance entry window
    client_id_offset: int = 1            # TWS clientId = cfg.client_id + client_id_offset
    panel_path: str = ""                 # optional custom path to daily_panel.pkl for historical replay


@dataclass
class LiveConfig:
    mode: str = "shadow"
    initial_capital: float = 100_000.0   # independent $100k paper allocation for Strategy 1 (Gap Short)
    isolated_capital: bool = True        # track Strategy 1's own $100k ledger independently in paper/shadow
    tws_host: str = "127.0.0.1"
    tws_port: int = 7497            # TWS paper 7497, TWS live 7496 (IB Gateway: 4002 / 4001)
    client_id: int = 17
    allow_live: bool = False
    http_host: str = "127.0.0.1"    # keep on localhost; publish to the phone with `tailscale serve`
    http_port: int = 8787
    data_dir: str = "~/.local/share/gapshort"
    secrets_path: str = "~/.config/gapshort/secrets.json"
    decision_minutes_before_close: int = 15
    reconcile_minutes_after_close: int = 15
    max_positions: int = 6
    hold_days: int = 3
    cooldown_days: int = 10
    slip_per_side: float = 0.005
    borrow_annual: float = 1.50
    max_borrow_annual: float = 3.00
    demo_start: str = "2026-01-01"
    demo_seconds_per_day: float = 6.0
    ntfy_url: str = ""              # e.g. https://ntfy.sh/<your-private-topic>
    telegram_chat_id: str = ""
    sizing: SizingSettings = field(default_factory=SizingSettings)
    bwb: BwbSettings = field(default_factory=BwbSettings)

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir).expanduser()

    @property
    def secrets_file(self) -> Path:
        return Path(self.secrets_path).expanduser()

    def validate(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if self.mode == "live" and not self.allow_live:
            raise ValueError("live mode needs allow_live = true in the config")
        if self.http_host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("http_host must be localhost; reach it from the phone through `tailscale serve`")
        if self.sizing.mode not in SIZING_MODES:
            raise ValueError(f"sizing.mode must be one of {SIZING_MODES}")
        if self.sizing.mode != "static" and not self.sizing.model_path:
            raise ValueError(f"sizing.mode = '{self.sizing.mode}' needs sizing.model_path")
        if not 0 < self.sizing.static_pct <= self.sizing.max_position_pct:
            raise ValueError("sizing.static_pct must be > 0 and <= sizing.max_position_pct")
        if not 0 < self.sizing.kelly_mult <= 1:
            raise ValueError("sizing.kelly_mult must be > 0 and <= 1")
        if not self.sizing.kelly_mult <= self.sizing.profit_kelly_mult <= 1:
            raise ValueError("sizing.profit_kelly_mult must be >= sizing.kelly_mult and <= 1")
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be > 0")
        if self.bwb.sizing_mode not in BWB_SIZING_MODES:
            raise ValueError(f"bwb.sizing_mode must be one of {BWB_SIZING_MODES}")
        if self.bwb.initial_capital <= 0:
            raise ValueError("bwb.initial_capital must be > 0")
        if not 0.05 <= self.bwb.delta_mid <= 0.40:
            raise ValueError("bwb.delta_mid must be between 0.05 and 0.40")
        if not 0 < self.bwb.base_collat_pct <= self.bwb.max_collat_pct <= 0.50:
            raise ValueError("bwb.base_collat_pct must be > 0 and <= bwb.max_collat_pct <= 0.50")
        if not 0.0 <= self.bwb.min_net_credit_pct <= 0.20:
            raise ValueError("bwb.min_net_credit_pct must be between 0.0 and 0.20")
        if not 5 <= self.bwb.entry_timeout_sec <= 600:
            raise ValueError("bwb.entry_timeout_sec must be between 5 and 600")


def _apply(obj, values: dict) -> None:
    known = {f.name for f in fields(obj)}
    for key, value in values.items():
        if key not in known:
            raise ValueError(f"unknown setting: {key}")
        if key == "sizing":
            _apply(obj.sizing, value)
        elif key == "bwb":
            _apply(obj.bwb, value)
        else:
            setattr(obj, key, value)


def load_config(path: str | os.PathLike | None) -> LiveConfig:
    cfg = LiveConfig()
    if path:
        with open(Path(path).expanduser(), "rb") as fh:
            _apply(cfg, tomllib.load(fh))
    cfg.validate()
    return cfg


def load_secrets(cfg: LiveConfig) -> dict:
    """Secrets live in a JSON file readable only by the owner. Environment variables override it."""
    data: dict = {}
    path = cfg.secrets_file
    if path.exists():
        mode = path.stat().st_mode
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise PermissionError(f"{path} must be readable only by you: chmod 600 {path}")
        data = json.loads(path.read_text())
    for key, env in (("telegram_token", "GAPSHORT_TELEGRAM_TOKEN"), ("ntfy_token", "GAPSHORT_NTFY_TOKEN"),
                     ("healthchecks_url", "GAPSHORT_HEALTHCHECKS_URL")):
        if os.environ.get(env):
            data[key] = os.environ[env]
    # TODO(security): secrets sit in a chmod-600 file on the laptop; a hardware-backed keyring would be stronger.
    return data


def save_secrets(cfg: LiveConfig, data: dict) -> None:
    path = cfg.secrets_file
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
