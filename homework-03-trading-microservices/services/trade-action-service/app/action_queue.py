import queue
import time


class TradeActionQueue:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, data):
        """Put data into the queue, stamped with the enqueue time"""
        self.queue.put((time.perf_counter(), data))

    def get(self, timeout=1):
        """Get (enqueued_at, data) from the queue with a timeout"""
        return self.queue.get(timeout=timeout)

    def get_size(self):
        """Get the current size of the queue"""
        return self.queue.qsize()