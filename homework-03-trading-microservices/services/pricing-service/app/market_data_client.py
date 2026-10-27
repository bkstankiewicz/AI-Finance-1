import json
import urllib.request
import threading
import time
import structlog
from config import STREAM_URL, RECONNECTING_INTERVAL
from shared.trading_shared.audit import log_audit_error, AuditEventType

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)

class MarketDataClient:
    def __init__(self):
        self.log = structlog.get_logger()
        self.lock = threading.Lock()
        self.connection_status = "DISCONNECTED"
        self.received_event_id = 0
        self.cache = {}
        self.curves = {}

    def start(self):
        """Start streaming thread"""
        threading.Thread(target=self.connect_to_market_data_stream, daemon=True).start()

    def log_stream_disconnected(self):
        """STREAM_ERROR goes to AuditLogs (via the log file); entity_id/entity_type are always the same here"""
        log_audit_error(self.log, AuditEventType.STREAM_ERROR, "Market data stream disconnected",
                        entity_type="Stream", entity_id=STREAM_URL)

    def connect_to_market_data_stream(self):
        """Connect to the market data stream and read events"""
        while True:
            try:
                request = urllib.request.Request(STREAM_URL, headers={'Accept': 'text/event-stream'})
                with urllib.request.urlopen(request, timeout=None) as response:
                    with self.lock:
                        previous_status = self.connection_status
                        self.connection_status = "CONNECTED"
                    self.log.info("connection_status_to_market_data_stream", status=self.connection_status)
                    if previous_status != "CONNECTED":
                        self.log.info("market_data_stream_connected", entity_type="Stream", entity_id=STREAM_URL)
                    self.read_events(response)
            except Exception:
                self.log.warning("connection_error_to_market_data_stream")
            finally:
                with self.lock:
                    previous_status = self.connection_status
                    self.connection_status = "DISCONNECTED"
                if previous_status != "DISCONNECTED":
                    self.log_stream_disconnected()
            time.sleep(RECONNECTING_INTERVAL)

    def read_events(self, received_data):
        """Reading events from market data stream and updating cache"""
        for line in received_data:
            line = line.decode('utf-8').strip()
            if not line.startswith('data: '):
                continue
            data = json.loads(line[6:])
            if data.get("event_type") == "CURVE":
                with self.lock:
                    self.curves[data["curve_name"]] = data
                continue
            symbol = data.get("symbol")
            if not symbol:
                continue
            with self.lock:
                self.cache[symbol] = data

    def get_price(self, symbol):
        """Get latest price for asset_description = (asset_class, symbol)"""
        with self.lock:
            return self.cache.get(symbol)

    def get_curve(self, curve_name):
        """Get latest curve by name, e.g. USD_DISCOUNT"""
        with self.lock:
            return self.curves.get(curve_name)
