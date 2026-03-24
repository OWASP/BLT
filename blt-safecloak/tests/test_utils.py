import sys
import os
import json
import pytest
import ast
from datetime import datetime
from unittest.mock import MagicMock

# --- THE CLOUDFLARE MOCK ---
# This creates a "fake" Cloudflare workers module so local Python doesn't crash.
mock_workers = MagicMock()

class FakeResponse:
    def __init__(self, body, status=200, headers=None):
        self.body = body.encode('utf-8') if isinstance(body, str) else body
        self.status_code = status
        self.headers = headers or {}

mock_workers.Response = FakeResponse
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