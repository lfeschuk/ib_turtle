"""Login for the phone app: scrypt password hash, server-side sessions in HttpOnly cookies, double-submit CSRF
tokens, and rate limits."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from collections import deque

from .journal import Journal

SESSION_COOKIE = "__Host-gs_session"
CSRF_COOKIE = "__Host-gs_csrf"
CSRF_HEADER = "x-csrf-token"
SESSION_LIFETIME_S = 14 * 24 * 3600
SESSION_IDLE_S = 3 * 24 * 3600
MIN_PASSWORD_LEN = 12
_SCRYPT = dict(n=2 ** 15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, dk_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        expected = base64.b64decode(dk_b64)
        dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), n=int(n), r=int(r), p=int(p),
                            maxmem=64 * 1024 * 1024, dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk, expected)


def _sid_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthStore:
    def __init__(self, journal: Journal, password_hash: str):
        if not password_hash:
            raise ValueError("no password set")
        self.journal = journal
        self.password_hash = password_hash

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password_hash)

    def create_session(self) -> str:
        token = secrets.token_urlsafe(32)
        self.journal.add_session(_sid_hash(token), SESSION_LIFETIME_S)
        return token

    def valid_session(self, token: str | None) -> bool:
        if not token or len(token) > 128:
            return False
        h = _sid_hash(token)
        s = self.journal.get_session(h)
        now = time.time()
        if s is None:
            return False
        if s["expires"] < now or s["last_seen"] < now - SESSION_IDLE_S:
            self.journal.delete_session(h)
            return False
        self.journal.touch_session(h)
        return True

    def end_session(self, token: str | None) -> None:
        if token:
            self.journal.delete_session(_sid_hash(token))


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_ok(cookie_value: str | None, header_value: str | None) -> bool:
    if not cookie_value or not header_value or len(header_value) > 128:
        return False
    return hmac.compare_digest(cookie_value, header_value)


class TokenBucket:
    """Global request limit (single-user app behind a local proxy)."""

    def __init__(self, capacity: int = 120, refill_per_s: float = 2.0):
        self.capacity = capacity
        self.refill = refill_per_s
        self.tokens = float(capacity)
        self.updated = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.refill)
        self.updated = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class LoginLimiter:
    """At most 5 failed password checks per 15 minutes, then wait."""

    def __init__(self, max_failures: int = 5, window_s: float = 900):
        self.max_failures = max_failures
        self.window_s = window_s
        self.failures: deque[float] = deque()

    def _trim(self) -> None:
        cutoff = time.monotonic() - self.window_s
        while self.failures and self.failures[0] < cutoff:
            self.failures.popleft()

    def blocked(self) -> bool:
        self._trim()
        return len(self.failures) >= self.max_failures

    def retry_after_s(self) -> int:
        self._trim()
        if not self.failures:
            return 0
        return max(1, int(self.failures[0] + self.window_s - time.monotonic()))

    def failure(self) -> None:
        self.failures.append(time.monotonic())

    def success(self) -> None:
        self.failures.clear()

# TODO(security): single password, no second factor. Tailscale limits who can reach the app at all; add TOTP if the
# app is ever exposed beyond your own tailnet.
