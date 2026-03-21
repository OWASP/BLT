"""
Utility functions for BLT-SafeCloak worker.

This module provides helper functions to generate HTTP responses
for HTML, JSON, and CORS preflight requests.

Key design decisions:
- Centralized header handling (DRY principle)
- Proper CORS support for both preflight AND actual responses
- Safer JSON serialization
"""

from workers import Response
import json
from typing import Any, Dict


def base_headers(content_type: str) -> Dict[str, str]:
    """
    Create a base set of headers for all responses.

    Why this exists:
    - Avoids repeating header logic (DRY)
    - Ensures CORS is applied consistently across all responses



    Args:
        content_type: The MIME type of the response

    Returns:
        Dictionary of headers
    """
    return {
        'Content-Type': content_type,

        # Allows any origin to access the response
        'Access-Control-Allow-Origin': '*',
    }


def html_response(html_str: str, status: int = 200) -> Response:
    """
    Create an HTML response.

    Args:
        html_str: HTML content to return
        status: HTTP status code (default: 200)

    Returns:
        Response object with HTML content type and CORS headers
    """
    return Response(
        html_str,
        status=status,
        headers=base_headers('text/html; charset=utf-8')
    )


def json_response(data: Any, status: int = 200) -> Response:
    """
    Create a JSON response.

    Improvements over basic implementation:
    - Supports non-ASCII characters (ensure_ascii=False)
    - Prevents crashes on non-serializable objects (default=str)

    Args:
        data: Any JSON-serializable data (dict, list, etc.)
        status: HTTP status code (default: 200)

    Returns:
        Response object with JSON content type and CORS headers
    """
    return Response(
        json.dumps(
            data,
            ensure_ascii=False,  # Keeps Unicode readable (e.g., हिंदी)
            default=str          # Fallback for non-serializable objects
        ),
        status=status,
        headers=base_headers('application/json; charset=utf-8')
    )


def cors_response(status: int = 204) -> Response:
    """
    Create a CORS preflight (OPTIONS) response.

    When this is used:
    - Browser sends an OPTIONS request before certain requests
    - This tells the browser what is allowed

   
    Args:
        status: HTTP status code (default: 204 No Content)

    Returns:
        Response object with CORS headers
    """
    return Response(
        None,  # 204 responses should not include a body
        status=status,
        headers={
            # Allow all origins 
            'Access-Control-Allow-Origin': '*',

            # Allowed HTTP methods
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',

            # Allowed request headers
            'Access-Control-Allow-Headers': 'Content-Type',

            # Cache preflight response (in seconds basically 1 day)
            # Reduces repeated OPTIONS requests
            'Access-Control-Max-Age': '86400',
        }
    )