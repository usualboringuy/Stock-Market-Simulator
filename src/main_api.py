# src/main_api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.instruments import router as instruments_router
from src.api.portfolio import router as portfolio_router
from src.api.quotes import router as quotes_router
from src.api.trades import router as trades_router
from src.config import Config
from src.db.mongo import ensure_indexes, init_mongo

app = FastAPI(title="Stock Simulator API", version="0.1.0")

# CORS
origins = (
    [o.strip() for o in Config.CORS_ALLOW_ORIGINS.split(",")]
    if Config.CORS_ALLOW_ORIGINS
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_mongo()
    ensure_indexes()


@app.get("/health")
def health():
    return {"status": "ok"}


# Routers
app.include_router(auth_router)
app.include_router(quotes_router)
app.include_router(portfolio_router)
app.include_router(trades_router)
app.include_router(instruments_router)
