import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import update
from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import Trades
import structlog

class TradeActionRepository:
    def __init__(self):
        self.log = structlog.get_logger()

    def add_trade(self, trade_data):
        """Add a new trade to the database; returns trade_id, or None for a duplicate request"""
        with SessionFactory() as session:
            if trade_data.get("client_request_id"):
                existing = session.query(Trades).filter_by(
                    client_request_id=trade_data["client_request_id"]
                ).first()
                if existing:
                    self.log.warning("duplicate_trade_request", client_request_id=trade_data["client_request_id"])
                    return None

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
            session.flush()  # populate record.trade_id (Python-side default) before it's used below
            trade_id = record.trade_id
            session.commit()
            self.log.info("trade_opened", entity_type="Trade", entity_id=str(trade_id),
                          client_request_id=trade_data.get("client_request_id"))
            return trade_id

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
        """Atomic conditional close; returns the closed trade's symbol, or None if it was not ACTIVE"""
        with SessionFactory() as session:
            result = session.execute(
                update(Trades)
                .where(Trades.trade_id == trade_id, Trades.status == "ACTIVE")
                .values(**close_data)
                .returning(Trades.symbol)
            )
            symbol = result.scalar_one_or_none()
            session.commit()
            if symbol is not None:
                self.log.info("trade_closed", entity_type="Trade", entity_id=str(trade_id),
                              symbol=symbol, close_reason=close_data.get("close_reason"))
            return symbol
