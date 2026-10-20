import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import structlog
from sqlalchemy.exc import IntegrityError

from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import Books
from config import SERVICE_NAME


UPDATABLE_FIELDS = {"name", "description", "expected_asset_class", "is_active", "updated_by"}


class BookNotFoundError(ValueError):
    pass


class BookInUseError(ValueError):
    pass


class BooksRepository:
    def __init__(self):
        self.log = structlog.get_logger().bind(service=SERVICE_NAME)

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
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ValueError(f"Book with name '{book_data['name']}' already exists")
            session.refresh(record)
            self.log.info("book_created", entity_type="Book", entity_id=str(record.book_id), name=record.name)
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

            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ValueError(f"Book with name '{book_data.get('name')}' already exists")
            session.refresh(record)
            self.log.info("book_deactivated" if is_deactivation else "book_updated",
                          entity_type="Book", entity_id=str(record.book_id), changes=book_data)
            return record

    def delete_book(self, book_id):
        """Delete a book by ID"""
        with SessionFactory() as session:
            record = session.get(Books, book_id)
            if not record:
                return False
            name = record.name
            session.delete(record)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise BookInUseError(
                    f"Book '{name}' is referenced by trades or valuations; deactivate it with is_active=false")
            self.log.warning("book_deleted", entity_type="Book", entity_id=str(book_id), name=name)
            return True
