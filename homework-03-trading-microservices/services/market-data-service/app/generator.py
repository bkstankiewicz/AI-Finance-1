import random
import threading
import datetime
import structlog
from config import SERVICE_NAME
from persistence import Persistence

# Rates curve (bonds, IRS) - tenors in years; yearly points up to 5Y cover annual IRS payments
RATE_TENORS = {"1Y": 1, "2Y": 2, "3Y": 3, "4Y": 4, "5Y": 5, "7Y": 7, "10Y": 10, "20Y": 20, "30Y": 30}
USD_BASE_RATES = [0.038, 0.040, 0.041, 0.0415, 0.042, 0.0425, 0.043, 0.044, 0.045]

# FX forward curve - tenors in months
FX_TENORS = {"1M": 1 / 12, "3M": 0.25, "6M": 0.5, "9M": 0.75, "1Y": 1.0}


def _bounded_walk(value: float, step_std: float, low: float, high: float, decimals: int = 4) -> float:
    return round(min(max(value + random.gauss(0, step_std), low), high), decimals)


class EventIdSequence:
    def __init__(self, start: int):
        self._value = start
        self._lock = threading.Lock()

    @classmethod
    def from_db(cls, db: Persistence) -> "EventIdSequence":
        return cls(db.get_last_event_id())

    def __iter__(self):
        return self

    def __next__(self) -> int:
        with self._lock:
            self._value += 1
            return self._value


class MarketDataGenerator:
    asset_class: str
    symbol: str
    currency = "USD"
    initial_price = 0.0
    decimal_places = 2

    def __init__(self, ids: EventIdSequence, db: Persistence):
        self.event_id = ids
        self.log = structlog.get_logger().bind(asset_class=self.asset_class)
        self._restore_state(db.get_last_quote(self.symbol) or {})

    @property
    def snapshot_type(self) -> str:
        return f"{self.asset_class}_DATA_SNAPSHOT"

    def generate(self) -> dict:
        quote = self._build_quote(self._event_time())
        self._log_validation_errors(quote)
        self.log.info("generated_market_data", data=quote)
        return quote

    def _restore_state(self, last_quote: dict) -> None:
        """Continue the random walk from the last persisted quote instead of the initial value"""
        self.last_price = last_quote.get("spot") or self.initial_price

    def _build_quote(self, event_time: str) -> dict:
        return {
            "event_id": next(self.event_id),
            "timestamp": event_time,
            "asset_class": self.asset_class,
            "symbol": self.symbol,
            "currency": self.currency,
            **self._price_fields(),
            **self._extra_fields(),
            "snapshot_type": self.snapshot_type,
            "snapshot_time": event_time,
        }

    def _price_fields(self) -> dict:
        """Default: random-walk price quoted in currency"""
        price = self._next_price()
        fields = {**self._two_sided_quote(price), "spot": price, "last": self.last_price}
        self.last_price = price
        return fields

    def _next_price(self) -> float:
        return round(self.last_price * (1 + random.uniform(-0.01, 0.01)), self.decimal_places)

    def _two_sided_quote(self, price: float) -> dict:
        dp = self.decimal_places
        half_spread = round(price * random.uniform(0.0002, 0.001) / 2, dp)
        bid = round(price - half_spread, dp)
        ask = round(price + half_spread, dp)
        return {"bid": bid, "ask": ask, "mid": round((bid + ask) / 2, dp)}

    def _extra_fields(self) -> dict:
        return {}

    def _log_validation_errors(self, quote: dict) -> None:
        errors = self._validate_quote(quote)
        if errors:
            self.log.error("invalid_quote", errors=errors)

    @staticmethod
    def _validate_quote(quote) -> list[str]:
        # Not every instrument has a two-sided quote (bond, option)
        if "bid" not in quote or "ask" not in quote:
            return []

        errors = []
        if quote["bid"] <= 0:
            errors.append("Bid must be positive")
        if quote["ask"] <= 0:
            errors.append("Ask must be positive")
        if quote["bid"] > quote["ask"]:
            errors.append("Bid cannot be greater than ask")
        return errors

    @staticmethod
    def _event_time() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()


class EquityMarketDataGenerator(MarketDataGenerator):
    asset_class = "EQUITY"
    symbol = "ACME"
    initial_price = 100.0


class FixedIncomeMarketDataGenerator(MarketDataGenerator):
    """Bond market inputs: face value + yield; PV (fair value) is computed in pricing-service"""
    asset_class = "FIXED_INCOME"
    symbol = "GOVT"
    currency = "PERCENT_OF_PAR"
    initial_price = 100.0
    initial_yield = 0.043

    def _restore_state(self, last_quote: dict) -> None:
        self.last_price = last_quote.get("face_value") or self.initial_price
        self.yield_rate = last_quote.get("yield") or self.initial_yield

    def _price_fields(self) -> dict:
        self.last_price = self._next_price()
        last_yield = self.yield_rate
        self.yield_rate = _bounded_walk(self.yield_rate, 0.0005, 0.001, 0.15, decimals=5)
        return {"face_value": self.last_price, "yield": self.yield_rate, "last_yield": last_yield}


