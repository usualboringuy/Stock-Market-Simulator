import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=False)


@dataclass(frozen=True)
class Settings:
    # Mongo (for Module 2 onward)
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
    database_name: str = os.getenv("DATABASE_NAME", "stock_simulator")

    # SmartAPI
    angel_market_api_key: str = os.getenv("ANGEL_MARKET_API_KEY", "")
    angel_hist_api_key: str = os.getenv("ANGEL_HIST_API_KEY", "")
    angel_client_id: str = os.getenv("ANGEL_CLIENT_ID", "")
    angel_pin: str = os.getenv("ANGEL_PIN", "")
    angel_totp_secret: str = os.getenv("ANGEL_TOTP_SECRET", "")

    # Files
    stocks_csv: str = os.getenv("STOCKS_CSV", "data/stocks.csv")

    # Optional live polling interval
    live_poll_ms: int = int(os.getenv("LIVE_POLL_MS", "3000"))


settings = Settings()
