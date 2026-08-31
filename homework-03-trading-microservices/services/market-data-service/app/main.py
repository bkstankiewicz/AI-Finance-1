import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.bottle_server import run_server

from api import MarketDataApi
from config import HOST, PORT, TICK_INTERVAL, SERVICE_NAME
from generator import Generator
from publisher import Publisher
from persistence import Persistence

from concurrent.futures import ThreadPoolExecutor

import time
import threading
import traceback
import structlog

log = structlog.get_logger().bind(service=SERVICE_NAME)


def market_data_service(generator, executor, publisher, persistence, latest_data: dict):
    while True:
        tasks = [
            executor.submit(generator.generate_equity_data),
            executor.submit(generator.generate_fixed_income_data),
            executor.submit(generator.generate_forex_data),
            executor.submit(generator.generate_commodity_data),
            executor.submit(generator.generate_futures_data)
        ]

        for task in tasks:
            try:
                data = task.result()
                publisher.publish_data(data)
                latest_data[data["symbol"]] = data
                persistence.add_ticks(data)
                persistence.add_snapshot(data)
            except Exception:
                log.exception("error_generating_market_data")

        time.sleep(TICK_INTERVAL)

def push_data_to_db(persistence):
    while True:
        try:
            persistence.push_ticks()
            persistence.push_snapshots()
            persistence.push_curves()
        except Exception:
            log.exception("error_pushing_data_to_db")
        time.sleep(10)


if __name__ == '__main__':
    latest_data = {}

    executor = ThreadPoolExecutor(max_workers=5)
    publisher = Publisher()
    persistence = Persistence()
    last_event_id = persistence.get_last_event_id()
    generator = Generator(last_event_id)
    app = MarketDataApi(publisher, latest_data)

    thread_market_ticks = threading.Thread(target=market_data_service, args=(generator, executor, publisher, persistence, latest_data), daemon=True)
    thread_market_ticks.start()

    thread_snapshot = threading.Thread(target=push_data_to_db, args=(persistence,), daemon=True)
    thread_snapshot.start()

    log.info("service_started", host=HOST, port=PORT)
    run_server(app, host=HOST, port=PORT)
