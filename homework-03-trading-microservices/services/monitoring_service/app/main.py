import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from concurrent.futures import ThreadPoolExecutor
from shared.trading_shared.bottle_server import run_server
from shared.trading_shared.logging_config import configure_logging
from config import HOST, PORT, SERVICE_URLS, MONITORING_INTERVAL, SERVICE_NAME, JOIN_TIMEOUT
from monitor import Monitor
from publisher import MonitorPublisher
from api import MonitoringServiceApi
import threading
import structlog

log = structlog.get_logger()


def monitoring_service(monitor, publisher, stop):
    service_names = list(SERVICE_URLS.keys())
    service_urls = list(SERVICE_URLS.values())

    with ThreadPoolExecutor(max_workers=len(SERVICE_URLS)) as executor:
        while not stop.is_set():
            try:
                results = list(executor.map(monitor.check_service, service_names, service_urls))
                publisher.publish_data(dict(zip(service_names, results)))
            except Exception:
                log.exception("error_monitoring_services")
            stop.wait(MONITORING_INTERVAL)


if __name__ == '__main__':
    configure_logging(SERVICE_NAME)
    stop = threading.Event()
    monitor = Monitor()
    publisher = MonitorPublisher()
    app = MonitoringServiceApi(monitor, publisher)

    threads = [
        threading.Thread(target=monitoring_service, args=(monitor, publisher, stop), name="health-checks", daemon=True),
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
        log.info("service_stopped")