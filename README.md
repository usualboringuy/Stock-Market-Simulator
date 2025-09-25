# Stock Market Simulator

A full‑stack stock market simulator for NSE equities. It fetches charts on demand from Angel One SmartAPI (smartapi-python 1.5.5), stores users/sessions/portfolios/trades in MongoDB, and renders an SPA frontend (Vite + React + Chart.js). It does simulated BUY/SELL with proper average price and realized P&L, live polling during market hours, and never-blank charts (intraday→daily fallbacks).

Screenshots: see /docs/screenshots (or the images you shared).

---

## Table of contents

- Features
- Tech stack
- Project structure
- Quick start
- Configuration (.env)
- Data model and calculations
- API (selected endpoints)
- Frontend behavior
- SmartAPI notes
- Troubleshooting
- Roadmap
- License

---

## Features

Backend
- Angel One SmartAPI integration (historical candles via Historical App key; login throttling; TOTP)
- Candle fetching with:
  - Chunking by interval (1‑minute: 1 day per request; 1‑hour: 7 days; daily: wider)
  - Retries with backoff
  - Intraday→daily fallback (and last‑365‑day daily backup) so charts never render blank
- Instruments resolved only from your local CSV (no remote instrument master)
- MongoDB repositories (users, sessions, portfolios, trades) with indexes and TTL
- Simulated trading:
  - BUY updates avg price and cash
  - SELL realizes P&L, reduces/clears position, updates cash
  - Optimistic concurrency on portfolios
- Cookie sessions with CSRF (double‑submit cookie)
- Batch price endpoint for live portfolio updates and sparklines

Frontend
- React + Vite + Chart.js v4 + chartjs‑chart‑financial 0.2.1
- Dashboard (curated symbols): LIVE, 1D, 1W, 1M, 6M, 1Y
- Stock detail: full chart + trade form
- Portfolio:
  - Holdings‑only summary: holdings value, 1D returns, total returns, invested (excludes cash)
  - Click positions to open detail
  - Add Funds (deposit) with CSRF
  - Live auto‑refresh: holdings values, 1D/total returns, sparklines
- Charts:
  - Candlestick/line toggle
  - Adaptive line color across all ranges based on the range’s open:
    - Green if current (rightmost close) >= the range’s open (first bar’s open)
    - Red otherwise
  - LIVE marker (colored dot at the latest point)
  - Never blank: intraday/daily fallbacks
- Live polling (10s) during market hours (gated by /api/health), “Auto” follow mode:
  - When market opens: stays on your chosen range (doesn’t force LIVE)
  - When market closes: if you are on LIVE, it switches to 1D (or your chosen fallback)

---

## Tech stack

- Backend: Python 3.10+, FastAPI, Pydantic v2, MongoDB (pymongo), logzero, pyotp
- SmartAPI: smartapi-python 1.5.5 (Angel One)
- Frontend: Vite (React), Chart.js v4, chartjs‑chart‑financial 0.2.1, axios
- Time zone: IST (Asia/Kolkata); market hours 09:00–15:30 Mon–Fri

---

## Project structure

