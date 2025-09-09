"""
Scheduler for automated periodic stock data ingestion using dynamic top gainers from live_fno()
"""

import logging
import os
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from jugaad_nse_client import JugaadNSEClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_top_gainers_from_live_fno(nse_client, top_n=20):
    """
    Get top N gainers by % change from live_fno data.
    """
    data = nse_client.live_fno()
    stocks = data.get("data", [])
    valid_stocks = [
        s for s in stocks if s.get("pChange") is not None and s.get("symbol")
    ]

    sorted_stocks = sorted(valid_stocks, key=lambda x: x["pChange"], reverse=True)
    return [s["symbol"] for s in sorted_stocks[:top_n]]


def graceful_shutdown(signum, frame):
    logger.info("Shutdown signal received, stopping scheduler...")
    scheduler.shutdown(wait=False)
    sys.exit(0)


def scheduled_job():
    logger.info(f"Scheduled job started at {datetime.now()}")

    client = JugaadNSEClient(max_workers=10)
    try:
        symbols = get_top_gainers_from_live_fno(client.jugaad_client, top_n=10)
        logger.info(f"Dynamic top gainers fetched from live_fno: {symbols}")
    except Exception as e:
        logger.warning(f"Error fetching top gainers from live_fno: {e}")
        symbols = [
            "RELIANCE",
            "HDFCBANK",
            "TCS",
            "INFY",
            "ITC",
            "BHARTIARTL",
            "KOTAKBANK",
        ]

    count = client.fetch_and_store_multiple(symbols)
    client.close()

    logger.info(
        f"Scheduled job finished: fetched and stored {count}/{len(symbols)} symbols"
    )


if __name__ == "__main__":
    load_dotenv()

    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    scheduler.add_job(
        scheduled_job,
        trigger=IntervalTrigger(seconds=int(os.getenv("DATA_FETCH_INTERVAL", "5"))),
        id="stock_data_ingestion",
        max_instances=1,
        replace_existing=True,
        name="Periodic stock data ingestion",
    )

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    logger.info("Starting scheduler. Press Ctrl+C to exit.")

    scheduled_job()

    scheduler.start()
