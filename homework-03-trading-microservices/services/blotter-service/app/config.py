import os

SERVICE_NAME = "blotter-service"

HOST = os.environ.get('BLOTTER_HOST', '0.0.0.0')
PORT = int(os.environ.get('BLOTTER_PORT', 8006))

STREAM_URL = os.environ.get('STREAM_URL', 'http://localhost:8002/valuation-stream')

RECONNECTING_INTERVAL = int(os.environ.get('RECONNECTING_INTERVAL', 1))
