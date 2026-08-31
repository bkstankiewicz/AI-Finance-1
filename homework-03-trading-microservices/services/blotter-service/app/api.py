from bottle import Bottle, request, response


class BlotterServiceApi(Bottle):
    def __init__(self, blotter_repository):
        super().__init__()
        self.blotter_repository = blotter_repository

        self.route('/health', method='GET', callback=self.health)
        self.route('/books/summary', method='GET', callback=self.books_summary)
        self.route('/trades', method='GET', callback=self.get_trades)
        self.route('/trades/<trade_id>', method='GET', callback=self.get_trades_by_id)
        self.route('/trades/<trade_id>/valuations', method='GET', callback=self.get_trades_valuations)
        self.route('/trades/<trade_id>/audit-logs', method='GET', callback=self.get_trades_audit_logs)


    def health(self):
        """Health check requested"""
        health_status = {
            "service": "blotter-service",
            "status": "UP"
        }
        return health_status

    def books_summary(self):
        """Get summary of books with active trades and PnL values"""
        return {"books": self.blotter_repository.get_books_summary()}

    def get_trades(self):
        """Get trades with optional filters"""
        limit = int(request.query.get('limit', 20)) # type: ignore[attr-defined]
        book_id = request.query.get('book_id') # type: ignore[attr-defined]
        asset_class = request.query.get('asset_class') # type: ignore[attr-defined]
        status = request.query.get('status') # type: ignore[attr-defined]
        symbol = request.query.get('symbol') # type: ignore[attr-defined]

        return {"trades": self.blotter_repository.get_trades(limit, book_id, asset_class, status, symbol)}

    def get_trades_by_id(self, trade_id):
        """Get trade details by trade_id"""
        return self.blotter_repository.get_trades_by_id(trade_id)

    def get_trades_valuations(self, trade_id):
        """Get trade valuations by trade_id"""
        return self.blotter_repository.get_trades_valuations(trade_id)

    def get_trades_audit_logs(self, trade_id):
        """Get trade audit logs by trade_id"""
        return self.blotter_repository.get_trades_audit_logs(trade_id)
