"""
Utility functions for the BLT API.

This module provides common utilities for JSON responses, error handling,
CORS headers, and HTTP client operations.
"""

from typing import Any, Dict, List, Optional
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
        def new(cls, body, init=None):
            """Mock Response.new() to match Cloudflare Workers API."""
            if init is None:
                init = {}
            return MockResponse(body, init.get('status', 200), init.get('headers', {}))
    
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
    
    # Create Response with proper status code for Cloudflare Workers
    response_init = {
        'status': status,
        'headers': response_headers
    }
    return Response.new(json_body, response_init)


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

def convert_d1_results(results) -> List[Dict]:
    """Convert D1 proxy results to Python list of dicts.
    
    Args:
        results: D1 results object (could be JS proxy or Python list)
    
    Returns:
        List of dictionaries
    """
    if results is None:
        return []
    
    # Handle to_py() method if available (converts JsProxy to Python)
    if hasattr(results, 'to_py'):
        return results.to_py()
    
    # If already a list, return as is
    if isinstance(results, list):
        return results
    
    return []

async def check_required_fields(body, required_fields):
    for field in required_fields:
        if field not in body:
            return False, field
    return True, None

async def convert_single_d1_result(data):
    if hasattr(data, 'to_py'):
        return data.to_py()
    else:
        return dict(data)

def extract_id_from_result(result: Any, field:str) -> Optional[int]:
    """
    Extract ID from a database query result.
    
    Args:
        result: Database query result (JsProxy, dict, or other)
        field: Name of the ID field to extract
    
    Returns:
        The extracted ID value or None if not found
    """
    if not result:
        return None
    
    if hasattr(result, 'to_py'):
        return result.to_py().get(field)
    elif hasattr(result, field):
        return getattr(result, field)
    elif isinstance(result, dict):
        return result.get(field)
    
    return None


def debug_object(obj: Any, label: str = "DEBUG") -> None:
    """
    Debug utility to inspect any object and print its structure.
    Useful for debugging database results and other complex objects.
    
    Args:
        obj: Object to inspect
        label: Label to identify the debug output
    """
    print(f"\n{'='*60}")
    print(f"🔍 {label}")
    print(f"{'='*60}")
    print(f"Type: {type(obj)}")
    print(f"Value: {obj}")
    
    # Check if it's None
    if obj is None:
        print("⚠️  Object is None")
        print(f"{'='*60}\n")
        return
    
    # Check for to_py() method (Cloudflare D1 result)
    if hasattr(obj, 'to_py'):
        print(f"✓ Has to_py() method")
        try:
            py_obj = obj.to_py()
            print(f"to_py() result: {py_obj}")
            print(f"to_py() type: {type(py_obj)}")
        except Exception as e:
            print(f"✗ Error calling to_py(): {e}")
    
    # List all attributes and methods
    print(f"\nAttributes and methods:")
    attrs = dir(obj)
    for attr in attrs:
        if not attr.startswith('_'):  # Skip private/magic methods
            try:
                value = getattr(obj, attr)
                print(f"  - {attr}: {type(value).__name__}")
                if not callable(value):
                    print(f"      Value: {value}")
            except Exception as e:
                print(f"  - {attr}: Error accessing ({e})")
    
    # If it's dict-like
    if isinstance(obj, dict):
        print(f"\nDict keys: {list(obj.keys())}")
        print(f"Dict values: {list(obj.values())}")
    
    # Try to access as dict
    if hasattr(obj, '__getitem__'):
        print(f"✓ Object supports indexing (dict-like)")
    
    print(f"{'='*60}\n")


def debug_db_result(result: Any, label: str = "DB Result") -> Dict[str, Any]:
    """
    Debug database result and return it as a Python dict.
    
    Args:
        result: Database query result
        label: Label for debug output
    
    Returns:
        Dictionary representation of the result
    """
    debug_object(result, label)
    
    if not result:
        return {}
    
    if hasattr(result, 'to_py'):
        return result.to_py()
    elif isinstance(result, dict):
        return result
    else:
        # Try to convert to dict
        try:
            return dict(result)
        except:
            return {"error": "Could not convert to dict", "type": str(type(result))}
