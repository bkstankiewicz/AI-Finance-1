import os

SERVICE_NAME = "monitoring-service"

HOST = os.environ.get('MONITORING_HOST', '0.0.0.0')
PORT = int(os.environ.get('MONITORING_PORT', 8003))

MONITORING_INTERVAL = int(os.environ.get('MONITORING_INTERVAL', 1))

SERVICE_URLS = {
    "market-data-service": os.environ.get('MARKET_DATA_HEALTH_URL', 'http://localhost:8001/health'),
    "pricing-service": os.environ.get('PRICING_HEALTH_URL', 'http://localhost:8002/health'),
    "books-service": os.environ.get('BOOKS_HEALTH_URL', 'http://localhost:8004/health'),
    "trade-action-service": os.environ.get('TRADE_ACTION_HEALTH_URL', 'http://localhost:8008/health'),
    "trade-generation-service": os.environ.get('TRADE_GENERATION_HEALTH_URL', 'http://localhost:8007/health'),
    "blotter-service": os.environ.get('BLOTTER_HEALTH_URL', 'http://localhost:8006/health'),
}

SERVICE_UP = {
    "status": "UP",
    "last_checked": "2026-05-14T12:00:01.000Z",
    "response_time_ms": 12
}

SERVICE_DOWN = {
    "status": "DOWN",
    "last_checked": "2026-05-14T12:00:01.000Z",
    "error": "Connection refused"
}