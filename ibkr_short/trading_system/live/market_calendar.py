"""NYSE trading days and closing times, in New York time."""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)

# Full closures and 13:00 early closes. Check nyse.com each December and extend the table.
_HOLIDAYS = {
    2026: {"2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03",
           "2026-09-07", "2026-11-26", "2026-12-25"},
    2027: {"2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05",
           "2027-09-06", "2027-11-25", "2027-12-24"},
}
_EARLY_CLOSES = {
    2026: {"2026-11-27", "2026-12-24"},
    2027: {"2027-11-26"},
}
_warned_years: set[int] = set()


def _known(year: int) -> bool:
    if year not in _HOLIDAYS and year not in _warned_years:
        _warned_years.add(year)
        log.warning("no NYSE holiday table for %s: treating every weekday as a trading day", year)
    return year in _HOLIDAYS


def is_trading_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return not (_known(d.year) and d.isoformat() in _HOLIDAYS[d.year])


def close_time(d: date) -> datetime:
    early = _known(d.year) and d.isoformat() in _EARLY_CLOSES.get(d.year, set())
    return datetime.combine(d, time(13, 0) if early else time(16, 0), tzinfo=NY)


def now_ny() -> datetime:
    return datetime.now(NY)


def next_trading_day(d: date) -> date:
    d = d + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d


def trading_days_between(start: date, end: date) -> int:
    """Number of trading days after `start` up to and including `end` (0 if end <= start)."""
    if end <= start:
        return 0
    n, d = 0, start
    while d < end:
        d += timedelta(days=1)
        if is_trading_day(d):
            n += 1
    return n
