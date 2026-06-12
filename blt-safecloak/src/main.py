# pylint: disable=too-few-public-methods
import asyncio
import traceback
import re
from pathlib import Path
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response

try:
    from workers import DurableObject
except ImportError:  # pragma: no cover - depends on Cloudflare runtime version
    DurableObject = object

from libs.utils import html_response, cors_response, base_headers

# Route to HTML page mapping
PAGES_MAP = {
    '/': 'index.html',
    '/video-chat': 'video-chat.html',
    '/video-room': 'video-room.html',
    '/notes': 'notes.html',
    '/consent': 'consent.html',
}

ROOM_RE = re.compile(r'^[A-Za-z0-9._-]{1,80}$')
MAX_ROOM_CONNECTIONS = 128
MAX_CIPHERTEXT_BYTES = 96 * 1024 * 1024
MAX_STORED_CIPHERTEXTS = 200


def _get_binding(env, name):
    """Read a Cloudflare binding from either attribute-style or mapping-style env."""
    if env is None:
        return None
    try:
        value = getattr(env, name)
        if value is not None:
            return value
    except Exception:  # pragma: no cover - depends on runtime proxy behavior
        pass
    try:
        return env[name]
    except Exception:  # pragma: no cover - depends on runtime proxy behavior
        return None


class ChatRoom(DurableObject):
    """Encrypted WebSocket relay.

    The desktop client encrypts every payload before it reaches this object.
    The object only sees opaque ciphertext envelopes and room metadata from the
    URL. Recent ciphertext is retained briefly for reconnect/offline delivery
    and purged by alarm.
    """

    def __init__(self, state, env):
        try:
            super().__init__(state, env)
        except TypeError:  # pragma: no cover - for local fallback object
            pass

        # Different Python Workers versions expose these as ctx/env or state/env.
        self.state = getattr(self, 'ctx', state)
        self.env = env
        self.sessions = set()
        self._event_proxies = {}

    async def fetch(self, request):
        """Current Python Durable Object HTTP handler name."""
        return await self._handle_fetch(request)

    async def on_fetch(self, request):
        """Compatibility handler for Python Workers runtimes expecting on_fetch."""
        return await self._handle_fetch(request)

    async def _handle_fetch(self, request):
        if request.headers.get('Upgrade', '').lower() != 'websocket':
            return Response('Expected WebSocket',
                            status=426,
                            headers=base_headers('text/plain; charset=utf-8'))

        if request.method != 'GET':
            return Response('Expected GET',
                            status=400,
                            headers=base_headers('text/plain; charset=utf-8'))

        # Cloudflare's Python Worker runtime mirrors the JS WebSocketPair API.
        # Use the Python shape documented by Cloudflare: object_values() and
        # Response(..., web_socket=client).
        try:
            from js import Date, WebSocketPair
            from pyodide.ffi import create_proxy
        except ImportError:  # pragma: no cover
            return Response('WebSocketPair unavailable in this runtime',
                            status=500,
                            headers=base_headers('text/plain; charset=utf-8'))

        client, server = WebSocketPair.new().object_values()

        if len(self.sessions) >= MAX_ROOM_CONNECTIONS:
            # Accept before returning 101 so the client receives a valid WS close.
            server.accept()
            server.close(1013, 'room full')
            return Response(None, status=101, web_socket=client)

        server.accept()
        self.sessions.add(server)

        stored = await self.state.storage.get('messages') or []
        for item in stored:
            try:
                server.send(item)
            except Exception:
                break

        async def persist(ciphertext):
            if isinstance(ciphertext, str):
                size = len(ciphertext.encode('utf-8'))
            else:
                size = len(ciphertext)
            if size > MAX_CIPHERTEXT_BYTES:
                return

            messages = await self.state.storage.get('messages') or []
            messages.append(ciphertext)
            # One-hour, bounded safety buffer. The client dedupes by encrypted
            # plaintext message id after decryption.
            messages = messages[-MAX_STORED_CIPHERTEXTS:]
            await self.state.storage.put('messages', messages)
            await self.state.storage.set_alarm(Date.now() + 60 * 60 * 1000)

        async def handle_message(ciphertext):
            if isinstance(ciphertext, str):
                size = len(ciphertext.encode('utf-8'))
            else:
                size = len(ciphertext)

            if size > MAX_CIPHERTEXT_BYTES:
                server.close(1009, 'message too large')
                self._cleanup_session(server)
                return

            stale = []
            for ws in list(self.sessions):
                if ws == server:
                    continue
                try:
                    ws.send(ciphertext)
                except Exception:
                    stale.append(ws)

            for ws in stale:
                self._cleanup_session(ws)

            # Store in the background only when there is no other live client.
            if len(self.sessions) <= 1:
                try:
                    self.state.wait_until(persist(ciphertext))
                except AttributeError:
                    await persist(ciphertext)

        async def on_message(event):
            await handle_message(event.data)

        async def on_close(_event=None):
            self._cleanup_session(server)

        message_proxy = create_proxy(on_message)
        close_proxy = create_proxy(on_close)
        error_proxy = create_proxy(on_close)

        self._event_proxies[server] = (message_proxy, close_proxy, error_proxy)

        server.addEventListener('message', message_proxy)
        server.addEventListener('close', close_proxy)
        server.addEventListener('error', error_proxy)

        return Response(None, status=101, web_socket=client)

    def _cleanup_session(self, server):
        self.sessions.discard(server)
        proxies = self._event_proxies.pop(server, None)
        if proxies:
            for proxy in proxies:
                try:
                    proxy.destroy()
                except Exception:
                    pass

    async def alarm(self):
        await self.state.storage.delete('messages')


