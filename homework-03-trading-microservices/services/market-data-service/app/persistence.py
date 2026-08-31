from copy import deepcopy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.trading_shared.db import SessionFactory
from shared.trading_shared.models import MarketDataSpotPrices, MarketDataCurves, MarketDataSnapshots
from sqlalchemy import func
import threading


class Persistence:
    def __init__(self):
        self.tick_buffer = []
        self.snapshot_buffer = []
        self.curve_buffer = []
        self.tick_lock = threading.Lock()
        self.snapshot_lock = threading.Lock()
        self.curve_lock = threading.Lock()

    def add_ticks(self, data):
        """Add tick data to the buffer"""
        with self.tick_lock:
            self.tick_buffer.append(data)

    def add_snapshot(self, data):
        """Add snapshot data to the buffer"""
        with self.snapshot_lock:
            self.snapshot_buffer.append(data)

    def add_curve(self, data):
        """Add curve data to the buffer"""
        with self.curve_lock:
            self.curve_buffer.append(data)

    def push_ticks(self):
        """Push tick data from the buffer to the database"""
        with self.tick_lock:
            ticks = deepcopy(self.tick_buffer)
            self.tick_buffer.clear()

        with SessionFactory() as session:
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
        with self.snapshot_lock:
            snapshots = deepcopy(self.snapshot_buffer)
            self.snapshot_buffer.clear()

        with SessionFactory() as session:
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
        with self.curve_lock:
            curves = deepcopy(self.curve_buffer)
            self.curve_buffer.clear()

        with SessionFactory() as session:
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
            max_event_id = session.query(func.max(MarketDataSpotPrices.event_id)).scalar()
            if max_event_id is None:
                max_event_id = 0
            print(f"Last event ID from DB: {max_event_id}")
            return max_event_id
