import logging
import threading
import datetime
import urllib.request
import json
import time
import os
from bottle import get, run, abort, ServerAdapter
from wsgiref.simple_server import make_server, WSGIServer
from socketserver import ThreadingMixIn


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class ThreadedServer(ServerAdapter):
    def run(self, handler):
        server = make_server(self.host, self.port, handler, server_class=ThreadingWSGIServer)
        server.serve_forever()

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)

INSTRUMENTS = {
    "EQ_ACME": {
        "type": "EQUITY",
        "market_symbol": "ACME",
        "currency": "USD"
    },
    "BOND_GOVT_5Y": {
        "type": "BOND",
        "market_symbol": "GOVT_5Y",
        "currency": "USD",
        "face_value": 1000,
        "coupon_rate": 0.05,
        "maturity_years": 5,
        "payments_per_year": 1
    },
    "FX_EURUSD_1Y": {
        "type": "FX_FORWARD",
        "market_symbol": "EURUSD",
        "currency": "USD",
        "tenor_years": 1.0
    }
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

last_pricing_time = "No pricing calculations yet"
connection_status = "DISCONNECTED"
received_event_id = 0
last_event_time = None
latest_equity = {}
latest_bond = {}
latest_fx = {}
stream_url = os.environ.get('MARKET_DATA_URL', 'http://localhost:8001/stream')
json_data = "data.jsonl"
lock = threading.Lock()

def calculate_equity(data):
    global last_pricing_time
    with lock:
        last_pricing_time = datetime.datetime.now().isoformat()

    logger.info("Calculating equity price...")
    bid = data.get("bid")
    ask = data.get("ask")
    mid = (bid + ask) / 2
    data = {
        "type": INSTRUMENTS["EQ_ACME"]["type"],
        "market_symbol": INSTRUMENTS["EQ_ACME"]["market_symbol"],
        "currency": INSTRUMENTS["EQ_ACME"]["currency"],
        "fair_value": mid,
        "last_updated": last_pricing_time
    }
    latest_equity.update(data)

def calculate_bond(data):
    global last_pricing_time
    with lock:
        last_pricing_time = datetime.datetime.now().isoformat()

    logger.info("Calculating bond price...")
    maturity_years = INSTRUMENTS["BOND_GOVT_5Y"]["maturity_years"]
    payments_per_year = INSTRUMENTS["BOND_GOVT_5Y"]["payments_per_year"]
    coupon_rate = INSTRUMENTS["BOND_GOVT_5Y"]["coupon_rate"]
    face_value = INSTRUMENTS["BOND_GOVT_5Y"]["face_value"]
    coupon = face_value * coupon_rate

    yield_rate = data.get("yield")
    pv = 0
    for i in range(1, maturity_years + 1):
        pv += coupon / (1 + yield_rate) ** i
    pv += (coupon + face_value) / (1 + yield_rate) ** maturity_years

    data = {
        "type": INSTRUMENTS["BOND_GOVT_5Y"]["type"],
        "market_symbol": INSTRUMENTS["BOND_GOVT_5Y"]["market_symbol"],
        "currency": INSTRUMENTS["BOND_GOVT_5Y"]["currency"],
        "fair_value": pv,
        "last_updated": last_pricing_time
    }
    latest_bond.update(data)

def calculate_fx_forward(data):
    global last_pricing_time
    with lock:
        last_pricing_time = datetime.datetime.now().isoformat()

    logger.info("Calculating FX forward price...")
    spot = data.get("spot")
    domestic_rate = data.get("domestic_rate")
    foreign_rate = data.get("foreign_rate")
    t = INSTRUMENTS["FX_EURUSD_1Y"]["tenor_years"]
    
    forward = spot * (1 + domestic_rate * t) / (1 + foreign_rate * t)

    data = {
        "type": INSTRUMENTS["FX_EURUSD_1Y"]["type"],
        "market_symbol": INSTRUMENTS["FX_EURUSD_1Y"]["market_symbol"],
        "currency": INSTRUMENTS["FX_EURUSD_1Y"]["currency"],
        "fair_value": forward,
        "last_updated": last_pricing_time
    }
    latest_fx.update(data)

def connect_to_market_data_stream():
    global connection_status
    logger.info("Connecting to market data stream...")
    while True:
        try:
            logger.info("Attempting to connect to market data stream")
            request = urllib.request.Request(stream_url, headers={'Accept': 'text/event-stream'})
            with urllib.request.urlopen(request, timeout=5) as response:
                with lock:
                    connection_status = "CONNECTED"
                logger.info(f"{connection_status} to market data stream")
                read_events(response)
        except Exception as e:
            logger.error(f"Error connecting to market data stream: {e}")
            with lock:
                connection_status = "DISCONNECTED"
            logger.info(f"Market data stream status: {connection_status}")
        
        logger.info(f"{connection_status} to market data stream in 1 second...")
        with lock:
            connection_status = "RECONNECTING"
        time.sleep(1)

def read_events(received_data):
    global received_event_id, last_event_time
    logger.info("Reading events from market data stream")
    for line in received_data:
        line = line.decode('utf-8').strip()
        if not line.startswith('data: '):
            continue
        data = json.loads(line[6:])
        logger.info(f"Parsed event data: {data}")
        with lock:
            received_event_id += 1
            last_event_time = data.get("timestamp")
        update_market_state(data)

def update_market_state(data):
    asset_type = data.get("asset_type")
    if asset_type == "EQUITY":
        calculate_equity(data)
    elif asset_type == "BOND":
        calculate_bond(data)
    elif asset_type == "FX":
        calculate_fx_forward(data)
    else:
        logger.warning(f"Unknown asset type received: {asset_type}")

@get('/health')
def health():
    health_status = {
        "service": "pricing-service",
        "status": "UP",
        "market_data_connection": connection_status,
        "received_events": received_event_id,
        "last_market_event_time": last_event_time,
        "last_pricing_time": last_pricing_time
    }
    return health_status

@get('/valuations')
def valuations():
    logger.info("Calculating valuations")
    return {
        "EQ_ACME": dict(latest_equity),
        "BOND_GOVT_5Y": dict(latest_bond),
        "FX_EURUSD_1Y": dict(latest_fx)
    }

@get('/valuations/<instrument_id>')
def valuations_by_instrument(instrument_id):
    logger.info(f"Calculating valuation for instrument: {instrument_id}")
    if instrument_id == "EQ_ACME":
        return dict(latest_equity)
    elif instrument_id == "BOND_GOVT_5Y":
        return dict(latest_bond)
    elif instrument_id == "FX_EURUSD_1Y":
        return dict(latest_fx)
    else:
        abort(404, f"Unknown instrument: {instrument_id}")

if __name__ == '__main__':
    logger.info("Starting pricing service")

    t = threading.Thread(target=connect_to_market_data_stream, daemon=True)
    t.start()

    run(host='0.0.0.0', port=8002, server=ThreadedServer)  # type: ignore
