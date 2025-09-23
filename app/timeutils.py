from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(15, 30)


def now_ist() -> datetime:
    return datetime.now(tz=IST)


def is_market_day(dt: datetime) -> bool:
    return dt.weekday() < 5


def is_market_open(dt: datetime | None = None) -> bool:
    if dt is None:
        dt = now_ist()
    if not is_market_day(dt):
        return False
    t = dt.timetz()
    return (t >= MARKET_OPEN.replace(tzinfo=IST)) and (
        t <= MARKET_CLOSE.replace(tzinfo=IST)
    )


def to_smartapi_str(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    dt_ist = dt.astimezone(IST)
    return dt_ist.strftime("%Y-%m-%d %H:%M")


def clamp_market_hours(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    if start.tzinfo is None:
        start = start.replace(tzinfo=IST)
    if end.tzinfo is None:
        end = end.replace(tzinfo=IST)
    return start.astimezone(IST), end.astimezone(IST)


def parse_iso_ist(s: str) -> datetime:
    # Accept 'YYYY-MM-DD' or full iso; assume IST if no tz.
    s = s.strip()
    # Fix inputs where '+' became a space before offset, e.g. "2025-09-22T09:00:00 05:30"
    m = re.search(r"(.*[T\s]\d{2}:\d{2}:\d{2})\s(\d{2}:\d{2})$", s)
    if m and "+" not in s and "-" not in s[m.start(2) - 1 : m.start(2)]:
        s = f"{m.group(1)}+{m.group(2)}"
    # Add time if only date provided
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        s = s + "T00:00:00"
    dt = (
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        if ("T" in s or " " in s)
        else datetime.fromisoformat(s)
    )
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def last_n_days_endpoints(n: int) -> tuple[datetime, datetime]:
    end = now_ist()
    start = end - timedelta(days=n)
    return start, end


def start_of_day_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    dt = dt.astimezone(IST)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    dt = dt.astimezone(IST)
    return dt.replace(hour=23, minute=59, second=0, microsecond=0)
