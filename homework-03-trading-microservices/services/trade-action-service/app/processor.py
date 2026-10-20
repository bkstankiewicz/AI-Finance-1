import queue
import time
from typing import NamedTuple, Optional

import structlog


class ActionResult(NamedTuple):
    outcome: str
    message: Optional[str] = None
    symbol: Optional[str] = None  # resolved from DB when the payload doesn't carry it (CLOSE_TRADE)


class TradeActionProcessor:
    def __init__(self, trade_validation, trade_queue, repository, stats):
        self.log = structlog.get_logger()
        self.validation = trade_validation
        self.action_queue = trade_queue
        self.repository = repository
        self.stats = stats

    def get_next_trade(self):
        """Retrieve the next trade action from the queue, process it and record metrics"""
        try:
            enqueued_at, action = self.action_queue.get(timeout=1)
        except queue.Empty:
            return

        started_at = time.perf_counter()
        try:
            result = self.process_action(action)
        except Exception as e:
            self.log.exception("error_processing_trade_action")
            result = ActionResult("ERROR", type(e).__name__)
        finished_at = time.perf_counter()

        self.stats.record(
            action, result.outcome,
            wait_ms=(started_at - enqueued_at) * 1000,
            processing_ms=(finished_at - started_at) * 1000,
            message=result.message,
            symbol=result.symbol,
        )

    def process_action(self, action):
        """Process a single trade action based on its type; returns ActionResult"""
        action_type = action.get("action_type")

        if action_type == "OPEN_TRADE":
            return self.open_trade(action)
        if action_type == "CLOSE_TRADE":
            return self.close_trade(action)
        self.log.warning("unknown_action_type", action_type=action_type)
        return ActionResult("UNKNOWN_TYPE", f"Unknown action_type: {action_type}")

    def open_trade(self, action):
        """Validate and add a new trade to the repository"""
        try:
            self.validation.validate_open_trade(action)
        except ValueError as e:
            return ActionResult("REJECTED", str(e))  # already audited as TRADE_REJECTED by validation

        if self.repository.add_trade(action) is None:
            return ActionResult("DUPLICATE")
        return ActionResult("OPENED")

    def close_trade(self, action):
        """Validate and update an existing trade in the repository"""
        try:
            self.validation.validate_close_trade(action)
        except ValueError as e:
            return ActionResult("REJECTED", str(e))  # already audited as TRADE_REJECTED by validation

        close_data = {
            "status": "CLOSED",
            "close_price": action.get("close_price"),
            "close_reason": action.get("close_reason"),
            "closed_at": action.get("closed_at"),
        }
        symbol = self.repository.close_trade_if_active(action["trade_id"], close_data)
        if symbol is None:
            self.log.warning("close_trade_rejected_not_active", trade_id=action["trade_id"])
            return ActionResult("NOT_ACTIVE", "Trade not found or already closed")
        return ActionResult("CLOSED", symbol=symbol)
