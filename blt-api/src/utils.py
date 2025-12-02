"""
Utility functions for the BLT API.

This module provides common utilities for JSON responses, error handling,
CORS headers, and HTTP client operations.
"""

from typing import Any, Dict, Optional
import json

# Try to import Cloudflare Workers JS bindings
# Falls back to mock implementations for testing
try:
    from js import Response, Headers, JSON, Object
    _WORKERS_RUNTIME = True
except ImportError:
    _WORKERS_RUNTIME = False
    
    # Mock implementations for testing outside Workers runtime
    class Headers:
        @classmethod
        def new(cls, headers_dict):
            return headers_dict
    
    class Response:
        @classmethod
        def new(cls, body, status=200, headers=None):
            return MockResponse(body, status, headers)
    
    class MockResponse:
        def __init__(self, body, status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = headers or {}


def cors_headers() -> Dict[str, str]:
    """
    Return CORS headers for cross-origin requests.
    
    Returns:
        Dict containing CORS headers
    """
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Max-Age": "86400",
    }


def json_response(
    data: Any,
    status: int = 200,
    headers: Optional[Dict[str, str]] = None
) -> Response:
    """
    Create a JSON response.
    
    Args:
        data: Data to serialize as JSON
        status: HTTP status code
        headers: Additional headers to include
    
    Returns:
        Response object with JSON content
    """
    response_headers = {
        "Content-Type": "application/json",
        **cors_headers()
    }
    
    if headers:
        response_headers.update(headers)
    
    # Convert Python dict to JSON string
    json_body = json.dumps(data)
    
    # Create headers object for JavaScript
    js_headers = Headers.new(response_headers)
    
    return Response.new(json_body, status=status, headers=js_headers)


def error_response(
    message: str,
    status: int = 400,
    details: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Create an error JSON response.
    
    Args:
        message: Error message
        status: HTTP status code
        details: Additional error details
    
    Returns:
        Response object with error information
    """
    error_data = {
        "error": True,
        "message": message,
        "status": status
    }
    
    if details:
        error_data["details"] = details
    
    return json_response(error_data, status=status)


def success_response(
    data: Any = None,
    message: str = "Success",
    status: int = 200
) -> Response:
    """
    Create a success JSON response.
    
    Args:
        data: Response data
        message: Success message
        status: HTTP status code
    
    Returns:
        Response object with success information
    """
    response_data = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response_data["data"] = data
    
    return json_response(response_data, status=status)


def paginated_response(
    items: list,
    page: int = 1,
    per_page: int = 20,
    total: Optional[int] = None
) -> Response:
    """
    Create a paginated JSON response.
    
    Args:
        items: List of items for current page
        page: Current page number
        per_page: Items per page
        total: Total number of items (optional)
    
    Returns:
        Response object with pagination metadata
    """
    response_data = {
        "success": True,
        "data": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "count": len(items)
        }
    }
    
    if total is not None:
        response_data["pagination"]["total"] = total
        response_data["pagination"]["total_pages"] = (total + per_page - 1) // per_page
    
    return json_response(response_data)


def parse_pagination_params(query_params: Dict[str, str]) -> tuple:
    """
    Parse pagination parameters from query string.
    
    Args:
        query_params: Dictionary of query parameters
    
    Returns:
        Tuple of (page, per_page)
    """
    try:
        page = int(query_params.get("page", "1"))
        page = max(1, page)  # Ensure page is at least 1
    except ValueError:
        page = 1
    
    try:
        per_page = int(query_params.get("per_page", "20"))
        per_page = max(1, min(100, per_page))  # Clamp between 1 and 100
    except ValueError:
        per_page = 20
    
    return page, per_page


def get_blt_api_url(env: Any) -> str:
    """
    Get the BLT API base URL from environment.
    
    Args:
        env: Environment bindings
    
    Returns:
        BLT API base URL string
    """
    try:
        return str(env.BLT_API_BASE_URL)
    except AttributeError:
        return "https://blt.owasp.org/api/v1"


def get_blt_website_url(env: Any) -> str:
    """
    Get the BLT website URL from environment.
    
    Args:
        env: Environment bindings
    
    Returns:
        BLT website URL string
    """
    try:
        return str(env.BLT_WEBSITE_URL)
    except AttributeError:
        return "https://blt.owasp.org"


async def parse_json_body(request: Any) -> Optional[Dict[str, Any]]:
    """
    Parse JSON body from request.
    
    Args:
        request: The incoming Request object
    
    Returns:
        Parsed JSON data or None if parsing fails
    """
    try:
        text = await request.text()
        if text:
            return json.loads(text)
        return None
    except (json.JSONDecodeError, Exception):
        return None
