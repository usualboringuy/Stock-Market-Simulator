import os
import signal
import sys
from src.config import validate_config
from src.logger import get_logger
from src.utils.csv_loader import load_stocks_csv
from src.db.mongo import init_mongo
from src.ingestion.scheduler import IngestionScheduler

logger = get_logger("main")


def main() -> None:
    validate_config()
    init_mongo()

    csv_path = os.path.join("data", "stocks.csv")
    stocks = load_stocks_csv(csv_path)
    if not stocks:
        logger.error("No valid NSE equity stocks found in %s", csv_path)
        sys.exit(1)

    scheduler = IngestionScheduler(stocks)

    def handle_signal(sig, frame):
        logger.info("Signal received, shutting down...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Loaded %d stocks from %s", len(stocks), csv_path)
    logger.info("Ingestion interval (sec): %s", os.getenv("INGEST_INTERVAL_SEC", "1"))

    scheduler.start()


if __name__ == "__main__":
    main()
