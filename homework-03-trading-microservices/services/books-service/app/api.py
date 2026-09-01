from bottle import Bottle, request, response


class BooksServiceApi(Bottle):
    def __init__(self, books_service):
        super().__init__()
        self.books_service = books_service
        self.route('/health', method='GET', callback=self.health)
        self.route('/books', method='GET', callback=self.get_books)
        self.route('/books/<book_id>', method='GET', callback=self.get_book_by_id)
        self.route('/books', method='POST', callback=self.create_book)
        self.route('/books/<book_id>', method='PUT', callback=self.update_book)
        self.route('/books/<book_id>', method='DELETE', callback=self.delete_book)

    def health(self):
        """Health check requested"""
        health_status = {
            "service": "books-service",
            "status": "UP"
        }
        return health_status

    def book_to_dict(self, book) -> dict:
        return {
            "book_id": str(book.book_id),
            "name": book.name,
            "description": book.description,
            "expected_asset_class": book.expected_asset_class,
            "is_active": book.is_active,
            "created_at": book.created_at.isoformat() if book.created_at else None,
            "updated_at": book.updated_at.isoformat() if book.updated_at else None,
        }

    def get_books(self):
        """Get all books"""
        books = self.books_service.get_all_books()
        return {"books": [self.book_to_dict(b) for b in books]}

    def get_book_by_id(self, book_id):
        """Get a book by ID"""
        try:
            book = self.books_service.get_book_by_id(book_id)
            return self.book_to_dict(book)
        except ValueError as e:
            response.status = 404
            return {"error": str(e)}

    def create_book(self):
        """Create a new book"""
        data = request.json
        if not data:
            response.status = 400
            return {"error": "Request body is required"}
        try:
            book = self.books_service.create_book(data)
            response.status = 201
            return self.book_to_dict(book)
        except ValueError as e:
            response.status = 400
            return {"error": str(e)}

    def update_book(self, book_id):
        """Update a book by ID"""
        data = request.json
        if not data:
            response.status = 400
            return {"error": "Request body is required"}
        try:
            book = self.books_service.update_book(book_id, data)
            return self.book_to_dict(book)
        except ValueError as e:
            response.status = 404
            return {"error": str(e)}

    def delete_book(self, book_id):
        """Delete a book by ID"""
        try:
            self.books_service.delete_book(book_id)
            response.status = 204
        except ValueError as e:
            response.status = 404
            return {"error": str(e)}
