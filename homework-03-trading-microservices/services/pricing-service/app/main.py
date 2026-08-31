import sys
import threading
import time
import structlog
from concurrent.futures import ThreadPoolExecutor, thread
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.bottle_server import run_server

from api import PricingServiceApi
from valuation_publisher import ValuationPublisher
from market_data_client import MarketDataClient
from persistence import Persistence
from valuation_engine import ValuationEngine
from pnl import PnLService
from config import HOST, PORT, VALUATION_INTERVAL, SERVICE_NAME

log = structlog.get_logger().bind(service=SERVICE_NAME)


ASSET_CLASSES = ["EQUITY", "BOND", "FX", "COMMODITY", "FUTURES"]


def pricing_service_active_trades(pnl_service, persistence, publisher, executor):
    while True:
        tasks = [
            executor.submit(pnl_service.calculate_equity),
            executor.submit(pnl_service.calculate_fixed_income),
            executor.submit(pnl_service.calculate_forex),
            executor.submit(pnl_service.calculate_commodity),
            executor.submit(pnl_service.calculate_futures),
        ]
        for task in tasks:
            try:
                for valuation in task.result():
                    persistence.add_valuation(valuation)
                    publisher.publish_data(valuation)
            except Exception:
                log.exception("Error processing active trades")
        time.sleep(VALUATION_INTERVAL)

def pricing_service_close_trades(pnl_service, persistence, publisher, executor):
    while True:
        tasks = [executor.submit(pnl_service.calculate_closed_positions, asset_class) for asset_class in ASSET_CLASSES]
        for task in tasks:
            try:
                for valuation in task.result():
                    persistence.add_valuation(valuation)
                    publisher.publish_data(valuation)
            except Exception:
                log.exception("Error processing closed trades")
        time.sleep(VALUATION_INTERVAL)

def push_to_db(persistence):
    while True:
        try:
            persistence.push_valuations()
        except Exception:
            log.exception("Error pushing valuations to DB")
        time.sleep(10)


if __name__ == '__main__':
    publisher = ValuationPublisher()
    persistence = Persistence()
    market_data_client = MarketDataClient()
    valuation_engine = ValuationEngine(persistence, market_data_client)
    pnl_service = PnLService(valuation_engine)
    app = PricingServiceApi(publisher, valuation_engine)

    market_data_client.start()

    executor = ThreadPoolExecutor(max_workers=5)
    thread_active = threading.Thread(target=pricing_service_active_trades, args=(pnl_service, persistence, publisher, executor), daemon=True)
    thread_active.start()

    thread_close = threading.Thread(target=pricing_service_close_trades, args=(pnl_service, persistence, publisher, executor), daemon=True)
    thread_close.start()

    thread_push = threading.Thread(target=push_to_db, args=(persistence,), daemon=True)
    thread_push.start()

    log.info("service_started", host=HOST, port=PORT)
    run_server(app, host=HOST, port=PORT)