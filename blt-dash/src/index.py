"""Main entry point for BLT-Dash Cybersecurity Dashboard - Cloudflare Worker"""

from js import Request, Response, URL


async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname

    # Redirect /dash and /dash/ to root (navigation-only redirect; browser addresses follow 302)
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
        
    # Sub-path rewrite: strip /dash prefix (e.g. /dash/logo.svg -> /logo.svg)
    if path.startswith('/dash/'):
        new_url = URL.new(request.url)
        new_url.pathname = path[5:]
        request = Request.new(str(new_url), request)

    # Serve static assets
    if hasattr(env, 'ASSETS'):
        return await env.ASSETS.fetch(request)

    return Response.new(
        'Server misconfiguration: ASSETS binding is missing in wrangler.toml',
        {'status': 500, 'headers': cors_headers},
    )