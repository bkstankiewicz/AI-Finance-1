import datetime
import urllib.request
import structlog
import threading
from config import SERVICE_UP, SERVICE_DOWN
from shared.trading_shared.audit import log_audit_error, log_audit_recovery, AuditEventType
from functools import wraps
from time import perf_counter


opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)


def timed(func):
    """Return (result, elapsed_ms) measured with perf_counter"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = round((perf_counter() - start) * 1000, 0)
        return result, elapsed_ms

    return wrapper


class Monitor:
    def __init__(self):
        self.log = structlog.get_logger()
        self.status = {}
        self.error_counter = {}
        self._down_since = {}
        self.lock = threading.Lock()

    def log_service_error(self, service_name: str, error: str):
        """Service error connected to AuditLogs (via the log file)"""
        log_audit_error(self.log, AuditEventType.SERVICE_ERROR, "Service unavailable",
                        entity_type="Service", entity_id=service_name, error=error)

    @timed
    def ping_service(self, service_name: str, service_url: str):
        """Call /health; return (is_up, checked_at, error)"""
        is_up = False
        error = None
        try:
            request = urllib.request.Request(service_url)
            with urllib.request.urlopen(request, timeout=5) as response:
                is_up = response.status == 200
                if not is_up:
                    error = f"HTTP {response.status}"
        except Exception as exc:
            error = str(exc)
            self.log.warning(f"error_checking_{service_name}_service", exc_info=True)

        checked_at = datetime.datetime.now(datetime.timezone.utc)
        return is_up, checked_at, error

    @staticmethod
    def build_status(is_up: bool, checked_at, response_time_ms: float, error: str | None):
        """Build the status dict exposed by /status and /stream"""
        result = dict(SERVICE_UP if is_up else SERVICE_DOWN)
        result["last_checked"] = checked_at.isoformat()
        if is_up:
            result["response_time_ms"] = str(response_time_ms)
        else:
            result["error"] = error
        return result

    def update_status(self, service_name: str, result: dict, is_up: bool, checked_at):
        """Store the new status; return (previous_status, downtime_seconds)"""
        downtime_seconds = None
        with self.lock:
            previous_status = self.status.get(service_name, {}).get("status")
            self.status[service_name] = result
            if not is_up and previous_status != "DOWN":
                self._down_since[service_name] = checked_at
            elif is_up and previous_status == "DOWN":
                down_since = self._down_since.pop(service_name, checked_at)
                downtime_seconds = max(0.0, (checked_at - down_since).total_seconds())
        return previous_status, downtime_seconds

    def log_transition(self, service_name: str, is_up: bool, previous_status: str | None,
                       error: str | None, downtime_seconds: float | None):
        """Audit only UP->DOWN and DOWN->UP transitions"""
        if is_up and previous_status == "DOWN":
            log_audit_recovery(self.log, service_name, downtime_seconds)
        elif not is_up and previous_status != "DOWN":
            self.log_service_error(service_name, error)

    def check_service(self, service_name: str, service_url: str):
        """Check service health status"""
        (is_up, checked_at, error), response_time_ms = self.ping_service(service_name, service_url)
        result = self.build_status(is_up, checked_at, response_time_ms, error)
        previous_status, downtime_seconds = self.update_status(service_name, result, is_up, checked_at)
        self.log_transition(service_name, is_up, previous_status, error, downtime_seconds)
        return result
