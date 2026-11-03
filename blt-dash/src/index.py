"""Main entry point for BLT-Dash Cybersecurity Dashboard - Cloudflare Worker"""

from js import Response, URL


async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname

    # Redirect /dash and /dash/ to root
    if path == '/dash' or path == '/dash/':
        return Response.redirect(str(URL.new('/', request.url)), 302)

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

    return Response.new('Not Found', {'status': 404, 'headers': cors_headers})
