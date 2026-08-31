import os

SERVICE_NAME = "market-data-service"

HOST = os.environ.get('MARKET_DATA_HOST', '0.0.0.0')
PORT = int(os.environ.get('MARKET_DATA_PORT', 8001))

TICK_INTERVAL = float(os.environ.get('TICK_INTERVAL', 10.0))

TICK_BUFFER_SIZE = int(os.environ.get('TICK_BUFFER_SIZE', 100))
SNAPSHOT_BUFFER_SIZE = int(os.environ.get('SNAPSHOT_BUFFER_SIZE', 300))
CURVE_BUFFER_SIZE = int(os.environ.get('CURVE_BUFFER_SIZE', 100))