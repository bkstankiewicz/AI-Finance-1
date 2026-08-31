import json
import random
import urllib.request
import structlog
from config import GET_ACTIVE_TRADES_URL

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class TradeGeneratorBlotterClient:
    def __init__(self):
        self.trade_cache = []
        self.log = structlog.get_logger().bind(service="trade-generation-service")

    def get_active_trades(self):
        """Fetch the list of last 20 active trades from the blotter-service"""
        try:
            request = urllib.request.Request(GET_ACTIVE_TRADES_URL)
            with opener.open(request, timeout=5) as response:
                body = response.read()
                data = json.loads(body.decode())
                trades = data.get("trades", [])
                self.trade_cache = trades
                return trades
        except Exception:
            self.log.exception("error_fetching_active_trades")
            return self.trade_cache

    def get_random_active_trade(self):
        """Pick a random ACTIVE trade to close, or None if there are none"""
        trades = self.get_active_trades()
        if not trades:
            self.log.warning("no_active_trades_found")
            return None
        return random.choice(trades)

