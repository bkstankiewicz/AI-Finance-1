import threading


class LiveCache:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def update(self, trade_id, data):
        """Update the cache with new valuation data for a specific trade_id"""
        with self.lock:
            self.cache[trade_id] = data

    def get(self, trade_id):
        """Retrieve the cached valuation data for a specific trade_id"""
        with self.lock:
            return self.cache.get(trade_id)

    def get_all(self):
        """Retrieve all cached valuation data"""
        with self.lock:
            return dict(self.cache)
