"""
Cloudflare Worker for Toasty - AI Code Reviewer Backend

This worker handles API requests for the Toasty AI code review service.
It provides endpoints for code analysis, health checks, and status monitoring.
"""

from js import Response, fetch, Headers
import json


async def on_fetch(request, env):
    """
    Main entry point for Cloudflare Worker requests.
    
    Args:
        request: The incoming HTTP request
        env: Environment variables and bindings
        
    Returns:
        Response: HTTP response object
    """
    url = request.url
    method = request.method
    
    # Parse the URL to get the path
    try:
        # Extract path from URL (handle query params and fragments)
        # Format: https://domain.com/path?query#fragment
        url_without_protocol = url.split('://', 1)[1] if '://' in url else url
        path_start = url_without_protocol.find('/')
        
        if path_start == -1:
            path = '/'
        else:
            # Get everything after the domain
            path_with_query = url_without_protocol[path_start:]
            # Remove query parameters and fragments
            path = path_with_query.split('?')[0].split('#')[0]
            # Ensure path starts with /
            if not path.startswith('/'):
                path = '/' + path
            # Remove trailing slash for consistent matching (except root)
            if len(path) > 1 and path.endswith('/'):
                path = path[:-1]
    except Exception as e:
        return create_error_response(f"Error parsing URL: {str(e)}", 500)
    
    # Route requests based on path and method
    if path == '/' or path == '':
        return handle_root(request)
    elif path == '/health':
        return handle_health(request)
    elif path == '/api/review' and method == 'POST':
        return await handle_review(request, env)
    elif path == '/api/status' and method == 'GET':
        return handle_status(request)
    else:
        return create_error_response(f"Not Found: {path}", 404)


def handle_root(request):
    """
    Handle root endpoint requests.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        Response: Welcome message
    """
    response_data = {
        "service": "Toasty AI Code Reviewer",
        "version": "1.0.0",
        "description": "Backend API for OWASP BLT's AI-powered code review service",
        "endpoints": {
            "/": "Service information",
            "/health": "Health check endpoint",
            "/api/review": "POST - Submit code for review",
            "/api/status": "GET - Check service status"
        }
    }
    
    return create_json_response(response_data, 200)


def handle_health(request):
    """
    Handle health check endpoint.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        Response: Health status
    """
    health_data = {
        "status": "healthy",
        "service": "toasty-backend",
        "timestamp": None  # Would use datetime in production
    }
    
    return create_json_response(health_data, 200)


async def handle_review(request, env):
    """
    Handle code review requests.
    
    Args:
        request: The incoming HTTP request
        env: Environment variables and bindings
        
    Returns:
        Response: Code review results
    """
    try:
        # Parse request body
        body = await request.text()
        
        if not body:
            return create_error_response("Request body is required", 400)
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return create_error_response("Invalid JSON in request body", 400)
        
        # Validate required fields
        if 'code' not in data:
            return create_error_response("Missing required field: 'code'", 400)
        
        code = data.get('code', '')
        language = data.get('language', 'unknown')
        context = data.get('context', '')
        
        # Placeholder for actual AI review logic
        # In production, this would call AI services, perform static analysis, etc.
        review_result = {
            "status": "success",
            "analysis": {
                "language": language,
                "lines_of_code": len(code.split('\n')),
                "issues": [],
                "suggestions": [
                    {
                        "type": "info",
                        "message": "Code review placeholder - integration with AI services pending",
                        "line": 0
                    }
                ],
                "summary": "Review completed successfully"
            },
            "metadata": {
                "processed_at": None,  # Would use datetime in production
                "worker_version": "1.0.0"
            }
        }
        
        return create_json_response(review_result, 200)
        
    except Exception as e:
        return create_error_response(f"Error processing review request: {str(e)}", 500)


def handle_status(request):
    """
    Handle status check endpoint.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        Response: Service status information
    """
    status_data = {
        "service": "toasty-backend",
        "status": "operational",
        "version": "1.0.0",
        "features": {
            "code_review": "available",
            "health_check": "available",
            "status_monitoring": "available"
        },
        "uptime": "available"
    }
    
    return create_json_response(status_data, 200)


def create_json_response(data, status_code=200):
    """
    Create a JSON response with proper headers.
    
    Args:
        data: Dictionary to serialize as JSON
        status_code: HTTP status code
        
    Returns:
        Response: JSON response object
    """
    headers = Headers.new()
    headers.set("Content-Type", "application/json")
    headers.set("Access-Control-Allow-Origin", "*")
    headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    headers.set("Access-Control-Allow-Headers", "Content-Type")
    
    return Response.new(
        json.dumps(data),
        status=status_code,
        headers=headers
    )


def create_error_response(message, status_code=500):
    """
    Create an error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        
    Returns:
        Response: Error response object
    """
    error_data = {
        "error": message,
        "status": status_code
    }
    
    return create_json_response(error_data, status_code)
