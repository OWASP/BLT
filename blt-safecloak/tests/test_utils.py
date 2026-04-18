import sys
import os
import json
import pytest
import ast
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# --- THE CLOUDFLARE MOCK ---
# This creates a "fake" Cloudflare workers module so local Python doesn't crash.
mock_workers = MagicMock()

class FakeResponse:
    def __init__(self, body, status=200, headers=None):
        self.body = body.encode('utf-8') if isinstance(body, str) else body
        self.status_code = status
        self.headers = headers or {}

mock_workers.Response = FakeResponse
mock_workers.WorkerEntrypoint = type('WorkerEntrypoint', (), {})
sys.modules['workers'] = mock_workers
# ---------------------------

# Fix the path so it finds your 'src' folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Now the import will work perfectly!
from src.libs.utils import html_response, json_response, cors_response


def test_html_response():
    """Test that html_response sets the correct headers and content."""
    html_content = "<h1>Test Page</h1>"
    response = html_response(html_content)
    
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "<h1>Test Page</h1>" in response.body.decode('utf-8')
    #fix for issue 2
    assert response.headers["Access-Control-Allow-Origin"] == "*"

def test_json_response():
    """Test that json_response correctly formats a dict to JSON."""
    data = {"status": "success"}
    response = json_response(data)
    
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json; charset=utf-8"
    assert json.loads(response.body) == data
    #fix for issue 2
    assert response.headers["Access-Control-Allow-Origin"] == "*"

def test_cors_response():
    """Test that cors_response injects the correct CORS headers."""
    response = cors_response()
    #fix for isssue 3
    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert response.headers["Access-Control-Allow-Methods"] == "GET, POST, OPTIONS"
    assert response.headers["Access-Control-Allow-Headers"] == "Content-Type"
    assert response.headers["Access-Control-Max-Age"] == "86400"

def test_json_response_default_str_fallback():
    """
    Documents the API policy that unserializable objects 
    (like datetime or sets) are safely cast to strings instead of failing.
    """
    # Create an object json.dumps() normally fails on
    unserializable_data = {
        "timestamp": datetime(2026, 3, 22, 12, 0, 0),
        "unique_items": {1, 2, 3} 
    }
    
    response = json_response(unserializable_data)
    
    assert response.status_code == 200
    response_data = json.loads(response.body)
    # fix for issue 1
    assert response_data["timestamp"] == "2026-03-22 12:00:00"
    actual_set = set(ast.literal_eval(response_data["unique_items"]))
    assert actual_set == {1, 2, 3}


# --- on_fetch error handling tests ---
# main.py uses 'from libs.utils import ...' (Cloudflare Workers path),
# so we register src/libs as 'libs' before importing main.
import src.libs.utils as _utils_mod
sys.modules['libs'] = type(sys)('libs')
sys.modules['libs.utils'] = _utils_mod

from src.main import Default


def _make_request(method='GET', path='/'):
    """Create a fake request object for testing."""
    req = MagicMock()
    req.method = method
    req.url = f'http://localhost:8787{path}'
    return req


def _make_env(has_assets=False):
    """Create a fake env object for testing."""
    env = MagicMock(spec=[])
    if has_assets:
        env.ASSETS = AsyncMock()
    return env


def test_on_fetch_missing_page_returns_404():
    """Verify that a missing page file returns a clean 404, not an unhandled exception."""
    worker = Default()
    req = _make_request('GET', '/consent')
    env = _make_env()

    with patch('src.main.Path') as mock_path:
        mock_path.return_value = mock_path
        mock_path.__truediv__ = MagicMock(return_value=mock_path)
        instance = mock_path.return_value
        instance.parent.__truediv__ = MagicMock(return_value=instance)
        # Simulate read_text raising FileNotFoundError
        instance.read_text.side_effect = FileNotFoundError('consent.html not found')

        # Patch Path(__file__).parent / 'pages' / ... to raise
        with patch.object(Default, 'on_fetch', wraps=worker.on_fetch):
            response = asyncio.run(worker.on_fetch(req, env))

    assert response.status_code == 404
    assert b'Not Found' in response.body


def test_on_fetch_unexpected_error_returns_500():
    """Verify that an unexpected exception returns a clean 500, not a stack trace."""
    worker = Default()
    req = _make_request('GET', '/notes')
    env = _make_env()

    with patch('src.main.Path') as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.parent.__truediv__ = MagicMock(return_value=mock_instance)
        mock_instance.__truediv__ = MagicMock(return_value=mock_instance)
        mock_instance.read_text.side_effect = RuntimeError('disk I/O error')

        response = asyncio.run(worker.on_fetch(req, env))

    assert response.status_code == 500
    assert b'Internal Server Error' in response.body


def test_on_fetch_cancelled_error_is_reraised():
    """Verify that asyncio.CancelledError is not swallowed by the error handler."""
    worker = Default()
    req = _make_request('GET', '/notes')
    env = _make_env()

    with patch('src.main.Path') as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.parent.__truediv__ = MagicMock(return_value=mock_instance)
        mock_instance.__truediv__ = MagicMock(return_value=mock_instance)
        mock_instance.read_text.side_effect = asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            asyncio.run(worker.on_fetch(req, env))