class ForexMarketDataGenerator(MarketDataGenerator):
    asset_class = "FOREX"
    symbol = "EUR/USD"
    initial_price = 1.2
    decimal_places = 4
    initial_domestic_rate = 0.043  # USD (quote currency)
    initial_foreign_rate = 0.025   # EUR (base currency)
    rate_step = 0.0001             # ~1bp std per tick

    def _restore_state(self, last_quote: dict) -> None:
        super()._restore_state(last_quote)
        self.domestic_rate = last_quote.get("domestic_rate", self.initial_domestic_rate)
        self.foreign_rate = last_quote.get("foreign_rate", self.initial_foreign_rate)

    def _extra_fields(self) -> dict:
        self.domestic_rate = _bounded_walk(self.domestic_rate, self.rate_step, 0.0, 0.10, decimals=5)
        self.foreign_rate = _bounded_walk(self.foreign_rate, self.rate_step, 0.0, 0.10, decimals=5)
        return {"domestic_rate": self.domestic_rate, "foreign_rate": self.foreign_rate}


class FuturesMarketDataGenerator(MarketDataGenerator):
    asset_class = "FUTURES"
    symbol = "OIL"
    initial_price = 100.0


class CommodityMarketDataGenerator(MarketDataGenerator):
    asset_class = "COMMODITY"
    symbol = "XAU/USD"
    initial_price = 2000.0


class EUOptionMarketDataGenerator(MarketDataGenerator):
    """Option-only inputs (sigma, q); pricing takes spot from the ACME tick and r from USD_YIELD"""
    asset_class = "EUROPEAN_OPTION"
    underlying_symbol = EquityMarketDataGenerator.symbol
    symbol = f"{underlying_symbol}_EU_OPTION"
    long_run_volatility = 0.25
    initial_dividend_yield = 0.02

    def _restore_state(self, last_quote: dict) -> None:
        super()._restore_state(last_quote)
        self.volatility = last_quote.get("volatility") or self.long_run_volatility
        self.dividend_yield = last_quote.get("dividend_yield", self.initial_dividend_yield)

    def _price_fields(self) -> dict:
        return {}

    def _extra_fields(self) -> dict:
        pull = 0.05 * (self.long_run_volatility - self.volatility)
        self.volatility = _bounded_walk(self.volatility + pull, 0.005, 0.05, 1.0)
        self.dividend_yield = _bounded_walk(self.dividend_yield, 0.0002, 0.0, 0.10)
        return {
            "underlying_symbol": self.underlying_symbol,
            "volatility": self.volatility,
            "dividend_yield": self.dividend_yield,
        }


class IRSMarketDataGenerator(MarketDataGenerator):
    asset_class = "INTEREST_RATE_SWAP"
    # TODO
    symbol = "???"

class CurveGenerator:
    def __init__(self, ids: EventIdSequence, fx: ForexMarketDataGenerator):
        self.event_id = ids
        self.fx = fx
        self.log = structlog.get_logger().bind(service=SERVICE_NAME)

    def generate(self) -> list[dict]:
        """Generate USD yield/discount curves and EUR/USD forward curve (on startup / on demand)"""
        event_time = MarketDataGenerator._event_time()

        shift = random.uniform(-0.005, 0.005)
        yields = [round(r + shift, 5) for r in USD_BASE_RATES]
        discount_factors = [round(1 / (1 + r) ** t, 6) for r, t in zip(yields, RATE_TENORS.values())]

        spot = self.fx.last_price
        domestic_rate = self.fx.domestic_rate
        foreign_rate = self.fx.foreign_rate
        forwards = [
            round(spot * (1 + domestic_rate * t) / (1 + foreign_rate * t), 5)
            for t in FX_TENORS.values()
        ]

        curves = [
            self._build_curve(
                "USD_YIELD", "YIELD_CURVE", "USD", RATE_TENORS, yields, event_time,
                compounding="ANNUAL",
            ),
            self._build_curve(
                "USD_DISCOUNT", "DISCOUNT_CURVE", "USD", RATE_TENORS, discount_factors, event_time,
                compounding="ANNUAL", source_curve="USD_YIELD",
            ),
            self._build_curve(
                "EUR/USD_FWD", "FX_FORWARD_CURVE", "USD", FX_TENORS, forwards, event_time,
                pair="EUR/USD", spot=spot, domestic_rate=domestic_rate, foreign_rate=foreign_rate,
                forward_points=[round((f - spot) * 10000, 1) for f in forwards],
            ),
        ]

        self.log.info("generated_curves", curves=[c["curve_name"] for c in curves])
        return curves

    def _build_curve(self, curve_name, curve_type, currency, tenors: dict, rates, event_time, **extra) -> dict:
        return {
            "event_type": "CURVE",
            "event_id": next(self.event_id),
            "timestamp": event_time,
            "curve_name": curve_name,
            "curve_type": curve_type,
            "currency": currency,
            "tenors": list(tenors.keys()),
            "year_fractions": [round(t, 6) for t in tenors.values()],
            "rates": rates,
            **extra,
        }
