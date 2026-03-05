"""Utility functions for BLT-SafeCloak worker."""
from workers import Response


def html_response(html_str: str, status: int = 200) -> Response:
    """Create an HTML response.
    
    Args:
        html_str: HTML content to return
        status: HTTP status code (default: 200)
        
    Returns:
        Response object with HTML content type
    """
    return Response(html_str, status=status, headers={'Content-Type': 'text/html; charset=utf-8'})


def json_response(data: dict, status: int = 200) -> Response:
    """Create a JSON response.
    
    Args:
        data: Dictionary to return as JSON
        status: HTTP status code (default: 200)
        
    Returns:
        Response object with JSON content type
    """
    import json
    return Response(json.dumps(data),
                    status=status,
                    headers={'Content-Type': 'application/json; charset=utf-8'})


def cors_response(status: int = 204) -> Response:
    """Create a CORS preflight response.
    
    Args:
        status: HTTP status code (default: 204)
        
    Returns:
        Response object with CORS headers
    """
    return Response('',
                    status=status,
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type',
                    })
