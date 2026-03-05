from js import Response, URL
from workers import WorkerEntrypoint
from urllib.parse import urlparse

from pathlib import Path


class Default(WorkerEntrypoint):

    async def on_fetch(self, request, env):
        url = urlparse(request.url)
        path = url.path

        # Handle CORS preflight if needed in the future
        if request.method == 'OPTIONS':
            return Response.new(
                '', {
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type',
                    }
                })

        if (path == '/'):
            html_content = Path(__file__).parent / 'pages' / 'index.html'
            return Response.new(html_content,
                                {'headers': {
                                    'Content-Type': 'text/html'
                                }})
        # Serving static files from the 'public' directory
        if hasattr(env, 'ASSETS'):
            return await env.ASSETS.fetch(request)

        return Response.new('Asset server not configured', {'status': 500})
