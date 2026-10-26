"""SQLite journal: events, trades, processed fills, daily equity, settings, login sessions, and the backtest twin
of every signal the bot acted on (for the end-of-day report).

Every query is parameterized.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, level TEXT NOT NULL, kind TEXT NOT NULL,
    message TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, entry_date TEXT NOT NULL, entry_price REAL,
    shares REAL NOT NULL, notional REAL, stop REAL, target REAL, score REAL, setups TEXT, status TEXT NOT NULL,
    exit_date TEXT, exit_price REAL, exit_reason TEXT, pnl REAL, exit_shares REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS fills (exec_id TEXT PRIMARY KEY, symbol TEXT, side TEXT, shares REAL, price REAL,
    day TEXT, role TEXT, commission REAL DEFAULT 0, trade_id INTEGER);
CREATE TABLE IF NOT EXISTS equity (day TEXT PRIMARY KEY, nlv REAL NOT NULL, adj REAL NOT NULL);
CREATE TABLE IF NOT EXISTS signals (day TEXT NOT NULL, symbol TEXT NOT NULL, score REAL, setups TEXT,
    action TEXT NOT NULL, detail TEXT, notional REAL, PRIMARY KEY (day, symbol));
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS sessions (sid_hash TEXT PRIMARY KEY, created REAL NOT NULL, last_seen REAL NOT NULL,
    expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS twin (
    id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, symbol TEXT NOT NULL, setups TEXT, score REAL,
    kind TEXT NOT NULL, note TEXT, exp_ret REAL, shares REAL, plan_price REAL, fee_rate REAL, trade_id INTEGER,
    status TEXT NOT NULL DEFAULT 'waiting', close_ok INTEGER,
    m_close REAL, m_entry REAL, m_stop REAL, m_target REAL, m_mark REAL, m_borrow REAL DEFAULT 0, m_last_day TEXT,
    m_exit_day TEXT, m_exit REAL, m_reason TEXT,
    a_mark REAL, a_borrow REAL DEFAULT 0, a_last_day TEXT, a_done INTEGER DEFAULT 0,
    UNIQUE (day, symbol));
CREATE TABLE IF NOT EXISTS edge_daily (
    day TEXT PRIMARY KEY, actual REAL, theory REAL NOT NULL, expected REAL NOT NULL, var REAL NOT NULL,
    missed REAL NOT NULL, n_open INTEGER, n_closed INTEGER);
"""

# Columns added after the first release; older databases get them on startup.
_MIGRATIONS = (("trades", "exit_shares", "REAL DEFAULT 0"), ("fills", "commission", "REAL DEFAULT 0"),
               ("fills", "trade_id", "INTEGER"))

# Twin columns the service may update (column names come only from this list, never from input).
_TWIN_UPDATABLE = frozenset((
    "kind", "note", "shares", "trade_id", "status", "close_ok", "m_close", "m_entry", "m_stop", "m_target", "m_mark",
    "m_borrow", "m_last_day", "m_exit_day", "m_exit", "m_reason", "a_mark", "a_borrow", "a_last_day", "a_done"))
_TWIN_KINDS = ("pending", "taken", "missed", "shadow")
_TWIN_STATUSES = ("waiting", "open", "closed", "void")


