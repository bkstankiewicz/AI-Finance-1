import structlog

from shared.trading_shared.audit import log_audit_error, AuditEventType
from config import SERVICE_NAME


class TradeActionValidation:
    def __init__(self):
        self.log = structlog.get_logger()

    def reject_trade(self, action, message):
        """Audit-log a validation failure (TRADE_REJECTED) and raise to stop processing"""
        entity_id = action.get("trade_id") or action.get("client_request_id", "N/A")
        log_audit_error(
            self.log,
            AuditEventType.TRADE_REJECTED,
            message,
            entity_type="TradeAction",
            entity_id=entity_id,
            action=action,
        )
        raise ValueError(message)

    def validate_open_trade(self, action):
        """Validate the action data for opening a trade"""
        for field in ["action_type", "client_request_id", "side"]:
            if not action.get(field):
                self.reject_trade(action, f"Missing required field: {field}")

        if action.get("action_type") != "OPEN_TRADE":
            self.reject_trade(action, f"Invalid action_type for opening trade: {action.get('action_type')}. Must be 'OPEN_TRADE'")

        if action.get("asset_class") == "EUROPEAN_OPTION":
            self.validate_option_fields(action)

    def validate_option_fields(self, action):
        """Validate option-specific fields of an OPEN_TRADE action"""
        for field in ["underlying_symbol", "option_type", "strike", "maturity_years"]:
            if not action.get(field):
                self.reject_trade(action, f"Missing required option field: {field}")

        if action["option_type"] not in ("CALL", "PUT"):
            self.reject_trade(action, f"Invalid option_type: {action['option_type']}. Must be 'CALL' or 'PUT'")

        if action["strike"] <= 0 or action["maturity_years"] <= 0:
            self.reject_trade(action, "strike and maturity_years must be positive")

    def validate_close_trade(self, action):
        """Validate the action data for closing a trade"""
        for field in ["action_type", "trade_id", "close_reason"]:
            if not action.get(field):
                self.reject_trade(action, f"Missing required field: {field}")

        if action.get("action_type") != "CLOSE_TRADE":
            self.reject_trade(action, f"Invalid action_type for closing trade: {action.get('action_type')}. Must be 'CLOSE_TRADE'")
