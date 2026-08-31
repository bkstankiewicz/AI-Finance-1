import os

SERVICE_NAME = "pricing-service"

HOST = os.environ.get('PRICING_HOST', '0.0.0.0')
PORT = int(os.environ.get('PRICING_PORT', 8002))

STREAM_URL = os.environ.get('STREAM_URL', 'http://localhost:8001/stream')

RECONNECTING_INTERVAL = int(os.environ.get('RECONNECTING_INTERVAL', 1))
VALUATION_INTERVAL = float(os.environ.get('VALUATION_INTERVAL', 5.0))