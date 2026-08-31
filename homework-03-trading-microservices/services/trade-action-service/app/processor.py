import queue
import structlog
from config import SERVICE_NAME

class TradeActionProcessor:
    def __init__(self, trade_validation, trade_queue, repository):
        self.log = structlog.get_logger().bind(service=SERVICE_NAME)
        self.validation = trade_validation
        self.action_queue = trade_queue
        self.repository = repository

    def get_next_trade(self):
        """Retrieve the next trade action from the queue and process it"""
        try:
            action = self.action_queue.get(timeout=1)
            self.process_action(action)
        except queue.Empty:
            pass
        except Exception:
            self.log.exception("error_processing_trade_action")

    def process_action(self, action):
        """Process a single trade action based on its type"""
        action_type = action.get("action_type")

        if action_type == "OPEN_TRADE":
            self.open_trade(action)
        elif action_type == "CLOSE_TRADE":
            self.close_trade(action)
        else:
            self.log.warning("unknown_action_type", action_type=action_type)

    def open_trade(self, action):
        """Validate and add a new trade to the repository"""
        try:
            self.validation.validate_open_trade(action)
        except ValueError:
            self.log.exception("validation_error_open_trade")
            return

        self.repository.add_trade(action)

    def close_trade(self, action):
        """Validate and update an existing trade in the repository"""
        try:
            self.validation.validate_close_trade(action)
        except ValueError:
            self.log.exception("validation_error_close_trade")
            return

        close_data = action
        close_data["status"] = "CLOSED"
        closed = self.repository.close_trade_if_active(action["trade_id"], close_data)
        if not closed:
            self.log.warning("close_trade_rejected_not_active", trade_id=action["trade_id"])
