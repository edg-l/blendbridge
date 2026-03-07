"""Background HTTP server for the BlendBridge addon."""

import threading
from http.server import HTTPServer

from . import executor
from .handlers import BlendBridgeHandler

_server = None
_thread = None


def is_running() -> bool:
    return _server is not None


def start(port: int = 8400):
    global _server, _thread

    if _server is not None:
        return

    executor.start()

    _server = HTTPServer(("127.0.0.1", port), BlendBridgeHandler)
    _thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _thread.start()
    print(f"BlendBridge server started on http://127.0.0.1:{port}")


def stop():
    global _server, _thread

    executor.stop()

    if _server is not None:
        _server.shutdown()
        _server = None
        _thread = None
        print("BlendBridge server stopped")
