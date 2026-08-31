import random
import threading
import datetime
import structlog

class Generator:
    def __init__(self, event_id):
        self.log = structlog.get_logger().bind(service="market-data-service")
        self.last_equity_price = 100.0
        self.last_fixed_income_price = 100.0
        self.last_forex_spot = 1.2
        self.last_commodity_price = 2000.0
        self.last_futures_price = 100.0
        self.event_id = event_id
        self.lock = threading.Lock()

    def next_event_id(self):
        """Generate the next event ID in a thread-safe manner"""
        with self.lock:
            self.event_id += 1
            return self.event_id

    def generate_tick(self, last_price, asset_class):
        """Generate a new tick based on the last price"""
        decimal_places = 4 if asset_class in ["FOREX"] else 2

        ticks = round(random.uniform(-0.01, 0.01), 4)
        actual_price = round(last_price * (1 + ticks), decimal_places)
        half_spread = round(actual_price * random.uniform(0.0002, 0.001) / 2, decimal_places)
        bid = round(actual_price - half_spread, decimal_places)
        ask = round(actual_price + half_spread, decimal_places)
        mid = round((bid + ask) / 2, decimal_places)

        return actual_price, bid, ask, mid

    def generate_equity_data(self):
        """Generate equity market data"""
        actual_price, bid, ask, mid = self.generate_tick(self.last_equity_price, "EQUITY")
        last_event_time = datetime.datetime.now().isoformat()

        data = {
            "event_id": self.next_event_id(),
            "timestamp": last_event_time,
            "asset_class": "EQUITY",
            "symbol": "ACME",
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spot": actual_price,
            "last": self.last_equity_price,
            "currency": "USD",
            "snapshot_type": "EQUITY_DATA_SNAPSHOT",
            "snapshot_time": last_event_time
        }
        self.last_equity_price = actual_price
        self.log.info("generated_equity_data", data=data)
        return data

    def generate_fixed_income_data(self):
        """Generate fixed income market data"""
        yield_rate = round(random.uniform(0.03, 0.06), 3)
        actual_price, bid, ask, mid = self.generate_tick(self.last_fixed_income_price, "FIXED_INCOME")
        last_event_time = datetime.datetime.now().isoformat()

        data = {
            "event_id": self.next_event_id(),
            "timestamp": last_event_time,
            "asset_class": "FIXED_INCOME",
            "symbol": "GOVT",
            "yield": yield_rate,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spot": actual_price,
            "last": self.last_fixed_income_price,
            "currency": "USD",
            "snapshot_type": "FIXED_INCOME_DATA_SNAPSHOT",
            "snapshot_time": last_event_time
        }
        self.last_fixed_income_price = actual_price
        self.log.info("generated_fixed_income_data", data=data)
        return data

    def generate_forex_data(self):
        """Generate forex market data"""
        domestic_rate = round(random.uniform(0.01, 0.05), 4)
        foreign_rate = round(random.uniform(0.01, 0.05), 4)
        actual_price, bid, ask, mid = self.generate_tick(self.last_forex_spot, "FOREX")
        last_event_time = datetime.datetime.now().isoformat()

        data = {
            "event_id": self.next_event_id(),
            "timestamp": last_event_time,
            "asset_class": "FOREX",
            "symbol": "EUR/USD",
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spot": actual_price,
            "last": self.last_forex_spot,
            "domestic_rate": domestic_rate,
            "foreign_rate": foreign_rate,
            "currency": "USD",
            "snapshot_type": "FOREX_DATA_SNAPSHOT",
            "snapshot_time": last_event_time
        }
        self.last_forex_spot = actual_price
        self.log.info("generated_forex_data", data=data)
        return data

    def generate_commodity_data(self):
        """Generate commodity market data"""
        actual_price, bid, ask, mid = self.generate_tick(self.last_commodity_price, "COMMODITY")
        last_event_time = datetime.datetime.now().isoformat()

        data = {
            "event_id": self.next_event_id(),
            "timestamp": last_event_time,
            "asset_class": "COMMODITY",
            "symbol": "XAU/USD",
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spot": actual_price,
            "last": self.last_commodity_price,
            "currency": "USD",
            "snapshot_type": "COMMODITY_DATA_SNAPSHOT",
            "snapshot_time": last_event_time
        }
        self.last_commodity_price = actual_price
        self.log.info("generated_commodity_data", data=data)
        return data

    def generate_futures_data(self):
        """Generate futures market data"""
        actual_price, bid, ask, mid = self.generate_tick(self.last_futures_price, "FUTURES")
        last_event_time = datetime.datetime.now().isoformat()

        data = {
            "event_id": self.next_event_id(),
            "timestamp": last_event_time,
            "asset_class": "FUTURES",
            "symbol": "OIL",
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spot": actual_price,
            "last": self.last_futures_price,
            "currency": "USD",
            "snapshot_type": "FUTURES_DATA_SNAPSHOT",
            "snapshot_time": last_event_time
        }
        self.last_futures_price = actual_price
        self.log.info("generated_futures_data", data=data)
        return data
