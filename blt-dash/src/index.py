"""Main entry point for BLT-Dash Cybersecurity Dashboard - Cloudflare Worker"""

from js import Response, URL


async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname

    # Strip /dash prefix
    if path == '/dash':
        path = '/'
    elif path.startswith('/dash/'):
        path = path[5:]

    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }

    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response.new('', {'headers': cors_headers})

    # Serve static assets
    if hasattr(env, 'ASSETS'):
        return await env.ASSETS.fetch(request)

    # Fallback for root path
    if path == '/' or path == '/index.html':
        return Response.new(
            '<h1>BLT-Dash Cybersecurity Dashboard</h1><p>Please configure assets in wrangler.toml</p>',
            {'status': 200, 'headers': {**cors_headers, 'Content-Type': 'text/html'}},
        )

    return Response.new('Not Found', {'status': 404, 'headers': cors_headers})