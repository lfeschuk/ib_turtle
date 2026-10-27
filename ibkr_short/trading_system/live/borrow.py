"""IBKR short-stock availability and fee file (ftp2.interactivebrokers.com/usa.txt), without research imports."""
from __future__ import annotations

import ftplib
import io
import logging
import math
import time
from pathlib import Path

log = logging.getLogger(__name__)


class BorrowTable:
    """Annual borrow fee by symbol from IBKR's public short-stock file, refreshed at most every few hours."""

    def __init__(self, cache_path: Path, max_age_s: float = 4 * 3600):
        self.cache_path = cache_path
        self.max_age_s = max_age_s
        self._fees: dict[str, float] = {}
        self._loaded_at = 0.0

    def _download(self) -> None:
        ftp = ftplib.FTP("ftp2.interactivebrokers.com", timeout=20)
        try:
            ftp.login("shortstock", "")
            buf = io.BytesIO()
            ftp.retrbinary("RETR usa.txt", buf.write)
        finally:
            ftp.close()
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_bytes(buf.getvalue())

    def _parse(self) -> None:
        fees: dict[str, float] = {}
        for line in self.cache_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split("|")
            if len(parts) < 8 or line.startswith("#") or parts[0] == "SYM":
                continue
            try:
                fee = float(parts[6]) / 100.0
            except ValueError:
                continue
            if math.isfinite(fee):
                fees[parts[0].strip()] = max(0.0, fee)
        self._fees = fees
        self._loaded_at = time.time()

    def refresh(self, force: bool = False) -> None:
        fresh_file = self.cache_path.exists() and time.time() - self.cache_path.stat().st_mtime < self.max_age_s
        if force or not fresh_file:
            try:
                self._download()
            except Exception as exc:  # keep the last good copy
                log.warning("could not refresh the IBKR short-stock file: %s", type(exc).__name__)
        if self.cache_path.exists():
            self._parse()

    def fee(self, symbol: str) -> float | None:
        if not self._fees or time.time() - self._loaded_at > self.max_age_s:
            self.refresh()
        return self._fees.get(symbol)
