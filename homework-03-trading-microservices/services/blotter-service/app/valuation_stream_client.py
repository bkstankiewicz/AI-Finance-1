import json
import urllib.request
import threading
import time
import traceback
import structlog
from config import STREAM_URL, RECONNECTING_INTERVAL

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)

class PricingServiceClient:
    def __init__(self, live_cache):
        self.log = structlog.get_logger().bind(service="blotter-service")
        self.lock = threading.Lock()
        self.connection_status = "DISCONNECTED"
        self.received_event_id = 0
        self.cache = live_cache

    def start(self):
        """Start streaming thread"""
        threading.Thread(target=self.connect_to_valuations_stream, daemon=True).start()

    def connect_to_valuations_stream(self):
        """Connect to the pricing service stream and read events"""
        while True:
            try:
                request = urllib.request.Request(STREAM_URL, headers={'Accept': 'text/event-stream'})
                with urllib.request.urlopen(request, timeout=None) as response:
                    with self.lock:
                        self.connection_status = "CONNECTED"
                    self.log.info("connection_status", status=self.connection_status)
                    self.read_events(response)
            except Exception as e:
                self.log.exception("error_connecting_to_valuations_stream")
                with self.lock:
                    self.connection_status = "DISCONNECTED"
            time.sleep(RECONNECTING_INTERVAL)

    def read_events(self, received_data):
        """Reading events from pricing service stream and updating cache"""
        for line in received_data:
            line = line.decode('utf-8').strip()
            if not line.startswith('data: '):
                continue
            data = json.loads(line[6:])
            trade_id = data.get("trade_id")
            if not trade_id:
                continue
            self.cache.update(trade_id, data)
