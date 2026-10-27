import os

SERVICE_NAME = "pricing-service"

HOST = os.environ.get('PRICING_HOST', '0.0.0.0')
PORT = int(os.environ.get('PRICING_PORT', 8002))

STREAM_URL = os.environ.get('STREAM_URL', 'http://localhost:8001/stream')

RECONNECTING_INTERVAL = int(os.environ.get('RECONNECTING_INTERVAL', 1))
VALUATION_INTERVAL = float(os.environ.get('VALUATION_INTERVAL', 5.0))

BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 5000))
BUFFER_FLUSH_SIZE = int(os.environ.get('BUFFER_FLUSH_SIZE', 1000))

RECENT_CACHE_SIZE = int(os.environ.get('RECENT_CACHE_SIZE', 1000))
PER_TRADE_CACHE_SIZE = int(os.environ.get('PER_TRADE_CACHE_SIZE', 50))
MAX_CACHED_TRADES = int(os.environ.get('MAX_CACHED_TRADES', 10000))