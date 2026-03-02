from js import Response, URL

async def on_fetch(request, env):
    url = URL.new(request.url)
    path = url.pathname
    
    # Handle CORS preflight if needed in the future
    if request.method == 'OPTIONS':
        return Response.new('', {
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            }
        })

    # Serving static files from the 'public' directory
    if hasattr(env, 'ASSETS'):
        return await env.ASSETS.fetch(request)
        
    return Response.new('Asset server not configured', {'status': 500})
