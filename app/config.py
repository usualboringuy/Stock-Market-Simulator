import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=False)


def _bool(env_name: str, default: bool) -> bool:
    val = os.getenv(env_name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
    database_name: str = os.getenv("DATABASE_NAME", "stock_simulator")

    angel_market_api_key: str = os.getenv("ANGEL_MARKET_API_KEY", "")
    angel_hist_api_key: str = os.getenv("ANGEL_HIST_API_KEY", "")
    angel_client_id: str = os.getenv("ANGEL_CLIENT_ID", "")
    angel_pin: str = os.getenv("ANGEL_PIN", "")
    angel_totp_secret: str = os.getenv("ANGEL_TOTP_SECRET", "")

    stocks_csv: str = os.getenv("STOCKS_CSV", "data/stocks.csv")
    live_poll_ms: int = int(os.getenv("LIVE_POLL_MS", "3000"))

    # Auth / Cookies / CORS / CSRF
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "app_session")
    csrf_cookie_name: str = os.getenv("CSRF_COOKIE_NAME", "app_csrf")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "604800"))
    session_sliding: bool = _bool("SESSION_SLIDING", True)

    cookie_secure: bool = _bool("COOKIE_SECURE", False)
    cookie_samesite: str = (
        os.getenv("COOKIE_SAMESITE", "lax").strip().lower()
    )  # lax|strict|none
    cookie_domain: str = os.getenv("COOKIE_DOMAIN", "").strip()

    cors_origins: str = os.getenv("CORS_ORIGINS", "").strip()  # comma-separated
    csrf_enabled: bool = _bool("CSRF_ENABLED", True)


settings = Settings()
