import json
import urllib.request
import threading
import time
import structlog
from config import STREAM_URL, RECONNECTING_INTERVAL
from shared.trading_shared.audit import log_audit_error, AuditEventType

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)

class PricingServiceClient:
    def __init__(self, live_cache):
        self.log = structlog.get_logger()
        self.lock = threading.Lock()
        self.connection_status = "DISCONNECTED"
        self.received_event_id = 0
        self.cache = live_cache

    def start(self):
        """Start streaming thread"""
        threading.Thread(target=self.connect_to_valuations_stream, daemon=True).start()

    def log_stream_disconnected(self):
        """STREAM_ERROR goes to AuditLogs (via the log file); entity_id/entity_type are always the same here"""
        log_audit_error(self.log, AuditEventType.STREAM_ERROR, "Valuation stream disconnected",
                        entity_type="Stream", entity_id=STREAM_URL)

    def connect_to_valuations_stream(self):
        """Connect to the pricing service stream and read events"""
        while True:
            try:
                request = urllib.request.Request(STREAM_URL, headers={'Accept': 'text/event-stream'})
                with urllib.request.urlopen(request, timeout=None) as response:
                    with self.lock:
                        previous_status = self.connection_status
                        self.connection_status = "CONNECTED"
                    self.log.info("connection_status", status=self.connection_status)
                    if previous_status != "CONNECTED":
                        self.log.info("valuation_stream_connected", entity_type="Stream", entity_id=STREAM_URL)
                    self.read_events(response)
            except Exception:
                # WARNING, not ERROR: this fires on every reconnect attempt; the audited STREAM_ERROR is logged once per disconnect
                self.log.warning("error_connecting_to_valuations_stream", exc_info=True)
            finally:
                with self.lock:
                    previous_status = self.connection_status
                    self.connection_status = "DISCONNECTED"
                if previous_status != "DISCONNECTED":
                    self.log_stream_disconnected()
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
