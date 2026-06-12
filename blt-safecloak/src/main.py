# pylint: disable=too-few-public-methods
import asyncio
import traceback

from workers import WorkerEntrypoint, Response
try:
    from workers import DurableObject
except ImportError:  # pragma: no cover - depends on Cloudflare runtime version
    DurableObject = object
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


class ChatRoom(DurableObject):
    """Encrypted WebSocket relay.

    The desktop client encrypts every payload before it reaches this object.
    The object only sees opaque ciphertext envelopes and room metadata from the
    URL. Recent ciphertext is retained briefly for reconnect/offline delivery
    and purged by alarm.
    """

    def __init__(self, state, env):
        self.state = state
        self.env = env
        self.sessions = set()

    async def fetch(self, request):
        if request.headers.get('Upgrade', '').lower() != 'websocket':
            return Response('Expected WebSocket',
                            status=426,
                            headers=base_headers('text/plain; charset=utf-8'))

        # Cloudflare's Python Worker runtime mirrors the JS WebSocketPair API.
        # Access it dynamically so local imports/tests still work outside the
        # edge runtime.
        try:
            from js import Date, WebSocketPair
        except ImportError:  # pragma: no cover
            return Response('WebSocketPair unavailable in this runtime',
                            status=500,
                            headers=base_headers('text/plain; charset=utf-8'))

        pair = WebSocketPair.new()
        client = pair[0]
        server = pair[1]
        server.accept()
        self.sessions.add(server)

        stored = await self.state.storage.get('messages') or []
        for item in stored:
            server.send(item)

        async def persist(ciphertext):
            messages = await self.state.storage.get('messages') or []
            messages.append(ciphertext)
            # One-hour, bounded safety buffer. The client dedupes by encrypted
            # plaintext message id after decryption.
            messages = messages[-500:]
            await self.state.storage.put('messages', messages)
            await self.state.storage.set_alarm(Date.now() + 60 * 60 * 1000)

        def on_message(event):
            ciphertext = event.data
            stale = []
            for ws in self.sessions:
                if ws == server:
                    continue
                try:
                    ws.send(ciphertext)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self.sessions.discard(ws)
            # Store in the background only when there is no other live client.
            if len(self.sessions) <= 1:
                self.state.wait_until(persist(ciphertext))

        def on_close(_event=None):
            self.sessions.discard(server)

        server.addEventListener('message', on_message)
        server.addEventListener('close', on_close)
        server.addEventListener('error', on_close)
        return Response(None, status=101, webSocket=client)

    async def alarm(self):
        await self.state.storage.delete('messages')


class Default(WorkerEntrypoint):
    """Worker entrypoint for handling HTTP requests and serving content."""

    async def on_fetch(self, request, env):
        """Handle incoming HTTP requests and route them to the appropriate response."""
        url = urlparse(request.url)
        path = url.path
        origin = request.headers.get('Origin') if hasattr(request, 'headers') else None

        try:
            # Handle CORS preflight
            if request.method == 'OPTIONS':
                return cors_response(origin=origin)

            # Handle GET requests for HTML pages
            if request.method == 'GET' and path in PAGES_MAP:
                html_path = Path(__file__).parent / 'pages' / PAGES_MAP[path]
                html_content = html_path.read_text(encoding='utf-8')
                return html_response(html_content, origin=origin)

            if request.method == 'GET' and path.startswith('/api/room/') and path.endswith('/ws'):
                if not hasattr(env, 'CHAT_ROOMS'):
                    return Response('CHAT_ROOMS Durable Object binding is not configured',
                                    status=503,
                                    headers=base_headers('text/plain; charset=utf-8',
                                                         origin=origin))
                room = path.removeprefix('/api/room/').removesuffix('/ws').strip('/')
                if not room:
                    return Response('Room name required',
                                    status=400,
                                    headers=base_headers('text/plain; charset=utf-8',
                                                         origin=origin))
                room_id = env.CHAT_ROOMS.idFromName(room)
                room_stub = env.CHAT_ROOMS.get(room_id)
                return await room_stub.fetch(request)

            # Serving static files from the 'public' directory
            if hasattr(env, 'ASSETS'):
                return await env.ASSETS.fetch(request)

            return Response('Not Found',
                            status=404,
                            headers=base_headers('text/plain; charset=utf-8'))

        except FileNotFoundError as exc:
            print(f'[404] Page file not found: {exc}')
            return Response('Not Found',
                            status=404,
                            headers=base_headers('text/plain; charset=utf-8', origin=origin))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            traceback.print_exc()
            return Response('Internal Server Error',
                            status=500,
                            headers=base_headers('text/plain; charset=utf-8', origin=origin))
