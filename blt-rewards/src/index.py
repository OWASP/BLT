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
    
    # Redirect root path to index.html
    # Static assets are served directly by Cloudflare's asset handling configured in wrangler.toml
    if path == '/':
        return Response.new('', {
            'status': 302,
            'headers': {
                **cors_headers,
                'Location': '/index.html'
            }
        })
    
    # API routes can be added here
    # Example:
    # if path.startswith('/api/'):
    #     return handle_api_request(request, env)
    
    # All other routes (including /index.html and other static files) 
    # are handled by Cloudflare's static asset serving
    # Return None to let Cloudflare serve the static asset
    return None
