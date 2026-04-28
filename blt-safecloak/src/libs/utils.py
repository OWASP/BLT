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
from functools import lru_cache
import json
import os
from typing import Any, Dict, Set
from urllib.parse import urlsplit


def normalize_origin(origin: str) -> str:
    """Normalize origin for stable comparison."""
    value = origin.strip().rstrip('/')
    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc:
        return f'{parsed.scheme.lower()}://{parsed.netloc.lower()}'.rstrip('/')
    return value.lower()


@lru_cache(maxsize=128)
def parse_allowed_origins(configured: str) -> Set[str]:
    """Parse configured allowed origins once per unique env value."""
    return {normalize_origin(origin) for origin in configured.split(',') if origin.strip()}


def add_vary_origin(headers: Dict[str, str]) -> None:
    """Ensure responses varying by Origin are not cached across origins."""
    vary = headers.get('Vary')
    if not vary:
        headers['Vary'] = 'Origin'
        return

    vary_parts = [item.strip() for item in vary.split(',') if item.strip()]
    if 'Origin' not in vary_parts:
        vary_parts.append('Origin')
    headers['Vary'] = ', '.join(vary_parts)


def get_allowed_origins() -> Set[str]:
    """Return configured allowed CORS origins from env var SAFE_CLOAK_ALLOWED_ORIGINS."""
    configured = os.getenv('SAFE_CLOAK_ALLOWED_ORIGINS', '')
    return parse_allowed_origins(configured)


def resolve_allowed_origin(origin: str | None) -> str | None:
    """Return origin only when it is explicitly allowlisted; otherwise return None."""
    if not origin:
        return None
    normalized = normalize_origin(origin)
    return normalized if normalized in get_allowed_origins() else None


def base_headers(content_type: str, origin: str | None = None) -> Dict[str, str]:
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
    headers = {'Content-Type': content_type}
    if origin is not None:
        add_vary_origin(headers)
    allowed_origin = resolve_allowed_origin(origin)
    if allowed_origin:
        headers['Access-Control-Allow-Origin'] = allowed_origin
    return headers


def html_response(html_str: str, status: int = 200, origin: str | None = None) -> Response:
    """
    Create an HTML response.

    Args:
        html_str: HTML content to return
        status: HTTP status code (default: 200)

    Returns:
        Response object with HTML content type and CORS headers
    """
    return Response(html_str,
                    status=status,
                    headers=base_headers('text/html; charset=utf-8', origin=origin))


def json_response(data: Any, status: int = 200, origin: str | None = None) -> Response:
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
            default=str  # Fallback for non-serializable objects
        ),
        status=status,
        headers=base_headers('application/json; charset=utf-8', origin=origin))


def cors_response(origin: str | None = None, status: int = 204) -> Response:
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
    headers = {
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400',
        'Vary': 'Origin',
    }
    allowed_origin = resolve_allowed_origin(origin)
    if allowed_origin:
        headers['Access-Control-Allow-Origin'] = allowed_origin

    return Response(
        None,  # 204 responses should not include a body
        status=status,
        headers=headers)
