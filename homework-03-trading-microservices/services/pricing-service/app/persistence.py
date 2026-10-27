from collections import OrderedDict, defaultdict, deque
from datetime import datetime, timezone
import sys
import threading
import uuid
from pathlib import Path
import structlog
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.audit import log_audit_error, AuditEventType
from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import Valuations, Trades

from config import BATCH_SIZE, BUFFER_FLUSH_SIZE, RECENT_CACHE_SIZE, PER_TRADE_CACHE_SIZE, MAX_CACHED_TRADES

log = structlog.get_logger()


TRADE_COLUMNS = (
    Trades.trade_id,
    Trades.book_id,
    Trades.asset_class,
    Trades.symbol,
    Trades.side,
    Trades.quantity,
    Trades.trade_price,
    Trades.trade_currency,
    Trades.close_price,
)

ACTIVE = (Trades.status == "ACTIVE",)
CLOSED_NOT_SETTLED = (Trades.status == "CLOSED", Trades.is_settled == False)


class TradesCache:
    """Loads trades of all asset classes with one query and gives each asset class its list once per cycle"""

    def __init__(self, load_trades):
        self.load_trades = load_trades
        self.lock = threading.Lock()
        self.trades_by_asset_class = {}
        self.served = set()

    def get(self, asset_class):
        with self.lock:
            if not self.served or asset_class in self.served:
                self.trades_by_asset_class = self.load_trades()
                self.served = set()
            self.served.add(asset_class)
            return self.trades_by_asset_class.pop(asset_class, [])


class ValuationCache:
    """Latest stored valuations (newest first): globally and per trade, so reads don't scan Valuations.

    Global view is loaded from the DB at startup, per-trade views lazily on first read;
    afterwards both are kept up to date by add().
    Writers must hold self.lock across the DB commit and add(), so a load never misses a committed row.
    """

    def __init__(self, load_latest, load_by_trade_id):
        self.load_latest = load_latest
        self.load_by_trade_id = load_by_trade_id
        self.lock = threading.RLock()
        self.recent = deque(load_latest(), maxlen=RECENT_CACHE_SIZE)
        self.by_trade = OrderedDict()

    def add(self, valuations):
        with self.lock:
            for valuation in valuations:
                self.recent.appendleft(valuation)
                trade_valuations = self.by_trade.get(valuation["trade_id"])
                if trade_valuations is not None:
                    trade_valuations.appendleft(valuation)

    def latest(self):
        with self.lock:
            snapshot = list(self.recent)
        for valuation in snapshot:
            yield valuation

    def by_trade_id(self, trade_id):
        with self.lock:
            trade_valuations = self.by_trade.get(trade_id)
            if trade_valuations is None:
                trade_valuations = deque(self.load_by_trade_id(trade_id), maxlen=PER_TRADE_CACHE_SIZE)
                self.by_trade[trade_id] = trade_valuations
                if len(self.by_trade) > MAX_CACHED_TRADES:
                    self.by_trade.popitem(last=False)
            else:
                self.by_trade.move_to_end(trade_id)
            snapshot = list(trade_valuations)
        for valuation in snapshot:
            yield valuation


