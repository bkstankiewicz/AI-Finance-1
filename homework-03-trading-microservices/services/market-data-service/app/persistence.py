import sys
from contextlib import contextmanager
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import MarketDataSpotPrices, MarketDataCurves, MarketDataSnapshots
from sqlalchemy import func, or_, select
import threading
import structlog

from config import TICK_BUFFER_SIZE, SNAPSHOT_BUFFER_SIZE, CURVE_BUFFER_SIZE


class Buffer:
    """Thread-safe bounded buffer; when full, the oldest items are dropped"""

    def __init__(self, max_size: int):
        self._items = []
        self._max_size = max_size
        self._lock = threading.Lock()

    def add(self, item) -> None:
        with self._lock:
            self._items.append(item)
            self._items = self._items[-self._max_size:]

    @contextmanager
    def drain(self):
        """Yield buffered items; put them back if the block raises (e.g. DB write failed)"""
        with self._lock:
            items, self._items = self._items, []
        try:
            yield items
        except Exception:
            with self._lock:
                self._items = (items + self._items)[-self._max_size:]
            raise


class Persistence:
    def __init__(self):
        self.log = structlog.get_logger()
        self.ticks = Buffer(TICK_BUFFER_SIZE)
        self.snapshots = Buffer(SNAPSHOT_BUFFER_SIZE)
        self.curves = Buffer(CURVE_BUFFER_SIZE)

    def add_ticks(self, data):
        self.ticks.add(data)

    def add_snapshot(self, data):
        self.snapshots.add(data)

    def add_curve(self, data):
        self.curves.add(data)

    def push_ticks(self):
        """Push tick data from the buffer to the database"""
        with self.ticks.drain() as ticks, SessionFactory() as session:
            for data in ticks:
                session.add(MarketDataSpotPrices(
                    event_id=data["event_id"],
                    symbol=data["symbol"],
                    asset_class=data["asset_class"],
                    bid=data.get("bid"),
                    ask=data.get("ask"),
                    mid=data.get("mid"),
                    last=data.get("last"),
                    spot=data.get("spot"),
                    currency=data.get("currency"),
                    source=data.get("source", "SIMULATED"),
                    event_time=data["timestamp"],
                    raw_payload=data
                ))
            session.commit()

    def push_snapshots(self):
        """Push snapshot data from the buffer to the database"""
        with self.snapshots.drain() as snapshots, SessionFactory() as session:
            for data in snapshots:
                session.add(MarketDataSnapshots(
                    event_id=data["event_id"],
                    snapshot_type=data["snapshot_type"],
                    snapshot_time=data["snapshot_time"],
                    payload=dict(data)
                ))
            session.commit()

    def push_curves(self):
        """Push curve data from the buffer to the database"""
        with self.curves.drain() as curves, SessionFactory() as session:
            for data in curves:
                session.add(MarketDataCurves(
                    event_id=data["event_id"],
                    curve_name=data["curve_name"],
                    curve_type=data["curve_type"],
                    currency=data.get("currency"),
                    tenors=data["tenors"],
                    rates=data["rates"],
                    event_time=data["timestamp"],
                    raw_payload=data,
                ))
            session.commit()

    def get_last_event_id(self):
        """Get the last event ID"""
        with SessionFactory() as session:
            max_event_id = max(
                session.query(func.max(MarketDataSpotPrices.event_id)).scalar() or 0,
                session.query(func.max(MarketDataCurves.event_id)).scalar() or 0,
            )
            self.log.info("last_event_id_loaded", event_id=max_event_id)
            return max_event_id

    def get_last_quote(self, symbol: str) -> dict | None:
        """Most recent persisted quote payload for `symbol` (None if nothing stored yet)"""
        with SessionFactory() as session:
            return session.scalar(
                select(MarketDataSpotPrices.raw_payload)
                .where(MarketDataSpotPrices.symbol == symbol)
                .order_by(MarketDataSpotPrices.event_id.desc().nulls_last())
                .limit(1)
            )

    def get_history(self, limit):
        """Last `limit` persisted spot prices (bonds: yield) per symbol, oldest first"""
        # Bond yield has no own column - it lives only in raw_payload
        bond_yield = MarketDataSpotPrices.raw_payload["yield"].as_float()
        with SessionFactory() as session:
            ranked = (
                session.query(
                    MarketDataSpotPrices.symbol,
                    MarketDataSpotPrices.event_id,
                    MarketDataSpotPrices.event_time,
                    MarketDataSpotPrices.spot,
                    bond_yield.label("yield_"),
                    func.row_number().over(
                        partition_by=MarketDataSpotPrices.symbol,
                        order_by=MarketDataSpotPrices.event_id.desc(),
                    ).label("rn"),
                )
                .filter(
                    or_(MarketDataSpotPrices.spot.isnot(None), bond_yield.isnot(None)),
                    MarketDataSpotPrices.event_id.isnot(None),
                )
                .subquery()
            )

            rows = (
                session.query(ranked.c.symbol, ranked.c.event_id, ranked.c.event_time, ranked.c.spot, ranked.c.yield_)
                .filter(ranked.c.rn <= limit)
                .order_by(ranked.c.symbol, ranked.c.event_id)
                .all()
            )

            history = {}
            for row in rows:
                point = {"event_id": row.event_id, "timestamp": row.event_time.isoformat()}
                if row.spot is not None:
                    point["spot"] = float(row.spot)
                else:
                    point["yield"] = row.yield_
                history.setdefault(row.symbol, []).append(point)

        return history
