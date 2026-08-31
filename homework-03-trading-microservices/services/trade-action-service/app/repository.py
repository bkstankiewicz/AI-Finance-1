import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import update
from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import Trades
from shared.trading_shared.repositories import AuditLogsRepository
from shared.trading_shared.audit import build_audit_log, AuditEventType, AuditSeverity
from config import SERVICE_NAME
import structlog

class TradeActionRepository:
    def __init__(self):
        self.log = structlog.get_logger().bind(service=SERVICE_NAME)
        self.audit_repo = AuditLogsRepository()

    def add_trade(self, trade_data):
        """Add a new trade to the database"""
        with SessionFactory() as session:
            if trade_data.get("client_request_id"):
                existing = session.query(Trades).filter_by(
                    client_request_id=trade_data["client_request_id"]
                ).first()
                if existing:
                    self.log.warning("duplicate_trade_request", client_request_id=trade_data["client_request_id"])
                    return

            record = Trades(
                 book_id=trade_data["book_id"],
                 asset_class=trade_data["asset_class"],
                 instrument_id=trade_data["instrument_id"],
                 symbol=trade_data["symbol"],
                 side=trade_data["side"],
                 quantity=trade_data["quantity"],
                 trade_price=trade_data["trade_price"],
                 trade_currency=trade_data["trade_currency"],
                 trade_date=trade_data["trade_date"],
                 status=trade_data.get("status", "ACTIVE"),
                 opened_at=trade_data.get("opened_at"),
                 closed_at=trade_data.get("closed_at"),
                 close_price=trade_data.get("close_price"),
                 close_reason=trade_data.get("close_reason"),
                 source=trade_data.get("source", "GENERATED"),
                 client_request_id=trade_data.get("client_request_id"),
                 trade_metadata=trade_data.get("trade_metadata")
            )
            session.add(record)

            log_data = build_audit_log(
                event_type=AuditEventType.TRADE_OPENED,
                severity=AuditSeverity.INFO,
                service_name=SERVICE_NAME,
                entity_id=str(record.trade_id),
                entity_type="Trade",
                message=f"Trade opened with ID {record.trade_id}",
                payload=trade_data
            )
            self.audit_repo.push_audit_logs(log_data, session)

            session.commit()

    def update_trade(self, trade_id, trade_data):
        """Update an existing trade by ID"""
        with SessionFactory() as session:
            record = session.get(Trades, trade_id)
            if not record:
                return None

            for key, value in trade_data.items():
                setattr(record, key, value)

            session.commit()
            session.refresh(record)
            return record

    def close_trade_if_active(self, trade_id, close_data):
        """Atomic conditional close; prevents concurrent double-close of the same trade"""
        with SessionFactory() as session:
            result = session.execute(
                update(Trades)
                .where(Trades.trade_id == trade_id, Trades.status == "ACTIVE")
                .values(**close_data)
                .returning(Trades.trade_id)
            )
            updated = result.first() is not None

            log_data = build_audit_log(
                event_type=AuditEventType.TRADE_CLOSED,
                severity=AuditSeverity.INFO,
                service_name=SERVICE_NAME,
                entity_id=str(trade_id),
                entity_type="Trade",
                message=f"Trade closed with ID {trade_id}",
                payload=close_data
            )
            self.audit_repo.push_audit_logs(log_data, session)

            session.commit()
            return updated
