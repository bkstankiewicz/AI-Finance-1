import sys
import structlog
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.bottle_server import run_server

from config import HOST, PORT, SERVICE_NAME
from api import BlotterServiceApi
from live_cache import LiveCache
from valuation_stream_client import PricingServiceClient
from repository import BlotterRepository

log = structlog.get_logger().bind(service=SERVICE_NAME)


if __name__ == '__main__':
    cache = LiveCache()
    client = PricingServiceClient(cache)
    client.start()
    repository = BlotterRepository(cache)
    app = BlotterServiceApi(repository)


    log.info("service_started", host=HOST, port=PORT)
    run_server(app, host=HOST, port=PORT)