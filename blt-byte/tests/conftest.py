"""
pytest conftest – provide lightweight stubs for Cloudflare Workers runtime
modules that are not available outside the CF Workers environment.
"""
import json as _json
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
            return Response(_json.dumps(data), 200, {"Content-Type": "application/json"})

    class WorkerEntrypoint:
        pass

    mod.Response = Response
    mod.WorkerEntrypoint = WorkerEntrypoint
    return mod


def _make_pyodide_stub():
    """Return a minimal stub of the 'pyodide' module."""
    mod = ModuleType("pyodide")
    mod.setDebug = lambda *a, **kw: None
    return mod


def _make_js_stub():
    """Return a minimal stub of the 'js' module used in the Cloudflare Workers runtime."""
    mod = ModuleType("js")

    class _JSON:
        @staticmethod
        def parse(text):
            return _json.loads(text)

        @staticmethod
        def stringify(obj):
            return _json.dumps(obj)

    mod.JSON = _JSON()
    return mod


# Inject before any test module imports src/main.py
sys.modules.setdefault("workers", _make_workers_stub())
sys.modules.setdefault("pyodide", _make_pyodide_stub())
sys.modules.setdefault("js", _make_js_stub())
