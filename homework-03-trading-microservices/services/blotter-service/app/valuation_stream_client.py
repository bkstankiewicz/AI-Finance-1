import json
import urllib.request
import threading
import time
import traceback
import structlog
from config import STREAM_URL, RECONNECTING_INTERVAL, SERVICE_NAME
from shared.trading_shared.repositories import AuditLogsRepository
from shared.trading_shared.audit import build_audit_log, AuditEventType, AuditSeverity

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)

class PricingServiceClient:
    def __init__(self, live_cache):
        self.log = structlog.get_logger().bind(service=SERVICE_NAME)
        self.audit_repo = AuditLogsRepository()
        self.lock = threading.Lock()
        self.connection_status = "DISCONNECTED"
        self.received_event_id = 0
        self.cache = live_cache

    def start(self):
        """Start streaming thread"""
        threading.Thread(target=self.connect_to_valuations_stream, daemon=True).start()

    def log_stream_status(self, event_type, severity, message):
        """Push a stream status audit entry; entity_id/entity_type are always the same for this client"""
        log_data = build_audit_log(
            event_type=event_type,
            severity=severity,
            service_name=SERVICE_NAME,
            entity_id=STREAM_URL,
            entity_type="Stream",
            message=message,
        )
        self.audit_repo.push_audit_logs(log_data)

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
                        self.log_stream_status(AuditEventType.STREAM_RECONNECTED, AuditSeverity.INFO, "Valuation stream connected")
                    self.read_events(response)
            except Exception:
                self.log.exception("error_connecting_to_valuations_stream")
            finally:
                with self.lock:
                    previous_status = self.connection_status
                    self.connection_status = "DISCONNECTED"
                if previous_status != "DISCONNECTED":
                    self.log_stream_status(AuditEventType.STREAM_ERROR, AuditSeverity.ERROR, "Valuation stream disconnected")
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
