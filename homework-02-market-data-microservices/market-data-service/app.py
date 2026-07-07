import random
import datetime
import logging
import time
import threading
import queue
import json
from bottle import get, response, run, ServerAdapter
from wsgiref.simple_server import make_server, WSGIServer
from socketserver import ThreadingMixIn


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class ThreadedServer(ServerAdapter):
    def run(self, handler):
        server = make_server(
            self.host,
            self.port,
            handler,
            server_class=ThreadingWSGIServer
        )
        server.serve_forever()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market-data-service")

event_id = 0
last_event_time = None
latest_equity = {}
latest_bond = {}
latest_fx = {}
json_data = "data.jsonl"
lock = threading.Lock()
subscribers = []

def publish_data(data):
    with lock:
        for subscriber_queue in subscribers:
            logger.info(f"Publishing data to subscriber: {data}")
            subscriber_queue.put(data)

def generate_market_tick():
    global event_id, last_event_time

    while True:
        with lock:
            event_id += 1
            last_event_time = datetime.datetime.now().isoformat()
        generate_equity_data(event_id, last_event_time)
        logging_events()

        with lock:
            event_id += 1
            last_event_time = datetime.datetime.now().isoformat()
        generate_fixed_income_data(event_id, last_event_time)
        logging_events()

        with lock:
            event_id += 1
            last_event_time = datetime.datetime.now().isoformat()
        generate_forex_data(event_id, last_event_time)
        logging_events()

        time.sleep(0.1)

def logging_events():
    if event_id % 50 == 0:
        logger.info(f"Generated {event_id} events")

def generate_equity_data(event_id, last_event_time):
    last_price = latest_equity.get("last", 100.0)

    ticks = round(random.uniform(-0.01, 0.01), 4)
    actual_price = round(last_price * (1 + ticks), 2)
    half_spread = round(actual_price * random.uniform(0.0002, 0.001) / 2, 2)
    bid = round(actual_price - half_spread, 2)
    ask = round(actual_price + half_spread, 2)

    data = {
        "event_id": event_id,
        "timestamp": last_event_time,
        "asset_type": "EQUITY",
        "symbol": "ACME",
        "bid": bid,
        "ask": ask,
        "last": actual_price
    }
    latest_equity.update(data)
    publish_data(data)
    with open(json_data, 'a', encoding='utf-8') as file:
        file.write(json.dumps(data) + '\n')

def generate_fixed_income_data(event_id, last_event_time):
    yield_rate = round(random.uniform(0.03, 0.06), 3)

    data = {
        "event_id": event_id,
        "timestamp": last_event_time,
        "asset_type": "BOND",
        "symbol": "GOVT_5Y",
        "yield": yield_rate
    }
    latest_bond.update(data)
    publish_data(data)
    with open(json_data, 'a', encoding='utf-8') as file:
        file.write(json.dumps(data) + '\n')

def generate_forex_data(event_id, last_event_time):
    spot = round(random.uniform(1.0, 1.5), 4)
    domestic_rate = round(random.uniform(0.01, 0.05), 4)
    foreign_rate = round(random.uniform(0.01, 0.05), 4)

    data = {
        "event_id": event_id,
        "timestamp": last_event_time,
        "asset_type": "FX",
        "symbol": "EURUSD",
        "spot": spot,
        "domestic_rate": domestic_rate,
        "foreign_rate": foreign_rate
    }
    latest_fx.update(data)
    publish_data(data)
    with open(json_data, 'a', encoding='utf-8') as file:
        file.write(json.dumps(data) + '\n')

def get_next_event(client_queue):
    logger.info("Get next event for client")
    return client_queue.get(timeout=30)

@get('/health')
def health():
    health_status = {
        "service": "market-data-service",
        "status": "UP",
        "generated_events": event_id if event_id > 0 else "No events",
        "last_event_time": last_event_time or "No events"
    }
    return health_status

@get('/snapshot')
def update_snapshot():
    return {
        "ACME": dict(latest_equity),
        "GOVT_5Y": dict(latest_bond),
        "EURUSD": dict(latest_fx)
    }

@get('/stream')
def stream():
    global subscribers
    logger.info("Client connected to stream")
    response.content_type = "text/event-stream"
    response.set_header("Cache-Control", "no-cache")

    client_queue = queue.Queue()
    with lock:
        subscribers.append(client_queue)
    logger.info(f"Active subscribers: {len(subscribers)}")

    def event_generator():
        try:
            while True:
                try:
                    logger.info("Waiting for new events for client...")
                    event = get_next_event(client_queue)
                    yield f"data: {json.dumps(event)}\n\n".encode('utf-8')
                except queue.Empty:
                    yield b": heartbeat\n\n"
        finally:
            with lock:
                subscribers.remove(client_queue)
            logger.info(f"Client disconnected. Active SSE clients: {len(subscribers)}")
    return event_generator()

if __name__ == '__main__':
    logger.info("Starting market data service")
    logger.info("Generating market data")
    thread = threading.Thread(target=generate_market_tick, daemon=True)
    thread.start()

    run(host='0.0.0.0', port=8001, server=ThreadedServer)  # type: ignore
