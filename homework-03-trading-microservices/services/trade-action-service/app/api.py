from bottle import Bottle, request, response

class TradeActionApi(Bottle):
    def __init__(self, trade_action_queue):
        super().__init__()
        self.trade_action_queue = trade_action_queue
        self.route('/health', method='GET', callback=self.health)
        self.route('/trade-actions', method='POST', callback=self.trade_actions)
        self.route('/trade-actions/batch', method='POST', callback=self.trade_actions_batch)
        self.route('/queue/status', method='GET', callback=self.queue_status)

    def health(self):
        """Health check requested"""
        health_status = {
            "service": "trade-action-service",
            "status": "UP"
        }
        return health_status

    def trade_actions(self):
        """Queue a single trade action"""
        action_data = request.json
        if not action_data:
            response.status = 400
            return {"error": "Request body is required"}
        try:
            self.trade_action_queue.put(action_data)
            response.status = 202
            return {"message": "Trade action queued successfully"}
        except Exception as e:
            response.status = 500
            return {"error": f"Failed to queue trade action: {str(e)}"}
    
    def trade_actions_batch(self):
        """Queue a batch of trade actions"""
        action_data_list = request.json
        if not action_data_list or not isinstance(action_data_list, list):
            response.status = 400
            return {"error": "Request body must be a list of trade actions"}
        try:
            for action_data in action_data_list:
                self.trade_action_queue.put(action_data)
            response.status = 202
            return {"message": "Trade actions queued successfully"}
        except Exception as e:
            response.status = 500
            return {"error": f"Failed to queue trade action: {str(e)}"}

    def queue_status(self):
        """Get the current status of the trade action queue"""
        queue_size = self.trade_action_queue.get_size()
        status = {
            "message": "Queue status retrieved",
            "queue_size": queue_size
        }
        if queue_size == 0:
            status["message"] = "Queue is empty"

        return status
