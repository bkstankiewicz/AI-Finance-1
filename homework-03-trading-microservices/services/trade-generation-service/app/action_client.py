import json
import urllib.request
import structlog
import threading
from config import TRADE_ACTION_URL, GENERATION_INTERVAL, TRADE_OUT_PROBABILITY

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)


def _to_number(name, value):
    # bool is a subclass of int - reject it explicitly
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None


def _parse_frequency(value):
    number = _to_number("frequency", value)
    if number <= 0:
        raise ValueError("frequency must be greater than 0")
    return number


def _parse_trade_out_probability(value):
    number = _to_number("trade_out_probability", value)
    if not 0 <= number <= 100:
        raise ValueError("trade_out_probability must be between 0 and 100")
    return number


def _parse_max_active_trades(value):
    number = _to_number("max_active_trades", value)
    if not number.is_integer() or number < 1:
        raise ValueError("max_active_trades must be an integer >= 1")
    return int(number)


CONFIG_PARSERS = {
    "frequency": _parse_frequency,
    "trade_out_probability": _parse_trade_out_probability,
    "max_active_trades": _parse_max_active_trades,
}


class TradeGeneratorActionClient:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.count = 0
        self.configs = {
            "frequency": GENERATION_INTERVAL,
            "trade_out_probability": TRADE_OUT_PROBABILITY,
            "max_active_trades": None,
        }
        self.log = structlog.get_logger()

    def push_trade(self, trade_data):
        """Push a trade to the trade-action-service, unless generation is stopped"""
        if not self.push():
            return
        try:
            request = urllib.request.Request(
                url=TRADE_ACTION_URL,
                data=json.dumps(trade_data).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status == 202:
                    self.log.info("trade_pushed", client_request_id=trade_data.get("client_request_id"))
                else:
                    self.log.error("failed_to_push_trade", client_request_id=trade_data.get("client_request_id"), status=response.status)
        except Exception:
            self.log.exception("error_pushing_trade")


    def push_trade_batch(self):
        """Push a batch of trades to the trade-action-service"""
        pass 

    def start(self):
        """Start generating trades continuously"""
        with self.lock:
            self.running = True

    def stop(self):
        """Stop generating trades continuously"""
        with self.lock:
            self.running = False

    def is_running(self):
        with self.lock:
            return self.running

    def generate_once(self):
        """Allow exactly one more trade to be pushed, regardless of running state"""
        with self.lock:
            self.count += 1

    def push(self):
        """Consume a pending one-shot request if present, otherwise reflect running state"""
        with self.lock:
            if self.count > 0:
                self.count -= 1
                return True
            return self.running

    def get_configs(self):
        with self.lock:
            return dict(self.configs)

    def update_configs(self, config_data):
        """Partially update configs; missing / null / empty values keep the current setting.
        Raises ValueError on invalid input, nothing is applied in that case."""
        changes = {
            name: parse(config_data[name])
            for name, parse in CONFIG_PARSERS.items()
            if config_data.get(name) not in (None, "")
        }
        with self.lock:
            self.configs.update(changes)
            configs = dict(self.configs)
        self.log.info("configs_updated", changes=changes, configs=configs)
        return configs