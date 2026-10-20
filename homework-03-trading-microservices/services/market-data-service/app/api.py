import threading

from bottle import Bottle, request, response
from publisher import Publisher

MAX_HISTORY_LIMIT = 2000


class LatestValues:
    """Last value per key; written by worker threads, read by HTTP handler threads"""

    def __init__(self):
        self._items = {}
        self._lock = threading.Lock()

    def put(self, key, value) -> None:
        with self._lock:
            self._items[key] = value

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._items)


class MarketDataApi(Bottle):
    def __init__(self, publisher: Publisher, latest_data: LatestValues, latest_curves: LatestValues, refresh_curves, get_history):
        super().__init__()
        self.publisher = publisher
        self.latest_data = latest_data
        self.latest_curves = latest_curves
        self.refresh_curves_callback = refresh_curves
        self.get_history = get_history
        self.route('/health', method='GET', callback=self.health)
        self.route('/snapshot', method='GET', callback=self.snapshot)
        self.route('/history', method='GET', callback=self.history)
        self.route('/stream', method='GET', callback=self.stream)
        self.route('/curves', method='GET', callback=self.curves)
        self.route('/curves/refresh', method='POST', callback=self.refresh_curves)

    def health(self):
        """Health check requested"""
        last_event_id = None
        last_event_time = None

        latest_data = self.latest_data.snapshot()
        if latest_data:
            latest = max(latest_data.values(), key=lambda x: x.get("event_id", 0))
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
        return self.latest_data.snapshot()

    def history(self):
        """Persisted spot price history per symbol, so charts survive restarts"""
        try:
            limit = int(request.query.get('limit', 500)) # type: ignore[attr-defined]
        except ValueError:
            response.status = 400
            return {"error": "limit must be an integer"}
        return self.get_history(max(1, min(limit, MAX_HISTORY_LIMIT)))

    def curves(self):
        """Latest generated curves"""
        return self.latest_curves.snapshot()

    def refresh_curves(self):
        """Regenerate curves and persist them (hook for a future UI button)"""
        curves = self.refresh_curves_callback()
        return {"refreshed": [c["curve_name"] for c in curves]}

    def stream(self):
        """Stream requested"""
        response.content_type = "text/event-stream"
        response.set_header("Cache-Control", "no-cache")
        initial_events = [*self.latest_curves.snapshot().values(), *self.latest_data.snapshot().values()]
        return self.publisher.stream_events(initial_events=initial_events)
