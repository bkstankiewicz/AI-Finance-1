from bottle import Bottle, response
from publisher import Publisher


class MarketDataApi(Bottle):
    def __init__(self, publisher: Publisher, latest_data: dict):
        super().__init__()
        self.publisher = publisher
        self.latest_data = latest_data
        self.route('/health', method='GET', callback=self.health)
        self.route('/snapshot', method='GET', callback=self.snapshot)
        self.route('/stream', method='GET', callback=self.stream)

    def health(self):
        """Health check requested"""
        last_event_id = None
        last_event_time = None

        if self.latest_data:
            latest = max(self.latest_data.values(), key=lambda x: x.get("event_id", 0))
            last_event_id = latest.get("event_id")
            last_event_time = latest.get("timestamp")

        health_status = {
            "service": "market-data-service",
            "status": "UP",
            "last_event_id": last_event_id,
            "last_event_time": last_event_time
        }
        return health_status

    def snapshot(self):
        """Last snapshot requested"""
        return self.latest_data

    def stream(self):
        """Stream requested"""
        response.content_type = "text/event-stream"
        response.set_header("Cache-Control", "no-cache")
        return self.publisher.stream_events()
