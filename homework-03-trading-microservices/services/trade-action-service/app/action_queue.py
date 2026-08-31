import queue


class TradeActionQueue:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, data):
        """Put data into the queue"""
        self.queue.put(data)

    def get(self, timeout=1):
        """Get data from the queue with a timeout"""
        return self.queue.get(timeout=timeout)

    def get_size(self):
        """Get the current size of the queue"""
        return self.queue.qsize()