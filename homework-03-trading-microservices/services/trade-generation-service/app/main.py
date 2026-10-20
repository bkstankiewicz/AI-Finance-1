import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import threading
import structlog
from shared.trading_shared.bottle_server import run_server
from shared.trading_shared.logging_config import configure_logging

from config import HOST, PORT, SERVICE_NAME
from api import TradeGeneratorApi
from generator import (
    TradeActionGenerator,
    EquityTradeGenerator,
    FixedIncomeTradeGenerator,
    ForexTradeGenerator,
    CommodityTradeGenerator,
    FuturesTradeGenerator,
    EUOptionTradeGenerator,
    IRSTradeGenerator,
)
from action_client import TradeGeneratorActionClient
from book_client import TradeGeneratorBookClient
from market_data_client import MarketDataClient
from blotter_client import TradeGeneratorBlotterClient

log = structlog.get_logger()

# Docker kills the container 10 s after SIGTERM; joins must finish well before that
JOIN_TIMEOUT = 3


def generation_loop(generator, action_client, stop):
    while not stop.is_set():
        configs = action_client.get_configs()
        try:
            trade_data = generator.generate_trade_action(
                close_probability=configs["trade_out_probability"] / 100,
                max_active_trades=configs["max_active_trades"],
            )
            if trade_data:
                action_client.push_trade(trade_data)
        except Exception:
            log.exception("error_generating_trade")
        stop.wait(configs["frequency"])


if __name__ == '__main__':
    configure_logging(SERVICE_NAME)
    stop = threading.Event()
    action_client = TradeGeneratorActionClient()
    book_client = TradeGeneratorBookClient()
    blotter_client = TradeGeneratorBlotterClient()
    app = TradeGeneratorApi(action_client)
    market_data_client = MarketDataClient()
    market_data_client.start()
    trade_generators = [
        generator_cls(market_data_client, book_client)
        for generator_cls in (
            EquityTradeGenerator,
            FixedIncomeTradeGenerator,
            ForexTradeGenerator,
            CommodityTradeGenerator,
            FuturesTradeGenerator,
            EUOptionTradeGenerator,
            IRSTradeGenerator,
        )
    ]
    generator = TradeActionGenerator(trade_generators, market_data_client, blotter_client)

    threads = [
        threading.Thread(target=generation_loop, args=(generator, action_client, stop), name="trade-generation", daemon=True),
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
