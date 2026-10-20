import random
import uuid
import datetime
import structlog


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _client_request_id() -> str:
    return f"req-{uuid.uuid4()}"


class TradeGenerator:
    """Base OPEN_TRADE payload generator for a single instrument; subclasses override class attributes / hooks"""
    asset_class: str
    symbol: str
    price_field = "mid"
    sides = ("BUY",)
    currency = "USD"
    max_quantity = 1000

    def __init__(self, market_data_client, book_client):
        self.market_data_client = market_data_client
        self.book_client = book_client
        self.log = structlog.get_logger().bind(asset_class=self.asset_class)

    @property
    def market_data_key(self) -> tuple:
        return self.asset_class, self.symbol

    def generate(self) -> dict | None:
        price = self._trade_price()
        if price is None:
            return None

        book = self.book_client.get_book_for_asset_class(self.asset_class)
        if not book:
            return None

        trade = self._build_trade(price, book["book_id"])
        self.log.info("generated_trade", data=trade)
        return trade

    def _trade_price(self) -> float | None:
        tick = self.market_data_client.get_price(self.market_data_key)
        return tick.get(self.price_field) if tick else None

    def _build_trade(self, price: float, book_id) -> dict:
        return {
            "asset_class": self.asset_class,
            **self._instrument_fields(price),
            "side": random.choice(self.sides),
            "quantity": random.randint(1, self.max_quantity),
            "trade_price": price,
            "trade_currency": self.currency,
            "book_id": book_id,
            "trade_date": _utc_now(),
        }

    def _instrument_fields(self, price: float) -> dict:
        return {"symbol": self.symbol, "instrument_id": self.symbol}


class EquityTradeGenerator(TradeGenerator):
    asset_class = "EQUITY"
    symbol = "ACME"
    sides = ("BUY", "SELL")


class FixedIncomeTradeGenerator(TradeGenerator):
    asset_class = "BOND"
    symbol = "GOVT"
    price_field = "face_value"


class ForexTradeGenerator(TradeGenerator):
    asset_class = "FX"
    symbol = "EUR/USD"


class CommodityTradeGenerator(TradeGenerator):
    asset_class = "COMMODITY"
    symbol = "XAU/USD"


class FuturesTradeGenerator(TradeGenerator):
    asset_class = "FUTURES"
    symbol = "OIL"


class EUOptionTradeGenerator(TradeGenerator):
    """Option on the equity underlying; price comes from the underlying tick, payload has no `symbol`"""
    asset_class = "EUROPEAN_OPTION"
    underlying_symbol = EquityTradeGenerator.symbol
    sides = ("BUY", "SELL")
    option_types = ("CALL", "PUT")
    strike_moneyness = (0.9, 1.0, 1.1)
    maturities_years = (0.25, 0.5, 1.0)

    @property
    def market_data_key(self) -> tuple:
        return EquityTradeGenerator.asset_class, self.underlying_symbol

    def _trade_price(self) -> float | None:
        price = super()._trade_price()
        return round(price, 1) if price is not None else None

    def _instrument_fields(self, price: float) -> dict:
        strike = round(price * random.choice(self.strike_moneyness), 1)
        maturity_years = random.choice(self.maturities_years)
        return {
            "underlying_symbol": self.underlying_symbol,
            "option_type": random.choice(self.option_types),
            "strike": strike,
            "volatility": round(random.uniform(0.1, 0.5), 2),
            "maturity_years": maturity_years,
            "instrument_id": f"{self.underlying_symbol}_EU_OPTION_{strike}_{maturity_years}",
        }


class IRSTradeGenerator(TradeGenerator):
    asset_class = "INTEREST_RATE_SWAP"
    # TODO: no IRS market data / trade fields yet - payload carries only asset_class

    def generate(self) -> dict | None:
        trade = {"asset_class": self.asset_class}
        self.log.info("generated_trade", data=trade)
        return trade


class TradeActionGenerator:
    """Randomly produces OPEN_TRADE (via instrument generators) or CLOSE_TRADE actions"""

    def __init__(self, trade_generators: list[TradeGenerator], market_data_client, blotter_client):
        self.trade_generators = trade_generators
        self.market_data_client = market_data_client
        self.blotter_client = blotter_client
        self.log = structlog.get_logger()

    def generate_trade_action(self, close_probability: float = 0.3, max_active_trades: int | None = None) -> dict | None:
        if max_active_trades is not None and self._active_limit_reached(max_active_trades):
            return self.trade_out()

        if random.random() < close_probability:
            closing_trade = self.trade_out()
            if closing_trade:
                return closing_trade

        return self.trade_in()

    def _active_limit_reached(self, max_active_trades: int) -> bool:
        active_trades = self.blotter_client.get_active_trades(limit=max_active_trades)
        if len(active_trades) >= max_active_trades:
            self.log.info("max_active_trades_reached", max_active_trades=max_active_trades)
            return True
        return False

    def trade_in(self) -> dict | None:
        trade = random.choice(self.trade_generators).generate()
        if not trade:
            return None

        return {**trade, "action_type": "OPEN_TRADE", "client_request_id": _client_request_id()}

    def trade_out(self) -> dict | None:
        active_trade = self.blotter_client.get_random_active_trade()
        if not active_trade:
            self.log.warning("no_active_trades_to_close")
            return None

        tick = self.market_data_client.get_price((active_trade["asset_class"], active_trade["symbol"]))
        if not tick:
            return None

        return {
            "action_type": "CLOSE_TRADE",
            "client_request_id": _client_request_id(),
            "trade_id": active_trade["trade_id"],
            "close_price": tick.get("mid") or tick.get("face_value"),
            "closed_at": _utc_now(),
            "close_reason": "RANDOM_TRADE_OUT",
        }
