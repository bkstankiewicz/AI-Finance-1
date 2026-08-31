import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import AuditLogs


class AuditLogsRepository:
    def __init__(self):
        pass

    def push_audit_logs(self, log_data, session=None):
        if session is not None:
            session.add(AuditLogs(**log_data))
            return

        with SessionFactory() as own_session:
            own_session.add(AuditLogs(**log_data))
            own_session.commit()
