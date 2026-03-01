"""
pytest conftest – provide lightweight stubs for Cloudflare Workers runtime
modules that are not available outside the CF Workers environment.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock


def _make_workers_stub():
    """Return a minimal stub of the 'workers' package."""
    mod = ModuleType("workers")

    class Response:
        def __init__(self, body="", status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = headers or {}

        @staticmethod
        def json(data):
            import json
            return Response(json.dumps(data), 200, {"Content-Type": "application/json"})

    class WorkerEntrypoint:
        pass

    mod.Response = Response
    mod.WorkerEntrypoint = WorkerEntrypoint
    return mod


# Inject before any test module imports src/entry.py
sys.modules.setdefault("workers", _make_workers_stub())
