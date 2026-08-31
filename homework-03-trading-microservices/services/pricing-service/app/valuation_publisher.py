import json
import threading
import queue
import structlog

class ValuationPublisher:
    def __init__(self):
        self.log = structlog.get_logger().bind(service="pricing-service")
        self.subscribers = []
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
            subscribers = list(self.subscribers)
        for subscriber in subscribers:
            subscriber.put(data)

    def stream_events(self):
        """SSE event generator - subscribe, yield events, unsubscribe on disconnect"""
        client_queue = queue.Queue()
        self.subscribe(client_queue)
        self.log.info("client_subscribed", active_clients=len(self.subscribers))

        try:
            while True:
                try:
                    event = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n".encode('utf-8')
                except queue.Empty:
                    yield b": heartbeat\n\n"
        finally:
            self.unsubscribe(client_queue)
            self.log.info("client_disconnected", active_clients=len(self.subscribers))
