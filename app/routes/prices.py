from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from ..candles import fallback_daily_if_empty, normalize_candles
from ..timeutils import is_market_open, now_ist

router = APIRouter(prefix="/api", tags=["prices"])


def _downsample(series: List[dict], max_points: int) -> List[dict]:
    n = len(series)
    if n <= max_points:
        return series
    step = max(1, n // max_points)
    out = [series[i] for i in range(0, n, step)]
    if out and out[-1] is not series[-1]:
        out.append(series[-1])
    return out


@router.post("/prices/live")
def batch_live_prices(req: Dict[str, Any]) -> Dict[str, Any]:
    # Lightweight schema parsing to avoid tight coupling
    tokens = list(dict.fromkeys(req.get("tokens") or []))
    minutes = int(req.get("minutes", 15))
    include_series = bool(req.get("include_series", True))
    series_points = int(req.get("series_points", 40))

    if not tokens:
        raise HTTPException(status_code=400, detail="tokens required")
    if len(tokens) > 60:
        tokens = tokens[:60]

    now = now_ist()
    start = now - timedelta(minutes=minutes + 1)

    result: Dict[str, Dict[str, Any]] = {}
    for tok in tokens:
        try:
            # Primary: recent minute candles
            raw = fallback_daily_if_empty("NSE", tok, "ONE_MINUTE", start, now)
            series = normalize_candles(raw)
            last = float(series[-1]["c"]) if series else None

            payload: Dict[str, Any] = {"last": last}
            if include_series:
                compact: List[Dict[str, Any]] = [
                    {"t": s["t"], "c": s["c"]} for s in series
                ]

                # If series is too short (e.g., market closed), fetch last 30 days daily for sparkline
                if len(compact) < 3:
                    dstart = now - timedelta(days=30)
                    draw = fallback_daily_if_empty("NSE", tok, "ONE_DAY", dstart, now)
                    dser = normalize_candles(draw)
                    compact = [{"t": s["t"], "c": s["c"]} for s in dser][
                        -series_points:
                    ]

                payload["series"] = _downsample(compact, series_points)

            result[tok] = payload
        except Exception:
            result[tok] = {"last": None}
            if include_series:
                result[tok]["series"] = []

    return {
        "ok": True,
        "market_open": is_market_open(),
        "server_time": now.isoformat(),
        "prices": result,
    }
