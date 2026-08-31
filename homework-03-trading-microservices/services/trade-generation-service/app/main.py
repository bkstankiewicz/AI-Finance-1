import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import threading
import time
import structlog
from shared.trading_shared.bottle_server import run_server

from config import HOST, PORT
from api import TradeGeneratorApi
from generator import TradeGenerator
from action_client import TradeGeneratorActionClient
from book_client import TradeGeneratorBookClient
from market_data_client import MarketDataClient
from blotter_client import TradeGeneratorBlotterClient

log = structlog.get_logger().bind(service="trade-generation-service")


def generation_loop(generator, action_client):
    while True:
        try:
            trade_data = generator.generate_trade_action()
            if trade_data:
                action_client.push_trade(trade_data)
        except Exception:
            log.exception("error_generating_trade")
        time.sleep(0.5)


if __name__ == '__main__':
    action_client = TradeGeneratorActionClient()
    book_client = TradeGeneratorBookClient()
    blotter_client = TradeGeneratorBlotterClient()
    app = TradeGeneratorApi(action_client)
    market_data_client = MarketDataClient()
    market_data_client.start()
    generator = TradeGenerator(market_data_client, book_client, blotter_client)

    thread = threading.Thread(target=generation_loop, args=(generator, action_client), daemon=True)
    thread.start()

    log.info("service_started", host=HOST, port=PORT)
    run_server(app, host=HOST, port=PORT)
