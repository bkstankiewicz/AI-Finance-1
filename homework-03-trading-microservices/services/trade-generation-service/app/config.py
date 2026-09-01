import os

SERVICE_NAME = "trade-generation-service"

HOST = os.environ.get('TRADE_GENERATION_HOST', '0.0.0.0')
PORT = int(os.environ.get('TRADE_GENERATION_PORT', 8007))

STREAM_URL = os.environ.get('STREAM_URL', 'http://localhost:8001/stream')
GET_BOOKS_URL = os.environ.get('GET_BOOKS_URL', 'http://localhost:8004/books')
GET_ACTIVE_TRADES_URL = os.environ.get('GET_ACTIVE_TRADES_URL', 'http://localhost:8006/trades?status=ACTIVE&limit=20')
TRADE_ACTION_URL = os.environ.get('TRADE_ACTION_URL', 'http://localhost:8008/trade-actions')

RECONNECTING_INTERVAL = int(os.environ.get('RECONNECTING_INTERVAL', 1))
GENERATION_INTERVAL = float(os.environ.get('GENERATION_INTERVAL', 10.0))