import json
import urllib.request
import threading
import time
import structlog
from config import STREAM_URL, RECONNECTING_INTERVAL

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)


class MarketDataClient:
    def __init__(self):
        self.lock = threading.Lock()
        self.connection_status = "DISCONNECTED"
        self.received_event_id = 0
        self.cache = {}
        self.log = structlog.get_logger().bind(service="trade-generation-service")

    def start(self):
        """Start streaming thread"""
        threading.Thread(target=self.connect_to_market_data_stream, daemon=True).start()

    def connect_to_market_data_stream(self):
        """Connect to the market data stream and read events"""
        while True:
            try:
                request = urllib.request.Request(STREAM_URL, headers={'Accept': 'text/event-stream'})
                with urllib.request.urlopen(request, timeout=None) as response:
                    with self.lock:
                        self.connection_status = "CONNECTED"
                    self.log.info("connected_to_market_data_stream", status=self.connection_status)
                    self.read_events(response)
            except Exception as e:
                self.log.warning("error_connecting_to_market_data_stream", error=str(e))
                with self.lock:
                    self.connection_status = "DISCONNECTED"
            time.sleep(RECONNECTING_INTERVAL)

    def read_events(self, received_data):
        """Reading events from market data stream and updating cache"""
        for line in received_data:
            line = line.decode('utf-8').strip()
            if not line.startswith('data: '):
                continue
            data = json.loads(line[6:])
            symbol = data.get("symbol")
            if not symbol:
                continue
            with self.lock:
                self.cache[symbol] = data

    def get_price(self, asset_description):
        """Get latest price for asset_description = (asset_class, symbol)"""
        _, symbol = asset_description
        with self.lock:
            return self.cache.get(symbol)
