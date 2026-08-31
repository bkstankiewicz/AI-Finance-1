class ValuationEngine():
    def __init__(self, trades_valuations, market_data_client):
        self.trades_valuations = trades_valuations
        self.market_data_client = market_data_client

    def get_active_trades(self, asset_class):
        """Get all active trades for a specific asset class"""
        if not asset_class:
            return None
        return self.trades_valuations.get_all_active_trades(asset_class)

    def get_closed_trades(self, asset_class):
        """Get closed trades that still need their final realized PnL valuation"""
        if not asset_class:
            return None
        return self.trades_valuations.get_closed_trades(asset_class)

    def get_current_tick(self, symbol):
        """Get the current market tick for a specific symbol"""
        if not symbol:
            return None
        return self.market_data_client.get_price(symbol)

    def mark_trade_settled(self, trade_id):
        """Mark a closed trade as settled once its final realized PnL has been calculated"""
        if not trade_id:
            return None
        return self.trades_valuations.mark_trade_settled(trade_id)

    def get_valuation_by_trade_id(self, trade_id, limit=20):
        """Get valuations for a specific trade_id, limited by the specified number"""
        if not trade_id:
            return None
        return self.trades_valuations.get_valuation_by_trade_id(trade_id, limit=limit)

    def get_all_valuations(self, limit=20):
        """Get all valuations, limited by the specified number"""
        return self.trades_valuations.get_all_valuations(limit=limit)