class Default(WorkerEntrypoint):
    """Worker entrypoint for handling HTTP requests and serving content."""

    async def fetch(self, request):
        """Current Python Worker entrypoint."""
        return await self._handle_request(request, getattr(self, 'env', None))

    async def on_fetch(self, request, env=None):
        """Compatibility entrypoint for older wrappers/tests."""
        return await self._handle_request(request, env or getattr(self, 'env', None))

    async def _handle_request(self, request, env):
        """Handle incoming HTTP requests and route them to the appropriate response."""
        url = urlparse(request.url)
        path = url.path
        origin = request.headers.get('Origin') if hasattr(request, 'headers') else None

        try:
            # Handle CORS preflight.
            if request.method == 'OPTIONS':
                return cors_response(origin=origin)

            # Handle GET requests for HTML pages.
            if request.method == 'GET' and path in PAGES_MAP:
                html_path = Path(__file__).parent / 'pages' / PAGES_MAP[path]
                html_content = html_path.read_text(encoding='utf-8')
                return html_response(html_content, origin=origin)

            # Handle room WebSockets before static assets.
            if request.method == 'GET' and path.startswith('/api/room/') and path.endswith('/ws'):
                if request.headers.get('Upgrade', '').lower() != 'websocket':
                    return Response('Expected WebSocket upgrade',
                                    status=426,
                                    headers=base_headers('text/plain; charset=utf-8',
                                                         origin=origin))

                chat_rooms = _get_binding(env, 'CHAT_ROOMS')
                if chat_rooms is None:
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
                if not ROOM_RE.fullmatch(room):
                    return Response('Invalid room name',
                                    status=400,
                                    headers=base_headers('text/plain; charset=utf-8',
                                                         origin=origin))

                room_id = chat_rooms.idFromName(room)
                room_stub = chat_rooms.get(room_id)
                return await room_stub.fetch(request)

            # Serving static files from the configured assets binding.
            assets = _get_binding(env, 'ASSETS')
            if assets is not None:
                return await assets.fetch(request)

            return Response('Not Found',
                            status=404,
                            headers=base_headers('text/plain; charset=utf-8',
                                                 origin=origin))

        except FileNotFoundError as exc:
            print(f'[404] Page file not found: {exc}')
            return Response('Not Found',
                            status=404,
                            headers=base_headers('text/plain; charset=utf-8', origin=origin))
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc()
            return Response('Internal Server Error',
                            status=500,
                            headers=base_headers('text/plain; charset=utf-8', origin=origin))
