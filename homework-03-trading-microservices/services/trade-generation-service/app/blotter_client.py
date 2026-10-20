import json
import random
import urllib.request
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import structlog
from config import GET_ACTIVE_TRADES_URL

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _active_trades_url(limit):
    if limit is None:
        return GET_ACTIVE_TRADES_URL
    parts = urlsplit(GET_ACTIVE_TRADES_URL)
    query = dict(parse_qsl(parts.query))
    query["limit"] = str(limit)
    return urlunsplit(parts._replace(query=urlencode(query)))


class TradeGeneratorBlotterClient:
    def __init__(self):
        self.trade_cache = []
        self.log = structlog.get_logger()

    def get_active_trades(self, limit=None):
        """Fetch the latest active trades from the blotter-service (limit from GET_ACTIVE_TRADES_URL unless overridden)"""
        try:
            request = urllib.request.Request(_active_trades_url(limit))
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

