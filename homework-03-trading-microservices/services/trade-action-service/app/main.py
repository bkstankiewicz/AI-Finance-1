import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import threading
from shared.trading_shared.bottle_server import run_server
import structlog
from config import HOST, PORT, SERVICE_NAME
from api import TradeActionApi
from action_queue import TradeActionQueue
from processor import TradeActionProcessor
from repository import TradeActionRepository
from validation import TradeActionValidation

log = structlog.get_logger().bind(service=SERVICE_NAME)


def worker_loop(processor: TradeActionProcessor):
    while True:
        processor.get_next_trade()


if __name__ == '__main__':
    trade_queue = TradeActionQueue()
    repository = TradeActionRepository()
    validation = TradeActionValidation()
    processor = TradeActionProcessor(validation, trade_queue, repository)

    app = TradeActionApi(trade_queue)

    thread_worker = threading.Thread(target=worker_loop, args=(processor,), daemon=True)
    thread_worker.start()

    log.info("service_started", host=HOST, port=PORT)
    run_server(app, host=HOST, port=PORT)