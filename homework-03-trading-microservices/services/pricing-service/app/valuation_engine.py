def validate_input(func):
    def wrapper(self, *args, **kwargs):
        if not args or not args[0]:
            raise ValueError(f"{func.__name__} argument cannot be None or empty")
        return func(self, *args, **kwargs)
    return wrapper

class ValuationEngine():
    def __init__(self, trades_valuations, market_data_client):
        self.trades_valuations = trades_valuations
        self.market_data_client = market_data_client

    @validate_input
    def get_active_trades(self, asset_class):
        """Get all active trades for a specific asset class"""
        return self.trades_valuations.get_all_active_trades(asset_class)

    @validate_input
    def get_closed_trades(self, asset_class):
        """Get closed trades that still need their final realized PnL valuation"""
        return self.trades_valuations.get_closed_trades(asset_class)

    @validate_input
    def get_current_tick(self, symbol):
        """Get the current market tick for a specific symbol"""
        return self.market_data_client.get_price(symbol)

    @validate_input
    def settle_trade(self, valuation):
        """Persist the final realized PnL of a closed trade and mark it settled"""
        return self.trades_valuations.settle_trade(valuation)

    @validate_input
    def get_valuation_by_trade_id(self, trade_id):
        """Get the latest valuations for a specific trade_id"""
        return self.trades_valuations.get_valuation_by_trade_id(trade_id)

    def get_all_valuations(self):
        """Get the latest valuations"""
        return self.trades_valuations.get_all_valuations()
