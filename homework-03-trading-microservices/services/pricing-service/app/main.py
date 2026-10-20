import sys
import threading
import structlog
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.bottle_server import run_server
from shared.trading_shared.logging_config import configure_logging
from shared.trading_shared.audit import log_audit_error, AuditEventType

from api import PricingServiceApi
from valuation_publisher import ValuationPublisher
from market_data_client import MarketDataClient
from persistence import Persistence
from valuation_engine import ValuationEngine
from pnl import PnLService
from config import HOST, PORT, VALUATION_INTERVAL, SERVICE_NAME

log = structlog.get_logger()


ASSET_CLASSES = ["EQUITY", "BOND", "FX", "COMMODITY", "FUTURES", "EUROPEAN_OPTION", "IRS"]

DB_PUSH_INTERVAL = 10

# Docker kills the container 10 s after SIGTERM; joins must finish well before that
JOIN_TIMEOUT = 3


def pricing_service_active_trades(pnl_service, persistence, publisher, executor, stop):
    while not stop.is_set():
        tasks = [
            executor.submit(pnl_service.calculate_equity),
            executor.submit(pnl_service.calculate_fixed_income),
            executor.submit(pnl_service.calculate_forex),
            executor.submit(pnl_service.calculate_commodity),
            executor.submit(pnl_service.calculate_futures),
            executor.submit(pnl_service.calculate_eu_option),
            executor.submit(pnl_service.calculate_irs),
        ]
        for task in tasks:
            try:
                for valuation in task.result():
                    persistence.add_valuation(valuation)
                    publisher.publish_data(valuation)
            except Exception:
                log.exception("Error processing active trades")
        stop.wait(VALUATION_INTERVAL)


def pricing_service_close_trades(pnl_service, persistence, publisher, executor, stop):
    while not stop.is_set():
        tasks = [executor.submit(pnl_service.calculate_closed_positions, asset_class) for asset_class in ASSET_CLASSES]
        for task in tasks:
            try:
                # Already stored together with is_settled - only publish
                for valuation in task.result():
                    publisher.publish_data(valuation)
            except Exception:
                log.exception("Error processing closed trades")
        stop.wait(VALUATION_INTERVAL)


def push_valuations(persistence):
    try:
        persistence.push_valuations()
    except Exception:
        log_audit_error(log, AuditEventType.DB_PUSH_ERROR, "Error pushing valuations to DB", exc_info=True)


def push_to_db(persistence, stop):
    while not stop.wait(DB_PUSH_INTERVAL):
        push_valuations(persistence)
    push_valuations(persistence)  # final flush on shutdown


if __name__ == '__main__':
    configure_logging(SERVICE_NAME)
    stop = threading.Event()
    publisher = ValuationPublisher()
    persistence = Persistence()
    market_data_client = MarketDataClient()
    valuation_engine = ValuationEngine(persistence, market_data_client)
    pnl_service = PnLService(valuation_engine)
    app = PricingServiceApi(publisher, valuation_engine)

    market_data_client.start()

    executor = ThreadPoolExecutor(max_workers=7)
    threads = [
        threading.Thread(target=pricing_service_active_trades, args=(pnl_service, persistence, publisher, executor, stop), name="valuation-active", daemon=True),
        threading.Thread(target=pricing_service_close_trades, args=(pnl_service, persistence, publisher, executor, stop), name="valuation-closed", daemon=True),
        threading.Thread(target=push_to_db, args=(persistence, stop), name="db-push", daemon=True),
    ]
    for thread in threads:
        thread.start()

    log.info("service_started", host=HOST, port=PORT)
    try:
        run_server(app, host=HOST, port=PORT)
    finally:
        log.info("service_stopping")
        stop.set()
        for thread in threads:
            thread.join(timeout=JOIN_TIMEOUT)
        executor.shutdown(wait=False, cancel_futures=True)
        log.info("service_stopped")