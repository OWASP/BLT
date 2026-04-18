# pylint: disable=too-few-public-methods
import asyncio
import traceback

from workers import WorkerEntrypoint, Response
from urllib.parse import urlparse
from pathlib import Path

from libs.utils import html_response, cors_response, base_headers

# Route to HTML page mapping
PAGES_MAP = {
    '/': 'index.html',
    '/video-chat': 'video-chat.html',
    '/video-room': 'video-room.html',
    '/notes': 'notes.html',
    '/consent': 'consent.html',
}


class Default(WorkerEntrypoint):
    """Worker entrypoint for handling HTTP requests and serving content."""

    async def on_fetch(self, request, env):
        """Handle incoming HTTP requests and route them to the appropriate response."""
        url = urlparse(request.url)
        path = url.path

        try:
            # Handle CORS preflight
            if request.method == 'OPTIONS':
                return cors_response()

            # Handle GET requests for HTML pages
            if request.method == 'GET' and path in PAGES_MAP:
                html_path = Path(__file__).parent / 'pages' / PAGES_MAP[path]
                html_content = html_path.read_text(encoding='utf-8')
                return html_response(html_content)

            # Serving static files from the 'public' directory
            if hasattr(env, 'ASSETS'):
                return await env.ASSETS.fetch(request)

            return Response('Not Found', status=404)

        except FileNotFoundError as exc:
            print(f'[404] Page file not found: {exc}')
            return Response(
                'Not Found',
                status=404,
                headers=base_headers('text/plain; charset=utf-8')
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            traceback.print_exc()
            return Response(
                'Internal Server Error',
                status=500,
                headers=base_headers('text/plain; charset=utf-8')
            )