class Journal:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(_SCHEMA)
            for table, column, decl in _MIGRATIONS:  # constants, not user input
                cols = {r["name"] for r in self._db.execute(f"PRAGMA table_info({table})")}
                if column not in cols:
                    self._db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        path.chmod(0o600)

    def _q(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, params).fetchall()

    def _insert(self, sql: str, params: tuple) -> int:
        with self._lock:
            return int(self._db.execute(sql, params).lastrowid)

    def reset(self) -> None:
        with self._lock:
            for table in ("events", "trades", "fills", "equity", "signals", "twin", "edge_daily"):
                self._db.execute(f"DELETE FROM {table}")  # table names are constants, not user input

    # events
    def event(self, level: str, kind: str, message: str) -> None:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._q("INSERT INTO events (ts, level, kind, message) VALUES (?, ?, ?, ?)", (ts, level, kind, message))

    def events(self, limit: int = 100) -> list[dict]:
        rows = self._q("SELECT ts, level, kind, message FROM events ORDER BY id DESC LIMIT ?", (int(limit),))
        return [dict(r) for r in rows]

    # trades (a short can fill in several executions; they are merged into one trade)
    def record_entry_fill(self, symbol: str, day: str, price: float, shares: float, plan: dict) -> tuple[int, float, bool]:
        """Add a short-sale execution. Returns (trade id, total shares, whether this opened a new trade)."""
        rows = self._q("SELECT id, entry_price, shares FROM trades WHERE symbol = ? AND entry_date = ? AND status = 'open' "
                       "ORDER BY id DESC LIMIT 1", (symbol, day))
        if rows:
            r = rows[0]
            total = r["shares"] + shares
            vwap = (r["entry_price"] * r["shares"] + price * shares) / total if total > 0 else price
            self._q("UPDATE trades SET shares = ?, entry_price = ? WHERE id = ?", (total, vwap, r["id"]))
            return int(r["id"]), float(total), False
        trade_id = self._insert(
            "INSERT INTO trades (symbol, entry_date, entry_price, shares, notional, stop, target, score, setups, status, "
            "exit_shares) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', 0)",
            (symbol, day, price, shares, plan.get("notional", price * shares), plan.get("stop"), plan.get("target"),
             plan.get("score"), plan.get("setups", "")))
        return trade_id, float(shares), True

    def record_exit_fill(self, symbol: str, day: str, price: float, shares: float, reason: str) -> dict | None:
        """Add a buy-to-cover execution to the open trade; the trade closes when every share is bought back."""
        rows = self._q("SELECT id, entry_price, shares, exit_shares, exit_price, pnl, exit_reason FROM trades "
                       "WHERE symbol = ? AND status = 'open' ORDER BY id LIMIT 1", (symbol,))
        if not rows:
            return None
        r = rows[0]
        done = r["exit_shares"] or 0.0
        take = min(shares, max(r["shares"] - done, 0.0))
        if take <= 0:
            return None
        new_done = done + take
        exit_price = ((r["exit_price"] or 0.0) * done + price * take) / new_done
        pnl = (r["pnl"] or 0.0) + (r["entry_price"] - price) * take if r["entry_price"] else None
        closed = new_done >= r["shares"] - 1e-6
        first_reason = r["exit_reason"] or reason
        self._q("UPDATE trades SET exit_shares = ?, exit_price = ?, pnl = ?, exit_reason = ?, status = ?, exit_date = ? "
                "WHERE id = ?", (new_done, exit_price, pnl, first_reason, "closed" if closed else "open",
                                 day if closed else None, r["id"]))
        return {"id": int(r["id"]), "symbol": symbol, "pnl": pnl, "reason": first_reason, "closed": closed,
                "covered": new_done, "shares": r["shares"]}

    def open_trades(self) -> list[dict]:
        return [dict(r) for r in self._q("SELECT * FROM trades WHERE status = 'open' ORDER BY id")]

    def recent_trades(self, limit: int = 50) -> list[dict]:
        return [dict(r) for r in self._q("SELECT * FROM trades ORDER BY id DESC LIMIT ?", (int(limit),))]

    def trades_by_id(self) -> dict[int, dict]:
        return {int(r["id"]): dict(r) for r in self._q("SELECT * FROM trades")}

    def last_exit_date(self, symbol: str) -> str | None:
        rows = self._q("SELECT MAX(exit_date) AS d FROM trades WHERE symbol = ? AND status = 'closed'", (symbol,))
        return rows[0]["d"] if rows else None

    def realized_pnl_since(self, day: str) -> float:
        rows = self._q("SELECT COALESCE(SUM(pnl), 0) AS p FROM trades WHERE status = 'closed' AND exit_date >= ?",
                       (day,))
        return float(rows[0]["p"])

    # fills (each broker execution is processed once)
    def fill_seen(self, exec_id: str) -> bool:
        return bool(self._q("SELECT 1 FROM fills WHERE exec_id = ?", (exec_id,)))

    def record_fill(self, exec_id: str, symbol: str, side: str, shares: float, price: float, day: str,
                    role: str, commission: float = 0.0, trade_id: int | None = None) -> None:
        self._q("INSERT OR IGNORE INTO fills (exec_id, symbol, side, shares, price, day, role, commission, trade_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (exec_id, symbol, side, shares, price, day, role, commission,
                                                       trade_id))

    def set_fill_commission(self, exec_id: str, commission: float) -> None:
        """IBKR reports commissions a moment after the execution, so they are filled in later."""
        self._q("UPDATE fills SET commission = ? WHERE exec_id = ?", (commission, exec_id))

    def commissions_by_trade(self) -> dict[int, float]:
        rows = self._q("SELECT trade_id, COALESCE(SUM(commission), 0) AS c FROM fills WHERE trade_id IS NOT NULL "
                       "GROUP BY trade_id")
        return {int(r["trade_id"]): float(r["c"]) for r in rows}

    # backtest twin of each signal the bot acted on
    def twin_add(self, day: str, symbol: str, setups: str, score: float, kind: str, note: str, exp_ret: float | None,
                 shares: float, plan_price: float, fee_rate: float | None) -> None:
        if kind not in _TWIN_KINDS:
            raise ValueError(kind)
        self._q("INSERT INTO twin (day, symbol, setups, score, kind, note, exp_ret, shares, plan_price, fee_rate, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'waiting') ON CONFLICT(day, symbol) DO NOTHING",
                (day, symbol, setups, score, kind, note, exp_ret, shares, plan_price, fee_rate))

    def twin_link_fill(self, day: str, symbol: str, trade_id: int, shares: float) -> None:
        self._q("UPDATE twin SET kind = 'taken', note = '', trade_id = ?, shares = ? WHERE day = ? AND symbol = ? "
                "AND kind IN ('pending', 'taken', 'missed')", (trade_id, shares, day, symbol))

    def twin_update(self, twin_id: int, **fields) -> None:
        cols = [c for c in fields if c in _TWIN_UPDATABLE]
        if not cols:
            return
        sets = ", ".join(f"{c} = ?" for c in cols)  # column names from the allow-list above
        self._q(f"UPDATE twin SET {sets} WHERE id = ?", tuple(fields[c] for c in cols) + (twin_id,))

    def twin_rows(self, kinds: tuple[str, ...] = _TWIN_KINDS, statuses: tuple[str, ...] = _TWIN_STATUSES,
                  day: str | None = None) -> list[dict]:
        kinds = tuple(k for k in kinds if k in _TWIN_KINDS)
        statuses = tuple(s for s in statuses if s in _TWIN_STATUSES)
        if not kinds or not statuses:
            return []
        sql = (f"SELECT * FROM twin WHERE kind IN ({','.join('?' * len(kinds))}) "
               f"AND status IN ({','.join('?' * len(statuses))})")
        params: tuple = kinds + statuses
        if day is not None:
            sql += " AND day = ?"
            params += (day,)
        return [dict(r) for r in self._q(sql + " ORDER BY id", params)]

    def twin_active(self) -> list[dict]:
        """Rows the end-of-day update still has to move forward."""
        return [dict(r) for r in self._q("SELECT * FROM twin WHERE kind != 'pending' AND (status IN ('waiting', 'open') "
                                         "OR (kind = 'taken' AND status = 'closed' AND a_done = 0)) ORDER BY id")]

    def twin_last_exit(self, symbol: str) -> str | None:
        rows = self._q("SELECT MAX(m_exit_day) AS d FROM twin WHERE symbol = ? AND kind = 'shadow' AND status = 'closed'",
                       (symbol,))
        return rows[0]["d"] if rows else None

    # end-of-day report snapshots (cumulative values in dollars)
    def edge_upsert(self, day: str, actual: float | None, theory: float, expected: float, var: float, missed: float,
                    n_open: int, n_closed: int) -> None:
        self._q("INSERT INTO edge_daily (day, actual, theory, expected, var, missed, n_open, n_closed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(day) DO UPDATE SET actual = excluded.actual, "
                "theory = excluded.theory, expected = excluded.expected, var = excluded.var, missed = excluded.missed, "
                "n_open = excluded.n_open, n_closed = excluded.n_closed",
                (day, actual, theory, expected, var, missed, n_open, n_closed))

    def edge_series(self, limit: int = 400) -> list[dict]:
        rows = self._q("SELECT * FROM (SELECT * FROM edge_daily ORDER BY day DESC LIMIT ?) ORDER BY day", (int(limit),))
        return [dict(r) for r in rows]

    # equity
    def record_equity(self, day: str, nlv: float, adj: float) -> None:
        self._q("INSERT INTO equity (day, nlv, adj) VALUES (?, ?, ?) ON CONFLICT(day) DO UPDATE SET nlv = excluded.nlv,"
                " adj = excluded.adj", (day, nlv, adj))

    def equity(self, limit: int = 400) -> list[dict]:
        rows = self._q("SELECT day, nlv, adj FROM (SELECT * FROM equity ORDER BY day DESC LIMIT ?) ORDER BY day",
                       (int(limit),))
        return [dict(r) for r in rows]

    def peak_adj_since(self, day: str) -> float | None:
        rows = self._q("SELECT MAX(adj) AS p FROM equity WHERE day >= ?", (day,))
        return rows[0]["p"] if rows and rows[0]["p"] is not None else None

    def last_equity_before(self, day: str) -> dict | None:
        rows = self._q("SELECT day, nlv, adj FROM equity WHERE day < ? ORDER BY day DESC LIMIT 1", (day,))
        return dict(rows[0]) if rows else None

    def first_equity_since(self, day: str) -> dict | None:
        rows = self._q("SELECT day, nlv, adj FROM equity WHERE day >= ? ORDER BY day LIMIT 1", (day,))
        return dict(rows[0]) if rows else None

    # signals
    def record_signal(self, day: str, symbol: str, score: float, setups: str, action: str, detail: str,
                      notional: float) -> None:
        self._q("INSERT INTO signals (day, symbol, score, setups, action, detail, notional) VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(day, symbol) DO UPDATE SET score = excluded.score, setups = excluded.setups,"
                " action = excluded.action, detail = excluded.detail, notional = excluded.notional",
                (day, symbol, score, setups, action, detail, notional))

    def signals(self, day: str) -> list[dict]:
        rows = self._q("SELECT symbol, score, setups, action, detail, notional FROM signals WHERE day = ? "
                       "ORDER BY score DESC", (day,))
        return [dict(r) for r in rows]

    def last_signal_day(self) -> str | None:
        rows = self._q("SELECT MAX(day) AS d FROM signals")
        return rows[0]["d"] if rows else None

    # settings
    def get(self, key: str, default: str | None = None) -> str | None:
        rows = self._q("SELECT value FROM kv WHERE key = ?", (key,))
        return rows[0]["value"] if rows else default

    def set(self, key: str, value: str) -> None:
        self._q("INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value))

    # sessions (only a hash of the session token is stored)
    def add_session(self, sid_hash: str, lifetime_s: float) -> None:
        now = time.time()
        self._q("INSERT INTO sessions (sid_hash, created, last_seen, expires) VALUES (?, ?, ?, ?)",
                (sid_hash, now, now, now + lifetime_s))

    def get_session(self, sid_hash: str) -> dict | None:
        rows = self._q("SELECT sid_hash, created, last_seen, expires FROM sessions WHERE sid_hash = ?", (sid_hash,))
        return dict(rows[0]) if rows else None

    def touch_session(self, sid_hash: str) -> None:
        self._q("UPDATE sessions SET last_seen = ? WHERE sid_hash = ?", (time.time(), sid_hash))

    def delete_session(self, sid_hash: str) -> None:
        self._q("DELETE FROM sessions WHERE sid_hash = ?", (sid_hash,))

    def delete_all_sessions(self) -> None:
        self._q("DELETE FROM sessions")

    def purge_sessions(self, idle_s: float) -> None:
        now = time.time()
        self._q("DELETE FROM sessions WHERE expires < ? OR last_seen < ?", (now, now - idle_s))
