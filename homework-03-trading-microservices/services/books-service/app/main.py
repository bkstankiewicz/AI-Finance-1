import sys
import structlog
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.bottle_server import run_server

from config import HOST, PORT, SERVICE_NAME
from api import BooksServiceApi
from service import BooksService
from repository import BooksRepository

log = structlog.get_logger().bind(service=SERVICE_NAME)


if __name__ == '__main__':
    repository = BooksRepository()
    service = BooksService(repository)
    app = BooksServiceApi(service)

    service.seed_default_books()

    log.info("service_started", host=HOST, port=PORT)
    run_server(app, host=HOST, port=PORT)