from shared.trading_shared.repositories import AuditLogsRepository
from shared.trading_shared.audit import build_audit_log, AuditEventType, AuditSeverity
from config import SERVICE_NAME


class TradeActionValidation:
    def __init__(self):
        self.audit_repo = AuditLogsRepository()

    def reject_trade(self, log_data, message):
        """Audit-log a validation failure and raise to stop processing"""
        entity_id = log_data.get("trade_id") or log_data.get("client_request_id", "N/A")
        log_data = build_audit_log(
            event_type=AuditEventType.TRADE_REJECTED,
            severity=AuditSeverity.ERROR,
            service_name=SERVICE_NAME,
            entity_id=str(entity_id),
            entity_type="TradeAction",
            message=message,
            payload=log_data
        )
        self.audit_repo.push_audit_logs(log_data)
        raise ValueError(message)

    def validate_open_trade(self, action):
        """Validate the action data for opening a trade"""
        for field in ["action_type", "client_request_id", "side"]:
            if not action.get(field):
                self.reject_trade(action, f"Missing required field: {field}")

        if action.get("action_type") != "OPEN_TRADE":
            self.reject_trade(action, f"Invalid action_type for opening trade: {action.get('action_type')}. Must be 'OPEN_TRADE'")

    def validate_close_trade(self, action):
        """Validate the action data for closing a trade"""
        for field in ["action_type", "trade_id", "close_reason"]:
            if not action.get(field):
                self.reject_trade(action, f"Missing required field: {field}")

        if action.get("action_type") != "CLOSE_TRADE":
            self.reject_trade(action, f"Invalid action_type for closing trade: {action.get('action_type')}. Must be 'CLOSE_TRADE'")
