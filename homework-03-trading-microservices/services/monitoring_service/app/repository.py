import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import AuditLogs
from sqlalchemy import func, select


def get_error_counter_per_service(service_name: str):
    with SessionFactory() as session:
        result = session.execute(
            select(func.count(AuditLogs.audit_id))
            .where(AuditLogs.entity_type == "Service")
            .where(AuditLogs.entity_id == service_name)
            .where(AuditLogs.event_type == "SERVICE_ERROR")
        ).scalar()
    return result

def get_last_error_timestamp(service_name: str):
    with SessionFactory() as session:
        result = session.execute(
            select(func.max(AuditLogs.created_at))
            .where(AuditLogs.entity_type == "Service")
            .where(AuditLogs.entity_id == service_name)
            .where(AuditLogs.event_type == "SERVICE_ERROR")
        ).scalar()
    return result