class Persistence:
    def __init__(self):
        self.valuation_buffer = []
        self.valuation_lock = threading.Lock()
        self.active_trades_cache = TradesCache(lambda: self._load_trades_by_asset_class(ACTIVE))
        self.closed_trades_cache = TradesCache(lambda: self._load_trades_by_asset_class(CLOSED_NOT_SETTLED))
        self.valuation_cache = ValuationCache(
            lambda: self._query_valuations(RECENT_CACHE_SIZE),
            lambda trade_id: self._query_valuations(PER_TRADE_CACHE_SIZE, Valuations.trade_id == trade_id),
        )

    def add_valuation(self, data):
        """Add valuation data to the buffer; flushes it right away once it reaches BUFFER_FLUSH_SIZE"""
        with self.valuation_lock:
            self.valuation_buffer.append(data)
            if len(self.valuation_buffer) < BUFFER_FLUSH_SIZE:
                return
            batch = self._take_buffer()
        try:
            self._store(batch)
        except Exception:
            log_audit_error(log, AuditEventType.DB_PUSH_ERROR, "Error pushing valuations to DB", exc_info=True)

    def push_valuations(self):
        """Push valuation data from the buffer to the database"""
        with self.valuation_lock:
            batch = self._take_buffer()
        if batch:
            self._store(batch)

    def _take_buffer(self):
        """Shallow-copy and clear the buffer; caller must hold valuation_lock"""
        batch = self.valuation_buffer.copy()
        self.valuation_buffer.clear()
        return batch

    def _store(self, batch, settle_trade_id=None):
        records = [self._to_valuation(data) for data in batch]
        cached = [self._valuation_to_dict(record) for record in records]
        with self.valuation_cache.lock, SessionFactory() as session:
            session.add_all(records)
            if settle_trade_id is not None:
                session.query(Trades).filter(Trades.trade_id == settle_trade_id).update({"is_settled": True})
            session.commit()
            self.valuation_cache.add(cached)

    @staticmethod
    def _to_valuation(data):
        return Valuations(
            valuation_id=uuid.uuid4(),
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
        )

    @staticmethod
    def _to_trade(row):
        return {
            "trade_id": str(row.trade_id),
            "book_id": str(row.book_id),
            "asset_class": row.asset_class,
            "symbol": row.symbol,
            "side": row.side,
            "quantity": float(row.quantity),
            "trade_price": float(row.trade_price),
            "trade_currency": row.trade_currency,
            "close_price": float(row.close_price) if row.close_price is not None else None,
        }

    def _query_trades(self, conditions):
        """Reads matching trades in batches of BATCH_SIZE instead of loading the whole result at once"""
        with SessionFactory() as session:
            query = session.query(*TRADE_COLUMNS).filter(*conditions).yield_per(BATCH_SIZE)
            return [self._to_trade(row) for row in query]

    def _load_trades_by_asset_class(self, conditions):
        trades_by_asset_class = defaultdict(list)
        for trade in self._query_trades(conditions):
            trades_by_asset_class[trade["asset_class"]].append(trade)
        return trades_by_asset_class

    @staticmethod
    def _filter_conditions(filters):
        """{"symbol": "AAPL"} -> symbol = 'AAPL', {"symbol": ["AAPL", "MSFT"]} -> symbol IN (...)"""
        conditions = []
        for column_name, value in filters.items():
            if column_name not in Trades.__mapper__.column_attrs:
                raise ValueError(f"Unknown Trades column: {column_name}")
            column = getattr(Trades, column_name)
            if isinstance(value, (list, tuple, set)):
                conditions.append(column.in_(value))
            else:
                conditions.append(column == value)
        return conditions

    def get_all_active_trades(self, asset_class, **filters):
        """Active trades of an asset class; with extra filters (e.g. symbol=...) queries the DB directly"""
        if not filters:
            return self.active_trades_cache.get(asset_class)
        conditions = (*ACTIVE, Trades.asset_class == asset_class, *self._filter_conditions(filters))
        return self._query_trades(conditions)

    def get_closed_trades(self, asset_class, **filters):
        """Closed trades that have not yet received their post-close realized PnL valuation"""
        if not filters:
            return self.closed_trades_cache.get(asset_class)
        conditions = (*CLOSED_NOT_SETTLED, Trades.asset_class == asset_class, *self._filter_conditions(filters))
        return self._query_trades(conditions)

    def settle_trade(self, data):
        """Store the final realized-PnL valuation and mark the trade settled in one transaction (bypasses the buffer)"""
        self._store([data], settle_trade_id=data["trade_id"])

    def _query_valuations(self, max_rows, *conditions):
        with SessionFactory() as session:
            query = (
                session.query(Valuations)
                .filter(*conditions)
                .order_by(Valuations.valuation_time.desc())
                .limit(max_rows)
            )
            return [self._valuation_to_dict(record) for record in query]

    # Materialized here because api.py serializes the result to JSON (Bottle can't serialize generators)
    def get_all_valuations(self):
        """Latest valuations, served from ValuationCache"""
        return list(self.valuation_cache.latest())

    def get_valuation_by_trade_id(self, trade_id):
        """Latest valuations of a trade, served from ValuationCache"""
        return list(self.valuation_cache.by_trade_id(trade_id))

    @staticmethod
    def _valuation_to_dict(record):
        return {
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
