"""
Homepage handler that returns HTML with API documentation.
"""

from typing import Any, Dict
from pathlib import Path

try:
    from js import Response, Headers
    _WORKERS_RUNTIME = True
except ImportError:
    _WORKERS_RUNTIME = False
    from utils import Response, Headers


async def handle_homepage(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle API homepage endpoint (GET /).
    
    Serves an interactive HTML documentation page with:
    - Complete list of all API endpoints and descriptions
    - Interactive "Try it" buttons for testing endpoints
    - Response format examples
    - Authentication information
    
    The HTML template uses [[API_BASE_URL]] placeholder syntax which is
    replaced with the actual request URL base for dynamic API endpoint links.
    
    Returns:
        HTML Response with Content-Type text/html and CORS headers enabled,
        displaying the full API documentation interface with working endpoint testers
    """
    
    # Get request URL to construct API base URL
    url = str(request.url)
    # Extract base URL (protocol + host)
    if "://" in url:
        protocol_and_host = url.split("://", 1)[1].split("/", 1)[0]
        base_url = f"{url.split('://')[0]}://{protocol_and_host}"
    else:
        base_url = "https://blt-api.workers.dev"
    
    html_file = Path(__file__).resolve().parent.parent / "pages" / "index.html"
    html_content = html_file.read_text().replace("[[API_BASE_URL]]", base_url)
    
    # Create HTML response with proper headers
    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    
    # Convert dict to list of tuples for Headers.new
    js_headers = Headers.new(list(headers.items()))
    
    return Response.new(html_content, status=200, headers=js_headers)
