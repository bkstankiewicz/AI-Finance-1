import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import AuditLogs


class AuditLogsRepository:
    def push_audit_logs_idempotent(self, rows):
        """Bulk insert in one transaction; rows whose audit_id already exists are skipped, so replays are safe"""
        if not rows:
            return
        statement = pg_insert(AuditLogs).values(rows).on_conflict_do_nothing(index_elements=["audit_id"])
        with SessionFactory() as session:
            session.execute(statement)
            session.commit()
