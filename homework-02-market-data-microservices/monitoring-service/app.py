import threading
import logging
import time
import datetime
import os
from bottle import get, run, ServerAdapter
from wsgiref.simple_server import make_server, WSGIServer
from socketserver import ThreadingMixIn
import urllib.request


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class ThreadedServer(ServerAdapter):
    def run(self, handler):
        server = make_server(self.host, self.port, handler, server_class=ThreadingWSGIServer)
        server.serve_forever()

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)

lock = threading.Lock()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monitoring-service")

service_urls = {
    "market-data-service": os.environ.get('MARKET_DATA_HEALTH_URL', 'http://localhost:8001/health'),
    "pricing-service": os.environ.get('PRICING_HEALTH_URL', 'http://localhost:8002/health'),
}

service_up = {
    "status": "UP",
    "last_checked": "2026-05-14T12:00:01.000Z",
    "response_time_ms": 12
}

service_down = {
    "status": "DOWN",
    "last_checked": "2026-05-14T12:00:01.000Z",
    "error": "Connection refused"
}

latest_market_service_status = {}
latest_pricing_service_status = {}

def check_market_data_service():
    logger.info("Checking market data service")
    while True:
        start_time = time.perf_counter()
        is_up = False
        try:
            request = urllib.request.Request(service_urls["market-data-service"])
            with urllib.request.urlopen(request, timeout=5) as response:
                is_up = response.status == 200
                if is_up:
                    logger.info("Market data service is UP")
                else:
                    logger.warning(f"Market data service returned status code: {response.status}")
        except Exception as e:
            logger.error(f"Error checking market data service: {e}")

        response_time_ms = round((time.perf_counter() - start_time) * 1000, 0)

        update = dict(service_up if is_up else service_down)
        update["last_checked"] = datetime.datetime.now().isoformat()
        if is_up:
            update["response_time_ms"] = str(response_time_ms)
        latest_market_service_status.clear()
        latest_market_service_status.update(update)
        time.sleep(1)

def check_pricing_service():
    logger.info("Checking pricing service")
    while True:
        start_time = time.perf_counter()
        is_up = False
        try:
            request = urllib.request.Request(service_urls["pricing-service"])
            with urllib.request.urlopen(request, timeout=5) as response:
                is_up = response.status == 200
                if is_up:
                    logger.info("Pricing service is UP")
                else:
                    logger.warning(f"Pricing service returned status code: {response.status}")
        except Exception as e:
            logger.error(f"Error checking pricing service: {e}")
        
        response_time_ms = round((time.perf_counter() - start_time) * 1000, 0)

        update = dict(service_up if is_up else service_down)
        update["last_checked"] = datetime.datetime.now().isoformat()
        if is_up:
            update["response_time_ms"] = str(response_time_ms)
        latest_pricing_service_status.clear()
        latest_pricing_service_status.update(update)
        time.sleep(1)

@get('/health')
def health():
    health_status = {
        "service": "monitoring-service",
        "status": "UP"
    }
    return health_status

@get('/status')
def service_status():
    logger.info("Status of services")
    return {
        "market-data-service": dict(latest_market_service_status),
        "pricing-service": dict(latest_pricing_service_status)
    }

if __name__ == '__main__':
    logger.info("Starting monitoring service")

    monitors = [check_market_data_service, check_pricing_service]
    threads = []

    for monitor in monitors:
        t = threading.Thread(target=monitor, daemon=True)
        threads.append(t)

    for thread in threads:    
        thread.start()

    run(host='0.0.0.0', port=8003, server=ThreadedServer)  # type: ignore
