import structlog

VALID_ASSET_CLASSES = ["EQUITY", "BOND", "FX", "COMMODITY", "FUTURES"]


class BooksService:
    def __init__(self, books_repository):
        self.log = structlog.get_logger().bind(service="books-service")
        self.books_repository = books_repository

    def get_all_books(self):
        """Get all books"""
        try:
            records = self.books_repository.get_all_books()
            return records
        except Exception:
            self.log.exception("error_retrieving_all_books")
            raise

    def get_book_by_id(self, book_id):
        """Get a book by ID"""
        try:
            record = self.books_repository.get_book_by_id(book_id)
        except Exception:
            self.log.exception("error_retrieving_book", book_id=book_id)
            raise

        if not record:
            raise ValueError(f"Book with ID {book_id} not found")
        return record

    def create_book(self, book_data):
        """Create a new book"""
        if not book_data.get("name"):
            raise ValueError("Book name is required")

        asset_class = book_data.get("expected_asset_class")
        if not asset_class:
            raise ValueError("expected_asset_class is required")

        if asset_class not in VALID_ASSET_CLASSES:
            raise ValueError(f"Invalid expected_asset_class: {asset_class}. Must be one of {VALID_ASSET_CLASSES}")

        try:
            created_record = self.books_repository.create_book(book_data)
        except Exception:
            self.log.exception("error_creating_book")
            raise

        return created_record

    def update_book(self, book_id, book_data):
        """Update a book by ID"""
        asset_class = book_data.get("expected_asset_class")
        if asset_class and asset_class not in VALID_ASSET_CLASSES:
            raise ValueError(f"Invalid expected_asset_class: {asset_class}. Must be one of {VALID_ASSET_CLASSES}")

        try:
            updated_record = self.books_repository.update_book(book_id, book_data)
        except Exception:
            self.log.exception("error_updating_book", book_id=book_id)
            raise

        if not updated_record:
            raise ValueError(f"Book with ID {book_id} not found")

        return updated_record

    def seed_default_books(self):
        """Create default books if none exist"""
        existing = self.books_repository.get_all_books()
        if existing:
            self.log.info("books_already_exist", count=len(existing))
            return

        default_books = [
            {"name": "EQUITY_BOOK_1", "expected_asset_class": "EQUITY"},
            {"name": "BOND_BOOK_1", "expected_asset_class": "BOND"},
            {"name": "FX_BOOK_1", "expected_asset_class": "FX"},
            {"name": "COMMODITY_BOOK_1", "expected_asset_class": "COMMODITY"},
            {"name": "FUTURES_BOOK_1", "expected_asset_class": "FUTURES"},
        ]
        for book_data in default_books:
            try:
                self.books_repository.create_book(book_data)
                self.log.info("created_default_book", book_name=book_data["name"])
            except Exception:
                self.log.exception("failed_to_create_default_book", book_name=book_data["name"])

    def delete_book(self, book_id):
        """Delete book by ID"""
        try:
            deleted = self.books_repository.delete_book(book_id)
        except Exception:
            self.log.exception("error_deleting_book", book_id=book_id)
            raise

        if not deleted:
            raise ValueError(f"Book with ID {book_id} not found")
