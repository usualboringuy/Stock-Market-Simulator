from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from .logger import logger
from .smartapi_client import smart_mgr
from .timeutils import IST, clamp_market_hours, now_ist, to_smartapi_str

Interval = Literal[
    "ONE_MINUTE",
    "THREE_MINUTE",
    "FIVE_MINUTE",
    "TEN_MINUTE",
    "FIFTEEN_MINUTE",
    "THIRTY_MINUTE",
    "ONE_HOUR",
    "ONE_DAY",
]


def _interval_chunk_days(interval: Interval) -> int:
    if interval in (
        "ONE_MINUTE",
        "THREE_MINUTE",
        "FIVE_MINUTE",
        "TEN_MINUTE",
        "FIFTEEN_MINUTE",
        "THIRTY_MINUTE",
    ):
        return 1
    if interval == "ONE_HOUR":
        return 7
    return 100


def _retry_fetch(
    exchange: str,
    token: str,
    interval: Interval,
    start: datetime,
    end: datetime,
    max_attempts: int = 3,
) -> Optional[Dict[str, Any]]:
    delay = 0.5
    for attempt in range(1, max_attempts + 1):
        try:
            res = smart_mgr.get_candles(
                exchange, token, interval, to_smartapi_str(start), to_smartapi_str(end)
            )
            if res and res.get("status") is not False and res.get("data"):
                return res
            logger.warning(
                f"Empty/unsuccessful candle response (attempt {attempt}) for {token} {interval} {start} - {end}"
            )
        except Exception as e:
            logger.warning(f"Candle fetch error (attempt {attempt}): {e}")
        if attempt < max_attempts:
            import time

            time.sleep(delay)
            delay *= 2
    return None


def fetch_historical_chunked(
    exchange: str, token: str, interval: Interval, start: datetime, end: datetime
) -> List[list]:
    start, end = clamp_market_hours(start, end)
    chunk_days = _interval_chunk_days(interval)
    result: List[list] = []

    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=chunk_days), end)
        res = _retry_fetch(exchange, token, interval, cur, nxt)
        if res and res.get("data"):
            result.extend(res["data"])
        cur = nxt
    return result


def _is_intraday(interval: Interval) -> bool:
    return interval in (
        "ONE_MINUTE",
        "THREE_MINUTE",
        "FIVE_MINUTE",
        "TEN_MINUTE",
        "FIFTEEN_MINUTE",
        "THIRTY_MINUTE",
        "ONE_HOUR",
    )


def fallback_daily_if_empty(
    exchange: str, token: str, interval: Interval, start: datetime, end: datetime
) -> List[list]:
    # Short-circuit: very old/large intraday ranges often unsupported — go straight to daily
    if _is_intraday(interval):
        too_old = (now_ist() - end) > timedelta(days=45)
        too_large = (end - start) > timedelta(days=45)
        if too_old or too_large:
            logger.info(
                f"Intraday range too old/large for token {token}. Using ONE_DAY fallback for {start} - {end}"
            )
            daily_fast = fetch_historical_chunked(
                exchange, token, "ONE_DAY", start, end
            )
            if daily_fast:
                return daily_fast

    data = fetch_historical_chunked(exchange, token, interval, start, end)
    if data:
        return data

    daily = fetch_historical_chunked(exchange, token, "ONE_DAY", start, end)
    if daily:
        return daily

    today = now_ist()
    last_year = today - timedelta(days=365)
    daily2 = fetch_historical_chunked(exchange, token, "ONE_DAY", last_year, today)
    return daily2 or []


def normalize_candles(raw: List[list]) -> List[dict]:
    out: List[dict] = []
    for row in raw:
        if not row or len(row) < 5:
            continue
        ts = row[0]
        try:
            iso = ts if "T" in ts else (ts.replace(" ", "T") + ":00+05:30")
        except Exception:
            iso = str(ts)
        o, h, l, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
        v = float(row[5]) if len(row) >= 6 and row[5] is not None else None
        item = {"t": iso, "o": o, "h": h, "l": l, "c": c}
        if v is not None:
            item["v"] = v
        out.append(item)
    return out
