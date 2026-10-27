"""Phone notifications (ntfy and/or Telegram) and a healthchecks.io heartbeat. Secrets never reach the logs."""
from __future__ import annotations

import asyncio
import logging
import urllib.parse
import urllib.request

from .config import LiveConfig

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, cfg: LiveConfig, secrets: dict):
        self.ntfy_url = cfg.ntfy_url if cfg.ntfy_url.startswith("https://") else ""
        self.ntfy_token = secrets.get("ntfy_token", "")
        self.telegram_token = secrets.get("telegram_token", "")
        self.telegram_chat = cfg.telegram_chat_id
        hc = secrets.get("healthchecks_url", "")
        self.healthchecks_url = hc if hc.startswith("https://") else ""
        self.prefix = "" if cfg.mode == "live" else f"[{cfg.mode}] "

    @property
    def enabled(self) -> bool:
        return bool(self.ntfy_url or (self.telegram_token and self.telegram_chat))

    def _post_ntfy(self, title: str, text: str, priority: str) -> None:
        headers = {"Title": title, "Priority": priority}
        if self.ntfy_token:
            headers["Authorization"] = f"Bearer {self.ntfy_token}"
        req = urllib.request.Request(self.ntfy_url, data=text.encode(), method="POST", headers=headers)
        urllib.request.urlopen(req, timeout=10).close()

    def _post_telegram(self, title: str, text: str) -> None:
        body = urllib.parse.urlencode({"chat_id": self.telegram_chat, "text": f"{title}\n{text}"}).encode()
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        urllib.request.urlopen(urllib.request.Request(url, data=body, method="POST"), timeout=10).close()

    def _send_blocking(self, title: str, text: str, priority: str) -> None:
        title = self.prefix + title
        if self.ntfy_url:
            try:
                self._post_ntfy(title, text, priority)
            except Exception as exc:
                log.warning("ntfy notification failed: %s", type(exc).__name__)
        if self.telegram_token and self.telegram_chat:
            try:
                self._post_telegram(title, text)
            except Exception as exc:
                log.warning("telegram notification failed: %s", type(exc).__name__)

    async def send(self, title: str, text: str, priority: str = "default") -> None:
        if self.enabled:
            await asyncio.get_running_loop().run_in_executor(None, self._send_blocking, title, text, priority)

    def _ping_blocking(self, ok: bool) -> None:
        url = self.healthchecks_url + ("" if ok else "/fail")
        try:
            urllib.request.urlopen(url, timeout=10).close()
        except Exception as exc:
            log.warning("heartbeat failed: %s", type(exc).__name__)

    async def heartbeat(self, ok: bool = True) -> None:
        if self.healthchecks_url:
            await asyncio.get_running_loop().run_in_executor(None, self._ping_blocking, ok)
