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
class LiveConfig:
    mode: str = "shadow"
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


def _apply(obj, values: dict) -> None:
    known = {f.name for f in fields(obj)}
    for key, value in values.items():
        if key not in known:
            raise ValueError(f"unknown setting: {key}")
        if key == "sizing":
            _apply(obj.sizing, value)
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
