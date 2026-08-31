from enum import Enum

from shared.trading_shared.serialization import to_jsonable


class AuditEventType(str, Enum):
    BOOK_CREATED = "BOOK_CREATED" #DONE
    BOOK_UPDATED = "BOOK_UPDATED" #DONE
    BOOK_DELETED = "BOOK_DELETED" #DONE
    BOOK_DEACTIVATED = "BOOK_DEACTIVATED" #DONE

    TRADE_OPENED = "TRADE_OPENED" #DONE
    TRADE_CLOSED = "TRADE_CLOSED" #DONE
    TRADE_REJECTED = "TRADE_REJECTED" #DONE

    SNAPSHOT_TAKEN = "SNAPSHOT_TAKEN"

    DB_PUSH_ERROR = "DB_PUSH_ERROR"

    STREAM_ERROR = "STREAM_ERROR"
    STREAM_RECONNECTED = "STREAM_RECONNECTED"


class AuditSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


def build_audit_log(service_name, event_type, entity_id, message, entity_type=None,
                       severity=AuditSeverity.INFO, payload=None, correlation_id=None):
    """Build a dict matching the AuditLogs columns, ready for push_audit_logs"""
    return {
        "service_name": service_name,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id is not None else None,
        "correlation_id": correlation_id,
        "severity": severity,
        "message": message,
        "payload": to_jsonable(payload),
    }
