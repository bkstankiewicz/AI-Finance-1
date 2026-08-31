from copy import deepcopy
from datetime import datetime, timezone
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import Valuations, Trades
import threading


class Persistence:
    def __init__(self):
        self.valuation_buffer = []
        self.valuation_lock = threading.Lock()

    def add_valuation(self, data):
        """Add valuation data to the buffer"""
        with self.valuation_lock:
            self.valuation_buffer.append(data)

    def push_valuations(self):
        """Push valuation data from the buffer to the database"""
        with self.valuation_lock:
            valuations = deepcopy(self.valuation_buffer)
            self.valuation_buffer.clear()

        with SessionFactory() as session:
            for data in valuations:
                session.add(Valuations(
                    trade_id=data["trade_id"],
                    book_id=data["book_id"],
                    asset_class=data["asset_class"],
                    valuation_time=datetime.now(timezone.utc),
                    fair_value=data["fair_value"],
                    market_value=data.get("market_value"),
                    unrealized_pnl=data.get("unrealized_pnl", 0),
                    realized_pnl=data.get("realized_pnl", 0),
                    total_pnl=data.get("total_pnl", 0),
                    currency=data.get("currency", "USD"),
                    market_data_reference=data.get("market_data_reference"),
                    valuation_payload=data
                ))
            session.commit()

    def get_all_active_trades(self, asset_class):
        """Get all active trades for a specific asset class"""
        results = []
        with SessionFactory() as session:
            records = session.query(Trades).filter(Trades.status == "ACTIVE", Trades.asset_class == asset_class).all()

            for record in records:
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
                }
                results.append(trade)
        return results

    def get_closed_trades(self, asset_class):
        """Closed trades that have not yet received their post-close realized PnL valuation"""
        results = []
        with SessionFactory() as session:
            records = session.query(Trades).filter(Trades.status == "CLOSED", Trades.is_settled == False, Trades.asset_class == asset_class).all()

            for record in records:
                results.append({
                    "trade_id": str(record.trade_id),
                    "book_id": str(record.book_id),
                    "asset_class": record.asset_class,
                    "symbol": record.symbol,
                    "side": record.side,
                    "quantity": float(record.quantity),
                    "trade_price": float(record.trade_price),
                    "trade_currency": record.trade_currency,
                    "close_price": float(record.close_price) if record.close_price is not None else None,
                })
        return results

    def mark_trade_settled(self, trade_id):
        """Mark a closed trade as settled once its final realized PnL has been calculated"""
        with SessionFactory() as session:
            session.query(Trades).filter(Trades.trade_id == trade_id).update({"is_settled": True})
            session.commit()

    def get_all_valuations(self, limit=20):
        """Get all valuations, limited by the specified number"""
        results = []
        with SessionFactory() as session:
            records = session.query(Valuations).order_by(Valuations.valuation_time.desc()).limit(limit).all()

            for record in records:
                valuation = {
                    "valuation_id": str(record.valuation_id),
                    "trade_id": str(record.trade_id),
                    "book_id": str(record.book_id),
                    "asset_class": record.asset_class,
                    "valuation_time": record.valuation_time.isoformat() if record.valuation_time else None,
                    "fair_value": float(record.fair_value),
                    "market_value": float(record.market_value) if record.market_value is not None else None,
                    "unrealized_pnl": float(record.unrealized_pnl),
                    "realized_pnl": float(record.realized_pnl),
                    "total_pnl": float(record.total_pnl),
                    "currency": record.currency,
                }
                results.append(valuation)
            return results

    def get_valuation_by_trade_id(self, trade_id, limit=20):
        """Get valuations for a specific trade_id, limited by the specified number"""
        results = []
        with SessionFactory() as session:
            records = (
                session.query(Valuations)
                .filter(Valuations.trade_id == trade_id)
                .order_by(Valuations.valuation_time.desc())
                .limit(limit)
                .all()
            )
            for record in records:
                results.append({
                    "valuation_id": str(record.valuation_id),
                    "trade_id": str(record.trade_id),
                    "book_id": str(record.book_id),
                    "asset_class": record.asset_class,
                    "valuation_time": record.valuation_time.isoformat() if record.valuation_time else None,
                    "fair_value": float(record.fair_value),
                    "market_value": float(record.market_value) if record.market_value is not None else None,
                    "unrealized_pnl": float(record.unrealized_pnl),
                    "realized_pnl": float(record.realized_pnl),
                    "total_pnl": float(record.total_pnl),
                    "currency": record.currency,
                })
        return results
