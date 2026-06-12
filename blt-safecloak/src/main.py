# pylint: disable=too-few-public-methods
import asyncio
import traceback
import re
import time
import uuid

from workers import DurableObject, Response, WorkerEntrypoint

try:
    from pyodide.ffi import create_proxy
except ImportError:  # pragma: no cover - only available in Cloudflare Python runtime
    def create_proxy(callback):
        return callback

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

ROOM_RE = re.compile(r'^[A-Za-z0-9._-]{1,80}$')
MAX_ROOM_CONNECTIONS = 128
MAX_CIPHERTEXT_BYTES = 96 * 1024 * 1024
MAX_STORED_CIPHERTEXTS = 200
MESSAGE_TTL_MS = 60 * 60 * 1000


def _get_binding(env, name):
    """Return a Worker binding from Python/JS-style env objects."""
    if env is None:
        return None

    try:
        value = getattr(env, name)
        if value is not None:
            return value
    except Exception:  # pragma: no cover - depends on runtime FFI behavior
        pass

    try:
        value = env[name]
        if value is not None:
            return value
    except Exception:  # pragma: no cover - env is usually attribute-based
        pass

    try:
        value = env.get(name)
        if value is not None:
            return value
    except Exception:  # pragma: no cover - env may not be dict-like
        pass

    return None


def _ciphertext_size(ciphertext):
    if isinstance(ciphertext, str):
        return len(ciphertext.encode('utf-8'))
    return len(ciphertext)


def _destroy_proxy(proxy):
    destroy = getattr(proxy, 'destroy', None)
    if destroy:
        destroy()


class Session:
    """A connected WebSocket plus the JS callback proxies it owns."""

    def __init__(self, *, ws, proxies):
        self.ws = ws
        self.proxies = proxies


class ChatRoom(DurableObject):
    """Encrypted WebSocket relay.

    The desktop client encrypts every payload before it reaches this object.
    The object only sees opaque ciphertext envelopes and room metadata from the
    URL. Recent ciphertext is retained briefly for reconnect/offline delivery
    and purged by alarm.
    """

    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.ctx = ctx
        self.env = env
        self.sessions = {}

    async def fetch(self, request):
        if request.method != 'GET':
            return Response('Expected GET',
                            status=405,
                            headers=base_headers('text/plain; charset=utf-8'))

        if request.headers.get('Upgrade', '').lower() != 'websocket':
            return Response('Expected WebSocket',
                            status=426,
                            headers=base_headers('text/plain; charset=utf-8'))

        try:
            from js import WebSocketPair
        except ImportError:  # pragma: no cover
            return Response('WebSocketPair unavailable in this runtime',
                            status=500,
                            headers=base_headers('text/plain; charset=utf-8'))

        # Cloudflare Python Workers expose JS object values through object_values().
        client, server = WebSocketPair.new().object_values()
        server.accept()

        if len(self.sessions) >= MAX_ROOM_CONNECTIONS:
            server.close(1013, 'room full')
            return Response(None, status=101, web_socket=client)

        session_id = str(uuid.uuid4())

        async def on_message(event):
            await self._handle_message(session_id, event.data)

        async def on_close(_event=None):
            await self._drop_session(session_id, close_socket=False)

        message_proxy = create_proxy(on_message)
        close_proxy = create_proxy(on_close)
        error_proxy = create_proxy(on_close)

        server.addEventListener('message', message_proxy)
        server.addEventListener('close', close_proxy)
        server.addEventListener('error', error_proxy)

        self.sessions[session_id] = Session(
            ws=server,
            proxies=[message_proxy, close_proxy, error_proxy],
        )

        stored = await self.ctx.storage.get('messages') or []
        stale = []
        for item in stored:
            try:
                server.send(item)
            except Exception:
                stale.append(session_id)
                break

        for stale_id in stale:
            await self._drop_session(stale_id, close_socket=True)

        return Response(None, status=101, web_socket=client)

    async def _handle_message(self, session_id, ciphertext):
        session = self.sessions.get(session_id)
        if not session:
            return

        if _ciphertext_size(ciphertext) > MAX_CIPHERTEXT_BYTES:
            await self._drop_session(session_id,
                                     close_socket=True,
                                     code=1009,
                                     reason='message too large')
            return

        stale = []
        for other_id, other in list(self.sessions.items()):
            if other_id == session_id:
                continue
            try:
                other.ws.send(ciphertext)
            except Exception:
                stale.append(other_id)

        for stale_id in stale:
            await self._drop_session(stale_id, close_socket=True)

        # Store in the short replay buffer only when there is no other live client.
        if len(self.sessions) <= 1:
            await self._persist(ciphertext)

    async def _persist(self, ciphertext):
        if _ciphertext_size(ciphertext) > MAX_CIPHERTEXT_BYTES:
            return

        messages = await self.ctx.storage.get('messages') or []
        messages.append(ciphertext)
        messages = messages[-MAX_STORED_CIPHERTEXTS:]
        await self.ctx.storage.put('messages', messages)
        self.ctx.storage.setAlarm(int(time.time() * 1000) + MESSAGE_TTL_MS)

    async def _drop_session(self, session_id, *, close_socket=False, code=1000, reason=''):
        session = self.sessions.pop(session_id, None)
        if not session:
            return

        if close_socket:
            try:
                session.ws.close(code, reason)
            except Exception:
                pass

        for proxy in session.proxies:
            _destroy_proxy(proxy)

    async def alarm(self):
        await self.ctx.storage.delete('messages')


class Default(WorkerEntrypoint):
    """Worker entrypoint for handling HTTP requests and serving content."""

    async def fetch(self, request):
        """Current Python Workers entrypoint."""
        return await self._handle_request(request, getattr(self, 'env', None))

    async def on_fetch(self, request, env=None):
        """Compatibility with older WorkerEntrypoint wrappers."""
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

            # WebSocket room route. Keep this before static assets so the upgrade
            # request can never be swallowed by ASSETS.fetch().
            if path.startswith('/api/room/') and path.endswith('/ws'):
                if request.method != 'GET':
                    return Response('Expected GET',
                                    status=405,
                                    headers=base_headers('text/plain; charset=utf-8',
                                                         origin=origin))

                if request.headers.get('Upgrade', '').lower() != 'websocket':
                    return Response('Expected Upgrade: websocket',
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

            # Handle GET requests for HTML pages.
            if request.method == 'GET' and path in PAGES_MAP:
                html_path = Path(__file__).parent / 'pages' / PAGES_MAP[path]
                html_content = html_path.read_text(encoding='utf-8')
                return html_response(html_content, origin=origin)

            # Serve static files from the configured assets binding.
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
                            headers=base_headers('text/plain; charset=utf-8',
                                                 origin=origin))
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc()
            return Response('Internal Server Error',
                            status=500,
                            headers=base_headers('text/plain; charset=utf-8',
                                                 origin=origin))