```
.
├── app/
│   ├── main.py                # FastAPI app
│   ├── config.py              # Settings from .env
│   ├── logger.py
│   ├── timeutils.py           # IST helpers, parsers, clamps
│   ├── cache.py               # Simple TTL cache (optional use)
│   ├── instruments.py         # CSV loader + search (symbol/token/name)
│   ├── smartapi_client.py     # SmartAPI sessions (historical + trading)
│   ├── candles.py             # Chunked fetch + fallbacks + normalize
│   ├── db.py                  # Mongo client + indexes
│   ├── security.py            # PBKDF2 hashing + verify
│   ├── trading.py             # Simulated BUY/SELL
│   ├── auth.py, deps.py       # Cookies, CSRF, dependencies
│   ├── schemas.py             # Pydantic models
│   ├── routes/
│   │   ├── auth.py            # /api/auth/*
│   │   ├── portfolio.py       # /api/portfolio, /api/portfolio/deposit
│   │   ├── trades.py          # /api/trades, /api/trades/recent
│   │   └── prices.py          # /api/prices/live (batch latest + sparkline)
│   └── repositories/          # users, sessions, portfolios, trades
│       ├──portfolios.py
│       ├──users.py
│       ├──sessions.py
│       └──trades.py
├── scripts/
│   ├── smoke_module1.py       # API smoke
│   ├── smoke_module2.py       # DB & trade smoke
│   └── smoke_module3.py       # Full auth/portfolio/trade smoke
├── data/
│   └── stocks.csv             # symbol,token,name (source of truth)
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx, App.jsx, styles.css
│       ├── api/client.js
│       ├── context/AuthContext.jsx
│       ├── utils/cookies.js
│       ├── components/
│       │   ├── Navbar.jsx, RangeToggle.jsx
│       │   ├── ChartOHLC.jsx       # Chart with line/candle, marker, color logic
│       │   └── Sparkline.jsx       # Tiny sparkline next to holdings
│       └── pages/
│           ├── Dashboard.jsx
│           ├── Stock.jsx
│           ├── Auth.jsx
│           └── Portfolio.jsx
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick start

Prereqs
- Python 3.10+
- Node 18+
- MongoDB running locally (mongodb://localhost:27017)
- Angel One SmartAPI keys (two apps recommended: Historical / Market)

1) Backend

```bash
cp .env.example .env
# fill in ANGEL_* keys and STOCKS_CSV, etc.

python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# start API
uvicorn app.main:app --reload
```

2) Frontend

```bash
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

3) Smoke tests

```bash
# minimal API health/instruments/candles
python -m scripts.smoke_module1

# DB + virtual trades + persists
python -m scripts.smoke_module2

# Full API: signup/login/portfolio/trades (needs backend running)
python -m scripts.smoke_module3
```

---

## Configuration (.env)

See .env.example; important keys:

Mongo
- MONGODB_URL=mongodb://localhost:27017/
- DATABASE_NAME=stock_simulator

SmartAPI (Angel One)
- ANGEL_HIST_API_KEY=...      # Historical app key (used for getCandleData)
- ANGEL_MARKET_API_KEY=...    # Optional market app key (for LTP; not mandatory here)
- ANGEL_CLIENT_ID=...
- ANGEL_PIN=...
- ANGEL_TOTP_SECRET=...       # pyotp TOTP secret

Files
- STOCKS_CSV=data/stocks.csv  # Columns: symbol,token,name

Auth / Cookies / CSRF
- SESSION_COOKIE_NAME=app_session
- CSRF_COOKIE_NAME=app_csrf
- SESSION_TTL_SECONDS=604800
- SESSION_SLIDING=true
- COOKIE_SECURE=false         # set true behind HTTPS in production
- COOKIE_SAMESITE=lax         # set none + secure=true for cross-site
- COOKIE_DOMAIN=
- CORS_ORIGINS=http://localhost:5173
- CSRF_ENABLED=true

Optional
- LIVE_POLL_MS=3000

Frontend note
- Chart.js v4 + chartjs-chart-financial 0.2.1 are used; if your registry only exposes 0.2.1, keep the versions as provided.

---

## Data model and calculations

Portfolio (Mongo)
- cash: float
- realized_pl: float
- positions: { token: { symbol, quantity, avg_price } }
- rev: int (optimistic concurrency)
- created_at, updated_at

Trades
- user_id, token, symbol, side (BUY/SELL), quantity, price, amount
- realized_pl (only on SELL)
- executed_at

Trading logic
- BUY:
  - avg_price’ = (qty_old × avg_old + qty_buy × fill_price) / (qty_old + qty_buy)
  - cash -= qty_buy × price
- SELL:
  - realized += (sell_price − avg_price) × qty_sell
  - qty reduces; if reaches 0, remove the position
  - cash += qty_sell × price
- Fill price: last candle close (ONE_MINUTE if market open; otherwise ONE_DAY with fallbacks)

Holdings metrics (Portfolio page; holdings-only = excludes cash)
- Holdings value = Σ qty × latest_price
- 1D returns = Σ qty × (today_last_close − prev_close)
- Total returns = Σ (qty × latest_price − qty × avg_price)
- Invested = Σ qty × avg_price
- Realized P&L = Σ realized_on_sell across past SELLs (independent of above)
- Overall (optional): Realized P&L + Total returns (not shown by default)

