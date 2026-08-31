import json
import urllib.request
import structlog
from config import GET_BOOKS_URL

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class TradeGeneratorBookClient:
    def __init__(self):
        self.books_cache = []
        self.log = structlog.get_logger().bind(service="trade-generation-service")

    def get_books(self):
        """Fetch the list of books from the books-service"""
        try:
            request = urllib.request.Request(GET_BOOKS_URL)
            with opener.open(request, timeout=5) as response:
                body = response.read()
                data = json.loads(body.decode())
                books = data.get("books", [])
                self.books_cache = books
                return books
        except Exception:
            self.log.exception("error_fetching_books")
            return self.books_cache

    def get_book_for_asset_class(self, asset_class):
        """Get a book that matches the given asset class"""
        books = self.get_books()
        matching = []
        for book in books:
            if book.get("expected_asset_class") == asset_class and book.get("is_active", True):
                matching.append(book)
        if not matching:
            self.log.warning("no_matching_book_found", asset_class=asset_class)
            return None
        return matching[0]
