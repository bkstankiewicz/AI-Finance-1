import structlog


class PnLService():
    def __init__(self, valuation_engine):
        self.log = structlog.get_logger().bind(service="pricing-service")
        self.valuation_engine = valuation_engine
        self.multiplier = 1.0

    def get_basic_values(self, trade):
        """Extract basic values from a trade dictionary"""
        quantity = trade.get("quantity")
        trade_price = trade.get("trade_price")
        side = trade.get("side")

        return (quantity, trade_price, side)

    def calculate_fx_forward(self, spot, domestic_rate, foreign_rate, time_years):
        """Calculate the forward price for a forex trade"""
        domestic_growth = 1 + domestic_rate * time_years
        foreign_growth = 1 + foreign_rate * time_years

        return spot * domestic_growth / foreign_growth

    def calculate_pv(self, face_value, coupon, yield_rate, maturity_years):
        """Calculate the present value of a series of cash flows"""
        pv = 0.0
        for i in range(1, maturity_years + 1):
            pv += coupon / (1 + yield_rate) ** i
        pv += (coupon + face_value) / (1 + yield_rate) ** maturity_years

        return pv

    def calculate_pnl(self, position, reference_price, trade_price, quantity):
        """Calculate PnL between a reference price and the trade price (used for both unrealized and realized PnL)"""
        if position == "BUY":
            pnl = (reference_price - trade_price) * quantity * self.multiplier
        else:
            pnl = (trade_price - reference_price) * quantity * self.multiplier

        return round(pnl, 2)

    def calculate_closed_positions(self, asset_class):
        """Calculate the one-time realized PnL for trades closed since the last valuation cycle"""
        results = []
        close_trades = self.valuation_engine.get_closed_trades(asset_class)

        for trade in close_trades:
            quantity, trade_price, side = self.get_basic_values(trade)
            close_price = trade.get("close_price")
            if close_price is None:
                continue

            realized_pnl = self.calculate_pnl(side, close_price, trade_price, quantity)
            data = {
                "trade_id": trade.get("trade_id"),
                "book_id": trade.get("book_id"),
                "asset_class": asset_class,
                "symbol": trade.get("symbol"),
                "fair_value": round(close_price * quantity, 2),
                "unrealized_pnl": 0.0,
                "realized_pnl": realized_pnl,
                "total_pnl": realized_pnl,
                "currency": trade.get("trade_currency"),
            }
            self.log.info("calculated_closed_pnl", trade_id=trade.get("trade_id"), data=data)
            self.valuation_engine.mark_trade_settled(trade.get("trade_id"))
            results.append(data)
        return results

    def calculate_equity(self):
        """Calculate PnL for all active equity trades"""
        asset_class = "EQUITY"
        results = []
        data = {}
        active_trades = self.valuation_engine.get_active_trades(asset_class)

        for trade in active_trades:
            symbol = trade.get("symbol")
            ticks = self.valuation_engine.get_current_tick(symbol)
            quantity, trade_price, side = self.get_basic_values(trade)

            current_price = ticks.get("mid") or ticks.get("last")
            fair_value = current_price * quantity

            unrealized_pnl = self.calculate_pnl(side, current_price, trade_price, quantity)
            data = {
                "trade_id": trade.get("trade_id"),
                "book_id": trade.get("book_id"),
                "asset_class": asset_class,
                "symbol": symbol,
                "fair_value": round(fair_value, 2),
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": 0.0,
                "total_pnl": unrealized_pnl,
                "currency": trade.get("trade_currency"),
            }
            results.append(data)
            self.log.info("calculated_equity_pnl", trade_id=trade.get("trade_id"), data=data)
        return results

    def calculate_fixed_income(self):
        """Calculate PnL for all active fixed income trades"""
        asset_class = "BOND"
        results = []
        coupon_rate = 0.05
        time_years = 5
        active_trades = self.valuation_engine.get_active_trades(asset_class)    

        for trade in active_trades:
            symbol = trade.get("symbol")
            ticks = self.valuation_engine.get_current_tick(symbol)
            quantity, trade_price, side = self.get_basic_values(trade)

            face_value = ticks.get("mid")
            coupon = face_value * coupon_rate
            yield_rate = ticks.get("yield")

            fair_value = self.calculate_pv(face_value, coupon, yield_rate, time_years) * quantity
            unrealized_pnl = self.calculate_pnl(side, face_value, trade_price, quantity)
            data = {
                "trade_id": trade.get("trade_id"),
                "book_id": trade.get("book_id"),
                "asset_class": asset_class,
                "symbol": symbol,
                "fair_value": round(fair_value, 2),
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": 0.0,
                "total_pnl": unrealized_pnl,
                "currency": trade.get("trade_currency"),
            }
            self.log.info("calculated_fixed_income_pnl", trade_id=trade.get("trade_id"), data=data)
            results.append(data)
        return results

    def calculate_forex(self):
        """Calculate PnL for all active forex trades"""
        asset_class = "FX"
        results = []
        data = {}
        active_trades = self.valuation_engine.get_active_trades(asset_class)

        for trade in active_trades:
            symbol = trade.get("symbol")
            ticks = self.valuation_engine.get_current_tick(symbol)
            quantity, trade_price, side = self.get_basic_values(trade)

            spot = ticks.get("spot")
            domestic_rate = ticks.get("domestic_rate")
            foreign_rate = ticks.get("foreign_rate")
            time_years = 0.5

            forward = self.calculate_fx_forward(spot, domestic_rate, foreign_rate, time_years)

            unrealized_pnl = self.calculate_pnl(side, spot, trade_price, quantity)
            data = {
                "trade_id": trade.get("trade_id"),
                "book_id": trade.get("book_id"),
                "asset_class": asset_class,
                "symbol": symbol,
                "fair_value": round(forward, 2),
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": 0.0,
                "total_pnl": unrealized_pnl,
                "currency": trade.get("trade_currency"),
            }
            self.log.info("calculated_forex_pnl", trade_id=trade.get("trade_id"), data=data)
            results.append(data)
        return results

    def calculate_commodity(self):
        """Calculate PnL for all active commodity trades"""
        asset_class = "COMMODITY"
        results = []
        data = {}
        active_trades = self.valuation_engine.get_active_trades(asset_class)

        for trade in active_trades:
            symbol = trade.get("symbol")
            ticks = self.valuation_engine.get_current_tick(symbol)
            quantity, trade_price, side = self.get_basic_values(trade)

            spot = ticks.get("spot")
            fair_value = spot * quantity

            unrealized_pnl = self.calculate_pnl(side, spot, trade_price, quantity)
            data = {
                "trade_id": trade.get("trade_id"),
                "book_id": trade.get("book_id"),
                "asset_class": asset_class,
                "symbol": symbol,
                "fair_value": round(fair_value, 2),
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": 0.0,
                "total_pnl": unrealized_pnl,
                "currency": trade.get("trade_currency"),
            }
            self.log.info("calculated_commodity_pnl", trade_id=trade.get("trade_id"), data=data)
            results.append(data)
        return results

    def calculate_futures(self):
        """Calculate PnL for all active futures trades"""
        asset_class = "FUTURES"
        results = []
        data = {}
        active_trades = self.valuation_engine.get_active_trades(asset_class)

        for trade in active_trades:
            symbol = trade.get("symbol")
            ticks = self.valuation_engine.get_current_tick(symbol)
            quantity, trade_price, side = self.get_basic_values(trade)

            current_price = ticks.get("mid")
            fair_value = current_price * self.multiplier * quantity

            unrealized_pnl = self.calculate_pnl(side, current_price, trade_price, quantity)
            data = {
                "trade_id": trade.get("trade_id"),
                "book_id": trade.get("book_id"),
                "asset_class": asset_class,
                "symbol": symbol,
                "fair_value": round(fair_value, 2),
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": 0.0,
                "total_pnl": unrealized_pnl,
                "currency": trade.get("trade_currency"),
            }
            self.log.info("calculated_futures_pnl", trade_id=trade.get("trade_id"), data=data)
            results.append(data)
        return results
