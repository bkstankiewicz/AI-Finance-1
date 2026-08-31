import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy.exc import IntegrityError

from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import Books
from shared.trading_shared.repositories import AuditLogsRepository
from shared.trading_shared.audit import build_audit_log, AuditEventType, AuditSeverity
from config import SERVICE_NAME


UPDATABLE_FIELDS = {"name", "description", "expected_asset_class", "is_active", "updated_by"}


class BooksRepository:
    def __init__(self):
        self.audit_repo = AuditLogsRepository()

    def get_all_books(self):
        """Get all books"""
        with SessionFactory() as session:
            record_all = session.query(Books).all()
            return record_all

    def get_book_by_id(self, book_id):
        """Get a book by ID"""
        with SessionFactory() as session:
            record = session.get(Books, book_id)
            return record

    def create_book(self, book_data):
        """Create a new book"""
        with SessionFactory() as session:
            record = Books(
                name=book_data["name"],
                description=book_data.get("description"),
                expected_asset_class=book_data["expected_asset_class"],
                is_active=book_data.get("is_active", True),
                created_by=book_data.get("created_by"),
                updated_by=book_data.get("updated_by")
            )
            session.add(record)

            log_data = build_audit_log(
                event_type=AuditEventType.BOOK_CREATED,
                severity=AuditSeverity.INFO,
                service_name=SERVICE_NAME,
                entity_id=str(record.book_id),
                entity_type="Book",
                message=f"Book '{record.name}' created with ID {record.book_id}",
                payload=book_data
            )
            
            self.audit_repo.push_audit_logs(log_data, session)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ValueError(f"Book with name '{book_data['name']}' already exists")
            session.refresh(record)
            return record

    def update_book(self, book_id, book_data):
        """Update a book by ID"""
        with SessionFactory() as session:
            record = session.get(Books, book_id)
            if not record:
                return None

            is_deactivation = book_data.get("is_active") is False and record.is_active

            for key, value in book_data.items():
                if key in UPDATABLE_FIELDS and value is not None:
                    setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)

            event_type = AuditEventType.BOOK_DEACTIVATED if is_deactivation else AuditEventType.BOOK_UPDATED
            message = f"Book '{record.name}' deactivated" if is_deactivation else f"Book '{record.name}' updated with ID {record.book_id}"
            log_data = build_audit_log(
                event_type=event_type,
                severity=AuditSeverity.INFO,
                service_name=SERVICE_NAME,
                entity_id=str(record.book_id),
                entity_type="Book",
                message=message,
                payload=book_data
            )
            self.audit_repo.push_audit_logs(log_data, session)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ValueError(f"Book with name '{book_data.get('name')}' already exists")
            session.refresh(record)
            return record

    def delete_book(self, book_id):
        """Delete a book by ID"""
        with SessionFactory() as session:
            record = session.get(Books, book_id)
            if not record:
                return False
            session.delete(record)

            log_data = build_audit_log(
                event_type=AuditEventType.BOOK_DELETED,
                severity=AuditSeverity.WARNING,
                service_name=SERVICE_NAME,
                entity_id=str(record.book_id),
                entity_type="Book",
                message=f"Book '{record.name}' deleted with ID {record.book_id}",
                payload=None
            )
            self.audit_repo.push_audit_logs(log_data, session)
            session.commit()
            return True