Sparklines (Portfolio list)
- Live: minute closes for ~15 min in a single batch; fallback to last 30–40 daily closes after hours
- Color baseline = latest daily open (today/last session):
  - green if last >= baseline, red if last < baseline
- Tiny trend only: not P/L/percent; no axes

Chart coloring (Stock detail & Dashboard cards)
- Line color across ALL ranges compares current (rightmost close of the displayed series) vs the range’s open (first bar’s open):
  - green if current ≥ range_open
  - red otherwise
- LIVE marker: dot at latest point, matches line color

---

## APIs

Public
- GET /api/health
  - { ok, time_ist, market_open, historical_api_key_present, trading_api_key_present, stocks_csv, csrf_enabled }

Instruments
- GET /api/instruments/search?q=RELIANCE&limit=20
  - Uses local CSV only (symbol, token, name)

Candles
- GET /api/candles?symbol=INFY-EQ&interval=ONE_DAY&from=...&to=...
  - interval: ONE_MINUTE | FIVE_MINUTE | TEN_MINUTE | FIFTEEN_MINUTE | THIRTY_MINUTE | ONE_HOUR | ONE_DAY
  - Returns { series: [{ t, o, h, l, c, v? }], ... }
  - Fallbacks: intraday→daily if too old/empty; last 365 daily backup

Auth (cookie sessions + CSRF)
- POST /api/auth/signup { username, password }
- POST /api/auth/login { username, password }
- POST /api/auth/logout
- GET  /api/auth/me

Portfolio
- GET  /api/portfolio
- POST /api/portfolio/deposit { amount }  [CSRF required]

Trades
- POST /api/trades { symbol or token, side: BUY|SELL, quantity }  [CSRF]
- GET  /api/trades/recent?limit=20

Batch prices (portfolio live)
- POST /api/prices/live
  - Body: { tokens: [string], minutes: 15, include_series: true, series_points: 40 }
  - Returns { prices: { token: { last, series: [{t,c}] } }, market_open, server_time }

CSRF
- Double-submit cookie: cookie app_csrf and header X‑CSRF‑Token must match
- Cookies: HttpOnly session cookie, non-HttpOnly CSRF cookie

---

## Frontend behavior

Dashboard
- Range buttons: LIVE / 1D / 1W / 1M / 6M / 1Y
- Auto toggle:
  - If Auto is ON:
    - When market opens: keeps your chosen range
    - When market closes: if you were on LIVE, switches to 1D
- LIVE polling: every 10s only when market_open = true (from /api/health)
- Silent refresh (no spinner) to avoid remount flicker

Stock detail
- Same range buttons + trade form (BUY/SELL)
- Chart line color: green/red vs range open
- LIVE marker: colored dot on latest point
- Footer: Current, Open, High, Low, Close, Change, Vol, Range

Portfolio
- Add funds (deposit) updates cash (CSRF-protected)
- Holdings summary (value, 1D returns, total returns, invested)
- Holdings rows clickable - go to Stock detail
- Sparklines colored vs latest daily open

---

## SmartAPI notes

- This app uses only documented smartapi-python 1.5.5 methods:
  - generateSession, getfeedToken (optional), getCandleData, terminateSession
- We use the “Historical App” key for candle data (as per Angel’s model).
- Login is TOTP-based (pyotp) with a mutex per session and call throttling.
- We never download the Scrip Master; instruments come from your CSV.

Market hours
- 09:00–15:30 IST, Mon–Fri
- /api/health returns market_open; used to gate LIVE polling

---

## Troubleshooting

- “No data” in charts
  - Check ANGEL_HIST_API_KEY is valid
  - Try 1D/1W/1M: the service falls back to daily if intraday is empty/too old
- 422 on signup/login
  - Username must match /^[a-zA-Z0-9_.-]+$/ and be ≥ 3 chars; password ≥ 6 chars
- Cookies not set in the browser
  - Dev: CORS_ORIGINS must include http://localhost:5173, SameSite=lax is fine if same-host proxy
  - Cross-site: set COOKIE_SAMESITE=none and COOKIE_SECURE=true with HTTPS
- chartjs-chart-financial version
  - We use 0.2.1 with Chart.js v4; explicit registration is in ChartOHLC.jsx
- Mongo naive/aware datetimes
  - If you want tz-aware objects, create the client with tz_aware=True (optional)
