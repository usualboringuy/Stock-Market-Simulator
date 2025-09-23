from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .candles import Interval, fallback_daily_if_empty, normalize_candles
from .config import settings
from .instruments import instruments
from .logger import logger
from .smartapi_client import smart_mgr
from .timeutils import is_market_open, last_n_days_endpoints, now_ist, parse_iso_ist

app = FastAPI(title="Stock Simulator - Module 1 Data Service")


@app.on_event("startup")
def _startup():
    logger.info("Starting Module 1 Data Service")
    # Lazy login (done upon first call), but we can attempt to login historical proactively
    try:
        if settings.angel_hist_api_key:
            smart_mgr.ensure_logged_in()
    except Exception as e:
        logger.warning(f"Historical session not ready yet: {e}")


@app.on_event("shutdown")
def _shutdown():
    try:
        smart_mgr.terminate_all()
    except Exception:
        pass


@app.get("/api/health")
def health():
    ist = now_ist().isoformat()
    open_now = is_market_open()
    return JSONResponse(
        {
            "ok": True,
            "time_ist": ist,
            "market_open": open_now,
            "historical_api_key_present": bool(settings.angel_hist_api_key),
            "trading_api_key_present": bool(settings.angel_market_api_key),
            "stocks_csv": settings.stocks_csv,
        }
    )


@app.get("/api/instruments/search")
def search_instruments(
    q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=50)
):
    results = instruments.search(q, limit=limit)
    return [
        {
            "symbol": r.symbol,
            "token": r.token,
            "name": r.name,
            "exchange": "NSE",
        }
        for r in results
    ]


@app.get("/api/candles")
def get_candles(
    symbol: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    interval: Interval = Query("ONE_DAY"),
    frm: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
):
    """
    Historical candles on-demand (SmartAPI Historical app).
    - One of (symbol, token) is required (symbol preferred).
    - interval: as per SmartAPI docs.
    - from/to: ISO date strings. If omitted, defaults to last 30 days.
    Fallbacks: if empty, fallback to daily within window; if still empty, last 365 days daily.
    Never returns an empty 'series' unless SmartAPI is unreachable or instrument invalid.
    """
    ins = None
    if symbol:
        ins = instruments.find_by_symbol(symbol)
    elif token:
        ins = instruments.find_by_token(token)
    if not ins:
        raise HTTPException(status_code=404, detail="Instrument not found in CSV")

    if not settings.angel_hist_api_key:
        raise HTTPException(
            status_code=500, detail="ANGEL_HIST_API_KEY missing in .env"
        )

    if frm and to:
        start = parse_iso_ist(frm)
        end = parse_iso_ist(to)
    else:
        start, end = last_n_days_endpoints(30)

    raw = fallback_daily_if_empty("NSE", ins.token, interval, start, end)
    series = normalize_candles(raw)
    return {
        "symbol": ins.symbol,
        "token": ins.token,
        "exchange": "NSE",
        "interval": interval,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "series": series,
    }
