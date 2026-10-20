import threading
import time
from collections import Counter
from datetime import datetime, timezone

RECENT_LIMIT = 20
THROUGHPUT_WINDOW_S = 60
DB_WRITE_OUTCOMES = ("OPENED", "CLOSED")


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


class ProcessingStats:
    """In-memory worker metrics (reset on restart); written by the worker, read by HTTP threads"""

    def __init__(self):
        self._lock = threading.Lock()
        self._started_at = _utcnow()
        self._outcomes = Counter()
        self._total_processing_ms = 0.0
        self._max_processing_ms = 0.0
        self._total_wait_ms = 0.0
        self._last_db_write_at = None
        self._finished_at = []
        self._recent_actions = []
        self._recent_rejections = []

    def record(self, action, outcome, wait_ms, processing_ms, message=None, symbol=None):
        now = time.perf_counter()
        payload = action if isinstance(action, dict) else {}
        entry = {
            **payload,
            "finished_at": _utcnow(),
            "action_type": payload.get("action_type"),
            "entity_id": payload.get("trade_id") or payload.get("client_request_id"),
            "symbol": symbol or payload.get("symbol") or payload.get("underlying_symbol"),
            "outcome": outcome,
            "wait_ms": round(wait_ms, 2),
            "processing_ms": round(processing_ms, 2),
            "message": message,
        }
        with self._lock:
            self._outcomes[outcome] += 1
            entry["seq"] = sum(self._outcomes.values())
            self._total_processing_ms += processing_ms
            self._max_processing_ms = max(self._max_processing_ms, processing_ms)
            self._total_wait_ms += wait_ms
            if outcome in DB_WRITE_OUTCOMES:
                self._last_db_write_at = entry["finished_at"]
            self._finished_at.append(now)
            self._trim_window(now)
            self._recent_actions = [entry] + self._recent_actions[:RECENT_LIMIT - 1]
            if outcome in ("REJECTED", "ERROR"):
                self._recent_rejections = [entry] + self._recent_rejections[:RECENT_LIMIT - 1]

    def _trim_window(self, now):
        self._finished_at = [t for t in self._finished_at if now - t <= THROUGHPUT_WINDOW_S]

    def snapshot(self, queue_size):
        with self._lock:
            self._trim_window(time.perf_counter())
            processed = sum(self._outcomes.values())
            return {
                "started_at": self._started_at,
                "queue_size": queue_size,
                "processed": processed,
                "db_writes": sum(self._outcomes[o] for o in DB_WRITE_OUTCOMES),
                "rejected": self._outcomes["REJECTED"],
                "errors": self._outcomes["ERROR"],
                "outcomes": dict(self._outcomes),
                "throughput_per_min": len(self._finished_at) * 60 / THROUGHPUT_WINDOW_S,
                "avg_processing_ms": round(self._total_processing_ms / processed, 2) if processed else None,
                "max_processing_ms": round(self._max_processing_ms, 2) if processed else None,
                "avg_wait_ms": round(self._total_wait_ms / processed, 2) if processed else None,
                "last_db_write_at": self._last_db_write_at,
                "recent_actions": list(self._recent_actions),
                "recent_rejections": list(self._recent_rejections),
            }
