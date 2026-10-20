import sys
import structlog
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.bottle_server import run_server
from shared.trading_shared.logging_config import configure_logging

from config import HOST, PORT, SERVICE_NAME
from api import BlotterServiceApi
from live_cache import LiveCache
from valuation_stream_client import PricingServiceClient
from repository import BlotterRepository

log = structlog.get_logger()


if __name__ == '__main__':
    configure_logging(SERVICE_NAME)
    cache = LiveCache()
    client = PricingServiceClient(cache)
    client.start()
    repository = BlotterRepository(cache)
    app = BlotterServiceApi(repository)

    log.info("service_started", host=HOST, port=PORT)
    try:
        run_server(app, host=HOST, port=PORT)
    finally:
        log.info("service_stopped")