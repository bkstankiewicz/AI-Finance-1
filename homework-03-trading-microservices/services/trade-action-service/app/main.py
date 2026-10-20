import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import threading
import structlog
from shared.trading_shared.bottle_server import run_server
from shared.trading_shared.logging_config import configure_logging
from config import HOST, PORT, SERVICE_NAME
from api import TradeActionApi
from action_queue import TradeActionQueue
from processor import TradeActionProcessor
from repository import TradeActionRepository
from validation import TradeActionValidation
from stats import ProcessingStats

log = structlog.get_logger()

# Docker kills the container 10 s after SIGTERM; joins must finish well before that
JOIN_TIMEOUT = 3


def worker_loop(processor: TradeActionProcessor, stop: threading.Event):
    while not stop.is_set():
        processor.get_next_trade()


if __name__ == '__main__':
    configure_logging(SERVICE_NAME)
    stop = threading.Event()
    trade_queue = TradeActionQueue()
    repository = TradeActionRepository()
    validation = TradeActionValidation()
    stats = ProcessingStats()
    processor = TradeActionProcessor(validation, trade_queue, repository, stats)

    app = TradeActionApi(trade_queue, stats)

    threads = [
        threading.Thread(target=worker_loop, args=(processor, stop), name="trade-action-worker", daemon=True),
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
        log.info("service_stopped", unprocessed_actions=trade_queue.get_size())