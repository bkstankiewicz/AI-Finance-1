import os

SERVICE_NAME = "trade-action-service"

HOST = os.environ.get('TRADE_ACTION_HOST', '0.0.0.0')
PORT = int(os.environ.get('TRADE_ACTION_PORT', 8008))

ACTION_TYPES = ["OPEN_TRADE", "CLOSE_TRADE"]