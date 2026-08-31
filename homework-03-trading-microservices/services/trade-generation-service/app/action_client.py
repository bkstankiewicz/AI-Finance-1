import json
import urllib.request
import structlog
import threading
from config import TRADE_ACTION_URL

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)


class TradeGeneratorActionClient:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.count = 0
        self.log = structlog.get_logger().bind(service="trade-generation-service")

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