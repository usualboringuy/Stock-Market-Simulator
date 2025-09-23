import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

MARKET_OPEN = time(9, 0)  # 09:00 IST
MARKET_CLOSE = time(15, 30)  # 15:30 IST


def now_ist() -> datetime:
    return datetime.now(tz=IST)


def is_market_day(dt: datetime) -> bool:
    # Monday=0 ... Sunday=6, market Mon-Fri only
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
    # SmartAPI format: "YYYY-MM-DD HH:MM" (IST) as per official docs
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    dt_ist = dt.astimezone(IST)
    return dt_ist.strftime("%Y-%m-%d %H:%M")


def clamp_market_hours(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    # Ensure both dates are tz-aware IST for consistent formatting
    if start.tzinfo is None:
        start = start.replace(tzinfo=IST)
    if end.tzinfo is None:
        end = end.replace(tzinfo=IST)
    return start.astimezone(IST), end.astimezone(IST)


def parse_iso_ist(s: str) -> datetime:
    s = s.strip()
    # Fix inputs like "2025-09-22T09:00:00 05:30" (space instead of '+')
    m = re.search(r"(.*[T\s]\d{2}:\d{2}:\d{2})\s(\d{2}:\d{2})$", s)
    if m and "+" not in s and "-" not in s[m.start(2) - 1 : m.start(2)]:
        s = f"{m.group(1)}+{m.group(2)}"
    # Accept ISO-like strings; if no tz, assume IST
    dt = (
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        if "T" in s or " " in s
        else datetime.fromisoformat(s)
    )
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def last_n_days_endpoints(n: int) -> tuple[datetime, datetime]:
    end = now_ist()
    start = end - timedelta(days=n)
    return start, end
