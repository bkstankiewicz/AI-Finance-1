from bottle import Bottle
from monitor import Monitor


class MonitoringServiceApi(Bottle):
    def __init__(self, monitor: Monitor):
        super().__init__()
        self.monitor = monitor
        self.route('/health', method='GET', callback=self.health)
        self.route('/status', method='GET', callback=self.service_status)

    def health(self):
        """Health check requested"""
        health_status = {
            "service": "monitoring-service",
            "status": "UP"
        }
        return health_status

    def service_status(self):
        """Get the current status of the monitored services"""
        return self.monitor.status
