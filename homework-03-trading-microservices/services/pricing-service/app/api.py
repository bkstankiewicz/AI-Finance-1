from bottle import Bottle, request, response


class PricingServiceApi(Bottle):
    def __init__(self, publisher, valuation_engine):
        super().__init__()
        self.publisher = publisher
        self.valuation_engine = valuation_engine
        self.route('/health', method='GET', callback=self.health)
        self.route('/valuations', method='GET', callback=self.valuations)
        self.route('/valuations/<trade_id>', method='GET', callback=self.valuations_by_trade)
        self.route('/valuation-stream', method='GET', callback=self.valuation_stream)

    def health(self):
        """Health check requested"""
        health_status = {
            "service": "pricing-service",
            "status": "UP"
        }
        return health_status

    def valuations(self):
        """Get all valuations with optional limit"""
        limit = int(request.query.get('limit', 20)) # type: ignore[attr-defined]
        return {"valuations": self.valuation_engine.get_all_valuations(limit=limit)}

    def valuations_by_trade(self, trade_id):
        """Get valuations for a specific trade_id with optional limit"""
        limit = int(request.query.get('limit', 20)) # type: ignore[attr-defined]
        return {"valuations": self.valuation_engine.get_valuation_by_trade_id(trade_id, limit=limit)}

    def valuation_stream(self):
        """Stream requested"""
        response.content_type = "text/event-stream"
        response.set_header("Cache-Control", "no-cache")
        return self.publisher.stream_events()

