import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Mongo
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "stock_simulator")

    # Angel One SmartAPI
    ANGEL_API_KEY: Optional[str] = os.getenv("ANGEL_API_KEY")
    ANGEL_CLIENT_ID: Optional[str] = os.getenv("ANGEL_CLIENT_ID")
    ANGEL_PIN: Optional[str] = os.getenv("ANGEL_PIN")
    ANGEL_TOTP_SECRET: Optional[str] = os.getenv("ANGEL_TOTP_SECRET")

    # Ingestion
    INGEST_INTERVAL_SEC: int = int(os.getenv("INGEST_INTERVAL_SEC", "1"))  # 1–5 seconds
    WS_SUB_CHUNK_SIZE: int = int(os.getenv("WS_SUB_CHUNK_SIZE", "100"))

    # Collections
    QUOTES_COLLECTION: str = os.getenv("QUOTES_COLLECTION", "quotes")

    # Safety
    REQUIRE_ALL_ENV: bool = True


def validate_config() -> None:
    missing = []
    for key in ["ANGEL_API_KEY", "ANGEL_CLIENT_ID", "ANGEL_PIN", "ANGEL_TOTP_SECRET"]:
        if not getattr(Config, key):
            missing.append(key)
    if Config.REQUIRE_ALL_ENV and missing:
        raise RuntimeError(f"Missing required .env keys: {', '.join(missing)}")
