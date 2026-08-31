import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import func
from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import Books, Trades, Valuations


class BlotterRepository:
    def __init__(self, valuation_cache):
        self.latest_valuations_cache = valuation_cache

    def get_books_summary(self):
        """Get summary of books with active trades and PnL values"""
        with SessionFactory() as session:
            books = session.query(Books).all()

            active_trades_rows = (
                session.query(Trades.book_id, func.count(Trades.trade_id).label("active_trades"))
                .filter(Trades.status == "ACTIVE")
                .group_by(Trades.book_id)
                .all()
            )

            active_trades_map = {}

            for trade_results in active_trades_rows:
                active_trades_map[str(trade_results.book_id)] = trade_results.active_trades

            latest_valuation = (
                session.query(Valuations.trade_id,
                    func.max(Valuations.valuation_time).label("max_time")
                )
                .group_by(Valuations.trade_id)
                .subquery()
            )

            pnl_values_rows = (
                session.query(Valuations.book_id,
                    func.sum(Valuations.realized_pnl).label("realized_pnl"),
                    func.sum(Valuations.unrealized_pnl).label("unrealized_pnl"),
                    func.sum(Valuations.total_pnl).label("total_pnl"),
                    Valuations.currency
                ).join(
                    latest_valuation,
                    (Valuations.trade_id == latest_valuation.c.trade_id) &
                    (Valuations.valuation_time == latest_valuation.c.max_time)
                )
                .group_by(Valuations.book_id, Valuations.currency)
                .all()
            )

            pnl_values_map = {}

            for pnl_results in pnl_values_rows:
                pnl_values_map[str(pnl_results.book_id)] = pnl_results

            results = []

            for book in books:
                book_id = str(book.book_id)
                pnl = pnl_values_map.get(book_id)
                results.append({
                    "book_id": book_id,
                    "name": book.name,
                    "expected_asset_class": book.expected_asset_class,
                    "active_trades": int(active_trades_map.get(str(book.book_id), 0)),
                    "realized_pnl": float(pnl.realized_pnl) if pnl else 0.0,
                    "unrealized_pnl": float(pnl.unrealized_pnl) if pnl else 0.0,
                    "total_pnl": float(pnl.total_pnl) if pnl else 0.0,
                    "currency": pnl.currency if pnl else "USD",
                })

            return results

    def get_trades(self, limit=20, book_id=None, asset_class=None, status=None, symbol=None):
        """Get trades with optional filters"""
        results = []
        with SessionFactory() as session:
            query = session.query(Trades).order_by(Trades.trade_date.desc())

            if book_id:
                query = query.filter(Trades.book_id == book_id)
            if asset_class:
                query = query.filter(Trades.asset_class == asset_class)
            if status:
                query = query.filter(Trades.status == status)
            if symbol:
                query = query.filter(Trades.symbol == symbol)

            records = query.limit(limit).all()

            for record in records:

                trade_id = str(record.trade_id)
                cached = self.latest_valuations_cache.get(trade_id)
                if cached is None:
                    return {"error": "No valuation found for the given trade_id"}

                trade = {
                    "trade_id": str(record.trade_id),
                    "book_id": str(record.book_id),
                    "asset_class": record.asset_class,
                    "symbol": record.symbol,
                    "side": record.side,
                    "quantity": float(record.quantity),
                    "trade_price": float(record.trade_price),
                    "trade_currency": record.trade_currency,
                    "status": record.status,
                    "close_price": float(record.close_price) if record.close_price is not None else None,
                    "fair_value": float(cached["fair_value"]) if cached else 0.0,
                    "unrealized_pnl": float(cached["unrealized_pnl"]) if cached else 0.0,
                    "realized_pnl": float(cached["realized_pnl"]) if cached else 0.0,
                    "total_pnl": float(cached["total_pnl"]) if cached else 0.0
                }
                results.append(trade)

        return results

    def get_trades_by_id(self, trade_id):
        """Get trade details by trade_id"""
        results = {}
        limit = 1
        with SessionFactory() as session:
            trade = session.query(Trades).filter(Trades.trade_id == trade_id).first()
            if trade is None:
                return {"error": "Trade not found"}

            latest_valuation = self.latest_valuations_cache.get(trade_id)
            if latest_valuation is None:
                return {"error": "No valuation found for the given trade_id"}

            valuation_history = session.query(Valuations).filter(Valuations.trade_id == trade_id).order_by(Valuations.valuation_time.desc()).limit(limit).all()
            if not valuation_history:
                return {"error": "No valuation history found for the given trade_id"}

            valuation_history_results = []

            for valuation in valuation_history:
                valuation_history_results.append({
                    "valuation_time": valuation.valuation_time.isoformat() if valuation.valuation_time else None,
                    "fair_value": float(valuation.fair_value),
                    "unrealized_pnl": float(valuation.unrealized_pnl)
                })

            # TODO: Add get Audit Logs

            results = {
                "trade": {
                    "trade_id": str(trade.trade_id),
                    "book_id": str(trade.book_id),
                    "asset_class": trade.asset_class,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": float(trade.quantity),
                    "trade_price": float(trade.trade_price),
                    "status": trade.status
                },
                "latest_valuation": {
                    "fair_value": float(latest_valuation["fair_value"]) if latest_valuation else 0.0,
                    "unrealized_pnl": float(latest_valuation["unrealized_pnl"]) if latest_valuation else 0.0,
                    "realized_pnl": float(latest_valuation["realized_pnl"]) if latest_valuation else 0.0,
                    "total_pnl": float(latest_valuation["total_pnl"]) if latest_valuation else 0.0,
                    "source": latest_valuation.get("source") if latest_valuation else None,
                },
                "valuation_history": valuation_history_results
            }

        return results

    def get_trades_valuations(self, trade_id):
        """Get trade valuations by trade_id"""
        results = {}
        latest_valuation = self.latest_valuations_cache.get(trade_id)
        if latest_valuation is None:
            return {"error": "No valuation found for the given trade_id"}

        results = {
            "trade_id": trade_id,
            "fair_value": float(latest_valuation["fair_value"]) if latest_valuation else 0.0,
            "unrealized_pnl": float(latest_valuation["unrealized_pnl"]) if latest_valuation else 0.0,
            "realized_pnl": float(latest_valuation["realized_pnl"]) if latest_valuation else 0.0,
            "total_pnl": float(latest_valuation["total_pnl"]) if latest_valuation else 0.0,
        }

        return results

    def get_trades_audit_logs(self, trade_id):
        results = {}

        return results
