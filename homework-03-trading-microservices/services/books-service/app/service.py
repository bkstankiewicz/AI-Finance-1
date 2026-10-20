import inspect
from functools import wraps

import structlog
from config import SERVICE_NAME, VALID_ASSET_CLASSES, DEFAULT_BOOKS
from repository import BookNotFoundError


def log_errors(event):
    """Log unexpected exceptions as `event` and re-raise; business ValueErrors pass through unlogged"""
    def decorator(func):
        signature = inspect.signature(func)
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ValueError:
                raise
            except Exception:
                arguments = signature.bind(self, *args, **kwargs).arguments
                context = {"book_id": arguments["book_id"]} if "book_id" in arguments else {}
                self.log.exception(event, **context)
                raise

        return wrapper

    return decorator


def validate_asset_class(asset_class):
    if asset_class not in VALID_ASSET_CLASSES:
        raise ValueError(f"Invalid expected_asset_class: {asset_class}. Must be one of {VALID_ASSET_CLASSES}")


class BooksService:
    def __init__(self, books_repository):
        self.log = structlog.get_logger().bind(service=SERVICE_NAME)
        self.books_repository = books_repository

    @log_errors("error_retrieving_all_books")
    def get_all_books(self):
        """Get all books"""
        return self.books_repository.get_all_books()

    @log_errors("error_retrieving_book")
    def get_book_by_id(self, book_id):
        """Get a book by ID"""
        record = self.books_repository.get_book_by_id(book_id)
        if not record:
            raise BookNotFoundError(f"Book with ID {book_id} not found")
        return record

    @log_errors("error_creating_book")
    def create_book(self, book_data):
        """Create a new book"""
        if not book_data.get("name"):
            raise ValueError("Book name is required")

        asset_class = book_data.get("expected_asset_class")
        if not asset_class:
            raise ValueError("expected_asset_class is required")
        validate_asset_class(asset_class)

        return self.books_repository.create_book(book_data)

    @log_errors("error_updating_book")
    def update_book(self, book_id, book_data):
        """Update a book by ID"""
        asset_class = book_data.get("expected_asset_class")
        if asset_class:
            validate_asset_class(asset_class)

        updated_record = self.books_repository.update_book(book_id, book_data)
        if not updated_record:
            raise BookNotFoundError(f"Book with ID {book_id} not found")
        return updated_record

    def seed_default_books(self):
        """Create default books if none exist"""
        existing = self.books_repository.get_all_books()
        if existing:
            self.log.info("books_already_exist", count=len(existing))
            return

        for book_data in DEFAULT_BOOKS:
            try:
                self.books_repository.create_book(book_data)
                self.log.info("created_default_book", book_name=book_data["name"])
            except Exception:
                self.log.exception("failed_to_create_default_book", book_name=book_data["name"])

    @log_errors("error_deleting_book")
    def delete_book(self, book_id):
        """Delete book by ID"""
        if not self.books_repository.delete_book(book_id):
            raise BookNotFoundError(f"Book with ID {book_id} not found")
