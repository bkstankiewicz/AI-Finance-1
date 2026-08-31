from wsgiref.simple_server import make_server, WSGIServer
from socketserver import ThreadingMixIn
from bottle import ServerAdapter


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class ThreadedServer(ServerAdapter):
    def run(self, handler):
        server = make_server(
            self.host,
            self.port,
            handler,
            server_class=ThreadingWSGIServer
        )
        server.serve_forever()

def run_server(app, host, port):
    """Run the Bottle server with threading support"""
    server = ThreadedServer(host=host, port=port)
    app.run(server=server)