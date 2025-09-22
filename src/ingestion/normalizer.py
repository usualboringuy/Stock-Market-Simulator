# src/ingestion/normalizer.py
from typing import Any, Dict, Optional, Iterable
from datetime import datetime, timezone


def _first_present(d: Dict[str, Any], keys: Iterable[str]) -> Optional[Any]:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _parse_timestamp(val: Any) -> datetime:
    # Convert common SmartAPI timestamps to timezone-aware datetime
    if isinstance(val, (int, float)):
        # Heuristic: >1e12 -> ms, else seconds
        secs = float(val) / 1000.0 if val > 1_000_000_000_000 else float(val)
        return datetime.fromtimestamp(secs, tz=timezone.utc)
    if isinstance(val, str):
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ):
            try:
                return datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
            except Exception:
                continue
    # Fallback to now if unrecognized
    return datetime.now(tz=timezone.utc)


def _scale_paise(val: Any) -> Optional[float]:
    # SmartAPI Full/SnapQuote prices are integers in paise for equities
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val) / 100.0
        # sometimes numeric arrives as numeric-like string
        return float(val) / 100.0
    except Exception:
        return None


def normalize_tick(raw: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a SmartAPI tick dict (FULL/SNAP) into a consistent quote schema.
    meta: {"symbol": "...", "token": "...", "name": "...", "exchange":"NSE"}
    """
    # Price
    price = _scale_paise(_first_present(raw, ["last_traded_price", "ltp", "LTP"]))

    # OHLC (SmartAPI provides *_price_of_the_day and closed_price)
    open_ = _scale_paise(_first_present(raw, ["open_price_of_the_day", "open", "o"]))
    high = _scale_paise(_first_present(raw, ["high_price_of_the_day", "high", "h"]))
    low = _scale_paise(_first_present(raw, ["low_price_of_the_day", "low", "l"]))
    close = _scale_paise(_first_present(raw, ["closed_price", "close", "c"]))

    # Volume (day)
    volume = _first_present(raw, ["volume_trade_for_the_day", "volume", "vtt"])
    try:
        volume = int(volume) if volume is not None else None
    except Exception:
        volume = None

    # Best bid/ask from level-1 arrays if present
    bid = None
    ask = None
    best_buys = raw.get("best_5_buy_data")
    best_sells = raw.get("best_5_sell_data")
    if isinstance(best_buys, list) and best_buys:
        bid = _scale_paise(best_buys[0].get("price"))
    if isinstance(best_sells, list) and best_sells:
        ask = _scale_paise(best_sells[0].get("price"))

    # Timestamp: prefer exchange_timestamp (ms), fallback to last_traded_timestamp (sec)
    ts_val = _first_present(
        raw,
        [
            "exchange_timestamp",
            "last_traded_timestamp",
            "last_update_time",
            "time",
            "timestamp",
        ],
    )
    ts = _parse_timestamp(ts_val)

    # Derived change/percent change vs previous close
    change = None
    percent_change = None
    try:
        if price is not None and close is not None:
            change = round(price - close, 4)
            if close != 0:
                percent_change = round((change / close) * 100.0, 4)
    except Exception:
        pass

    doc = {
        "symbol": meta["symbol"],
        "token": meta["token"],
        "name": meta.get("name"),
        "exchange": meta.get("exchange", "NSE"),
        "price": price,
        "volume": volume,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "bid": bid,
        "ask": ask,
        "change": change,
        "percent_change": percent_change,
        "timestamp": ts,  # datetime -> MongoDB Date
        "raw": raw,
    }
    return doc
