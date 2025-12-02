"""
Tests for the utility functions.
"""

import pytest
import json
from src.utils import (
    cors_headers,
    parse_pagination_params,
)


class TestCorsHeaders:
    """Tests for CORS headers function."""
    
    def test_cors_headers_returns_dict(self):
        """Test that cors_headers returns a dictionary."""
        headers = cors_headers()
        assert isinstance(headers, dict)
    
    def test_cors_headers_contains_origin(self):
        """Test that cors_headers contains Access-Control-Allow-Origin."""
        headers = cors_headers()
        assert "Access-Control-Allow-Origin" in headers
        assert headers["Access-Control-Allow-Origin"] == "*"
    
    def test_cors_headers_contains_methods(self):
        """Test that cors_headers contains allowed methods."""
        headers = cors_headers()
        assert "Access-Control-Allow-Methods" in headers
        assert "GET" in headers["Access-Control-Allow-Methods"]
        assert "POST" in headers["Access-Control-Allow-Methods"]
        assert "PUT" in headers["Access-Control-Allow-Methods"]
        assert "DELETE" in headers["Access-Control-Allow-Methods"]
        assert "OPTIONS" in headers["Access-Control-Allow-Methods"]
    
    def test_cors_headers_contains_allowed_headers(self):
        """Test that cors_headers contains allowed headers."""
        headers = cors_headers()
        assert "Access-Control-Allow-Headers" in headers
        assert "Content-Type" in headers["Access-Control-Allow-Headers"]
        assert "Authorization" in headers["Access-Control-Allow-Headers"]


class TestPaginationParams:
    """Tests for pagination parameter parsing."""
    
    def test_default_values(self):
        """Test default pagination values."""
        page, per_page = parse_pagination_params({})
        assert page == 1
        assert per_page == 20
    
    def test_custom_values(self):
        """Test custom pagination values."""
        page, per_page = parse_pagination_params({"page": "2", "per_page": "50"})
        assert page == 2
        assert per_page == 50
    
    def test_invalid_page(self):
        """Test handling of invalid page value."""
        page, per_page = parse_pagination_params({"page": "invalid"})
        assert page == 1
    
    def test_invalid_per_page(self):
        """Test handling of invalid per_page value."""
        page, per_page = parse_pagination_params({"per_page": "invalid"})
        assert per_page == 20
    
    def test_negative_page(self):
        """Test handling of negative page value."""
        page, per_page = parse_pagination_params({"page": "-5"})
        assert page == 1  # Should be clamped to minimum of 1
    
    def test_per_page_max_limit(self):
        """Test that per_page is clamped to maximum of 100."""
        page, per_page = parse_pagination_params({"per_page": "500"})
        assert per_page == 100
    
    def test_per_page_min_limit(self):
        """Test that per_page is clamped to minimum of 1."""
        page, per_page = parse_pagination_params({"per_page": "0"})
        assert per_page == 1


class TestJSONSerialization:
    """Tests for JSON serialization."""
    
    def test_serialize_dict(self):
        """Test serializing a dictionary."""
        data = {"key": "value", "number": 42}
        result = json.dumps(data)
        assert '"key": "value"' in result or '"key":"value"' in result
    
    def test_serialize_list(self):
        """Test serializing a list."""
        data = [1, 2, 3, "test"]
        result = json.dumps(data)
        parsed = json.loads(result)
        assert parsed == data
    
    def test_serialize_nested(self):
        """Test serializing nested structures."""
        data = {
            "items": [{"id": 1}, {"id": 2}],
            "meta": {"page": 1, "total": 100}
        }
        result = json.dumps(data)
        parsed = json.loads(result)
        assert parsed == data
