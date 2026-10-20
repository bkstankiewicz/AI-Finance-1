from bottle import Bottle, response
from monitor import Monitor
from publisher import MonitorPublisher
import repository


class MonitoringServiceApi(Bottle):
    def __init__(self, monitor: Monitor, publisher: MonitorPublisher):
        super().__init__()
        self.monitor = monitor
        self.publisher = publisher
        self.route('/health', method='GET', callback=self.health)
        self.route('/status', method='GET', callback=self.service_status)
        self.route('/stream', method='GET', callback=self.stream)
        self.route('/error-counter/<service_name>', method='GET', callback=self.error_counter)
        self.route('/last-error-timestamp/<service_name>', method='GET', callback=self.last_error_timestamp)

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

    def stream(self):
        """Stream events from the monitoring service"""
        response.content_type = "text/event-stream"
        response.set_header("Cache-Control", "no-cache")
        return self.publisher.stream_events()

    def error_counter(self, service_name: str):
        """Count transitions to DOWN for a specific service"""
        return {"service": service_name, "error_count": repository.get_error_counter_per_service(service_name)}

    def last_error_timestamp(self, service_name: str):
        """Get the last error timestamp for a specific service"""
        timestamp = repository.get_last_error_timestamp(service_name)
        return {"service": service_name, "last_error_timestamp": timestamp.isoformat() if timestamp else None}
