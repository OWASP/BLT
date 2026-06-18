"""FastAPI routes and WebSocket endpoint."""

from .routes import router, set_dependencies
from .websocket import websocket_endpoint

__all__ = ["router", "set_dependencies", "websocket_endpoint"]