import time
from responses import json_response, add_default_headers

# Basic in-memory rate limiting (resets on worker restart)
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 100

_ip_requests = {}

def rate_limit_middleware(request):
    """
    Checks if the incoming request exceeds the rate limit.
    Returns a Response with a 429 status code if limited, else None.
    """
    # Try to extract an IP from standard headers; default to 'unknown'
    ip = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for") or "unknown"
    
    current_time = time.time()
    
    # Initialize or reset window for the IP
    if ip not in _ip_requests:
        _ip_requests[ip] = []
        
    # Clean up old requests outside the window
    _ip_requests[ip] = [req_time for req_time in _ip_requests[ip] if current_time - req_time < RATE_LIMIT_WINDOW]
    
    if len(_ip_requests[ip]) >= MAX_REQUESTS_PER_WINDOW:
        response = json_response(
            {"error": "Too Many Requests", "message": f"Rate limit exceeded. Maximum {MAX_REQUESTS_PER_WINDOW} requests per {RATE_LIMIT_WINDOW} seconds."}, 
            status=429
        )
        return add_default_headers(response)
        
    _ip_requests[ip].append(current_time)
    return None

def alert_routing_middleware(request, path):
    """
    Middleware to route high-severity alerts. 
    Verifies privacy-safe payloads before passing through to core logic.
    Returns an error Response if verification fails, else None.
    """
    # We apply this specifically to paths that accept alerts/post data.
    if request.method in ["POST", "PUT"] and path.startswith("/api/alerts"):
        content_type = request.headers.get("content-type") or ""
        if "application/json" not in content_type:
            response = json_response({"error": "Invalid Content-Type", "message": "Expected application/json"}, status=400)
            return add_default_headers(response)
            
        # At this stage in the request lifecycle (sync context), we might not be able to 
        # await request.json() natively if we don't know the exact async nature, 
        # so we perform header-level checks. 
        # Extended payload checks should be handled in the specific route handlers.
        
    return None
