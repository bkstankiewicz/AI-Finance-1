from bottle import Bottle, request, response

class TradeGeneratorApi(Bottle):
    def __init__(self, action_client):
        super().__init__()
        self.generation_status = action_client
        self.route('/health', method='GET', callback=self.health)
        self.route('/generate-once', method='POST', callback=self.generate_once)
        self.route('/start', method='POST', callback=self.start)
        self.route('/stop', method='POST', callback=self.stop)
        self.route('/status', method='GET', callback=self.status)


    def health(self):
        """Health check requested"""
        health_status = {
            "service": "trade-generation-service",
            "status": "UP"
        }
        return health_status


    def generate_once(self):
        """Generate a single trade"""
        self.generation_status.generate_once()
        return {"message": "Trade generation once requested"}


    def start(self):
        """Start generating trades continuously"""
        self.generation_status.start()
        return {"message": "Trade generation started"}


    def stop(self):
        """Stop generating trades continuously"""
        self.generation_status.stop()
        return {"message": "Trade generation stopped"}


    def status(self):
        """Get the current status of the trade generation service"""
        status = {
            "service": "trade-generation-service",
            "status": "running" if self.generation_status.is_running() else "stopped"
        }
        return status
