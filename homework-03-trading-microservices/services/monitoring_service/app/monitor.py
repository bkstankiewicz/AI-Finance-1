import datetime
import urllib.request
import time
import structlog
from config import SERVICE_UP, SERVICE_DOWN

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)

class Monitor:
    def __init__(self):
        self.log = structlog.get_logger().bind(service="monitoring-service")
        self.status = {}

    def check_service(self, service_name: str, service_url: str):
        """Check service health status"""
        start_time = time.perf_counter()
        is_up = False

        try:
            request = urllib.request.Request(service_url)
            with urllib.request.urlopen(request, timeout=5) as response:
                is_up = response.status == 200
                if is_up:
                    self.log.info(f"{service_name}_service_is_up", status=response.status)
                else:
                    self.log.warning(f"{service_name}_service_is_down", status=response.status)
        except Exception as e:
            self.log.warning(f"error_checking_{service_name}_service", error=str(e))

        response_time_ms = round((time.perf_counter() - start_time) * 1000, 0)

        self.status[service_name] = dict(SERVICE_UP if is_up else SERVICE_DOWN)
        self.status[service_name]["last_checked"] = datetime.datetime.now().isoformat()
        if is_up:
            self.status[service_name]["response_time_ms"] = str(response_time_ms)
        
        return self.status
