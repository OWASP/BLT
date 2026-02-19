"""Main entry point for BLT-Rewards (BACON) - Cloudflare Worker"""

from js import Response, URL


async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response.new('', {'headers': cors_headers})
    
    # Serve HTML for root path 
    if path == '/' or path == '/index.html':
        with open('public/index.html', 'r') as f:
            html_content = f.read()
        return Response.new(html_content, {
            'headers': {
                **cors_headers,
                'Content-Type': 'text/html; charset=utf-8'
            }
        })
    
    # All other routes will be handled by static assets in public/
    # Return 404 for unknown API routes
    return Response.new('Not Found', {
        'status': 404,
        'headers': cors_headers
    })
