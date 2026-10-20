import json
import threading
import queue
import structlog
from config import SERVICE_NAME

class ValuationPublisher:
    def __init__(self):
        self.log = structlog.get_logger()
        self.subscribers = []
        self.latest_by_symbol = {}
        self.lock = threading.Lock()

    def subscribe(self, client_queue):
        """Subscribe a client queue to the publisher"""
        with self.lock:
            self.subscribers.append(client_queue)

    def unsubscribe(self, client_queue):
        """Unsubscribe a client queue from the publisher"""
        with self.lock:
            if client_queue in self.subscribers:
                self.subscribers.remove(client_queue)

    def publish_data(self, data):
        """Publish data to all subscribers"""
        with self.lock:
            self.latest_by_symbol[data.get("symbol")] = data
            subscribers = list(self.subscribers)
        for subscriber in subscribers:
            subscriber.put(data)

    def stream_events(self):
        """SSE event generator - subscribe, yield events, unsubscribe on disconnect"""
        client_queue = queue.Queue()
        self.subscribe(client_queue)
        with self.lock:
            initial_events = list(self.latest_by_symbol.values())
        self.log.info("client_subscribed", active_clients=len(self.subscribers))

        try:
            for event in initial_events:
                yield f"data: {json.dumps(event)}\n\n".encode('utf-8')
            while True:
                try:
                    event = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n".encode('utf-8')
                except queue.Empty:
                    yield b": heartbeat\n\n"
        finally:
            self.unsubscribe(client_queue)
            self.log.info("client_disconnected", active_clients=len(self.subscribers))
