import random
import uuid
import datetime
import structlog


class TradeGenerator:
    def __init__(self, market_data_client, book_client, blotter_client):
        self.market_data_client = market_data_client
        self.book_client = book_client
        self.blotter_client = blotter_client
        self.log = structlog.get_logger().bind(service="trade-generation-service")

    def trade_in(self):
        """Generate a trade with random parameters"""
        generate_trade = random.choice([
            self.generate_equity_trade,
            self.generate_fixed_income_trade,
            self.generate_forex_trade,
            self.generate_commodity_trade,
            self.generate_futures_trade
        ])

        generated_trade = generate_trade()
        if not generated_trade:
            return None

        generated_trade["action_type"] = "OPEN_TRADE"
        generated_trade["client_request_id"] = f"req-{uuid.uuid4()}"
        return generated_trade

    def generate_trade_action(self, close_probability=0.3):
        """Randomly decide whether to open a new trade or close an existing one"""
        if random.random() < close_probability:
            closing_trade = self.trade_out()
            if closing_trade:
                return closing_trade

        return self.trade_in()

    def trade_out(self):
        """Generate a trade closure with random parameters"""
        active_trade = self.blotter_client.get_random_active_trade()
        if not active_trade:
            self.log.warning("no_active_trades_to_close")
            return None

        tick = self.market_data_client.get_price((active_trade["asset_class"], active_trade["symbol"]))
        if not tick:
            return None
        close_price = tick.get("mid")

        data = {
            "action_type": "CLOSE_TRADE",
            "client_request_id": f"req-{uuid.uuid4()}",
            "trade_id": active_trade["trade_id"],
            "close_price": close_price,
            "closed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "close_reason": "RANDOM_TRADE_OUT"
        }
        return data

    def generate_equity_trade(self):
        """Generate a trade for the equity asset class"""
        equity_descrption = ("EQUITY", "ACME")
        quantity = random.randint(1, 1000)
        trade_data = self.market_data_client.get_price(equity_descrption)
        if not trade_data:
            return None
        trade_price = trade_data.get("mid")

        book = self.book_client.get_book_for_asset_class("EQUITY")
        if not book:
            return None

        data = {
            "asset_class": "EQUITY",
            "symbol": "ACME",
            "side": random.choice(["BUY", "SELL"]),
            "quantity": quantity,
            "trade_price": trade_price,
            "trade_currency": "USD",
            "book_id": book["book_id"],
            "instrument_id": "ACME",
            "trade_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.log.info("generated_equity_trade", data=data)
        return data

    def generate_fixed_income_trade(self):
        """Generate a trade for the fixed income asset class"""
        fixed_income_description = ("BOND", "GOVT")
        quantity = random.randint(1, 1000)
        trade_data = self.market_data_client.get_price(fixed_income_description)
        if not trade_data:
            return None
        trade_price = trade_data.get("mid")

        book = self.book_client.get_book_for_asset_class("BOND")
        if not book:
            return None

        data = {
            "asset_class": "BOND",
            "symbol": "GOVT",
            "side": "BUY",
            "quantity": quantity,
            "trade_price": trade_price,
            "trade_currency": "USD",
            "book_id": book["book_id"],
            "instrument_id": "GOVT",
            "trade_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.log.info("generated_fixed_income_trade", data=data)
        return data

    def generate_forex_trade(self):
        """Generate a trade for the forex asset class"""
        fx_description = ("FX", "EUR/USD")
        quantity = random.randint(1, 1000)
        trade_data = self.market_data_client.get_price(fx_description)
        if not trade_data:
            return None
        trade_price = trade_data.get("mid")

        book = self.book_client.get_book_for_asset_class("FX")
        if not book:
            return None

        data = {
            "asset_class": "FX",
            "symbol": "EUR/USD",
            "side": "BUY",
            "quantity": quantity,
            "trade_price": trade_price,
            "trade_currency": "USD",
            "book_id": book["book_id"],
            "instrument_id": "EUR/USD",
            "trade_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.log.info("generated_forex_trade", data=data)
        return data

    def generate_commodity_trade(self):
        """Generate a trade for the commodity asset class"""
        commodity_description = ("COMMODITY", "XAU/USD")
        quantity = random.randint(1, 1000)
        trade_data = self.market_data_client.get_price(commodity_description)
        if not trade_data:
            return None
        trade_price = trade_data.get("mid")

        book = self.book_client.get_book_for_asset_class("COMMODITY")
        if not book:
            return None

        data = {
            "asset_class": "COMMODITY",
            "symbol": "XAU/USD",
            "side": "BUY",
            "quantity": quantity,
            "trade_price": trade_price,
            "trade_currency": "USD",
            "book_id": book["book_id"],
            "instrument_id": "XAU/USD",
            "trade_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.log.info("generated_commodity_trade", data=data)
        return data

    def generate_futures_trade(self):
        """Generate a trade for the futures asset class"""
        futures_description = ("FUTURES", "OIL")
        quantity = random.randint(1, 1000)
        trade_data = self.market_data_client.get_price(futures_description)
        if not trade_data:
            return None
        trade_price = trade_data.get("mid")

        book = self.book_client.get_book_for_asset_class("FUTURES")
        if not book:
            return None

        data = {
            "asset_class": "FUTURES",
            "symbol": "OIL",
            "side": "BUY",
            "quantity": quantity,
            "trade_price": trade_price,
            "trade_currency": "USD",
            "book_id": book["book_id"],
            "instrument_id": "OIL",
            "trade_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.log.info("generated_futures_trade", data=data)
        return data
