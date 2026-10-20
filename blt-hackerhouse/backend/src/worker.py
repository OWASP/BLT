"""Cloudflare Workers entrypoint.

Routes WebSocket to Durable Object, delegates all REST routes
to FastAPI via the ASGI adapter. Also handles cron (scheduled)
and Queue consumer messages.
"""

import json
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response, DurableObject
from js import WebSocketPair
import asgi

from app import app
from core.security import verify_token


# blt-cron holds the account's cron trigger and calls POST /__scheduled
# through a service binding, authenticated with the shared CRON_SECRET.
CRON_DISPATCH_PATH = "/__scheduled"


def _json_response(body, status):
    return Response(json.dumps(body), status=status, headers={"Content-Type": "application/json"})


async def handle_cron_dispatch(request, env, run_scheduled):
    """Check ``X-BLT-Cron-Secret`` against ``CRON_SECRET`` and await ``run_scheduled()``."""
    if request.method != "POST":
        return _json_response({"ok": False, "error": "Method not allowed"}, 405)
    expected = str(getattr(env, "CRON_SECRET", None) or "")
    provided = str(request.headers.get("X-BLT-Cron-Secret") or "")
    if not verify_token(provided, expected):
        return _json_response({"ok": False, "error": "Forbidden"}, 403)
    try:
        summary = await run_scheduled()
    except Exception as exc:
        return _json_response({"ok": False, "error": str(exc)}, 500)
    return _json_response(summary or {"ok": True}, 200)


class Default(WorkerEntrypoint):

    async def fetch(self, request):
        path = urlparse(str(request.url)).path

        if path == "/ws" or path.startswith("/ws?"):
            return await self._handle_ws(request)

        if path == CRON_DISPATCH_PATH:
            return await handle_cron_dispatch(request, self.env, self._run_scheduled)

        return await asgi.fetch(app, request, self.env)

    async def scheduled(self, controller=None, *args, **kwargs):
        await self._run_scheduled()

    async def _run_scheduled(self):
        from ingestion.forge_poller import run_forge_poll

        return await run_forge_poll(self.env)

    async def queue(self, batch, *args, **kwargs):
        from pipeline.consumer import process_pipeline_event, record_consumer_health

        env = self.env
        db = env.HH_DB
        last_type = None
        for msg in batch.messages:
            body = msg.body
            if not isinstance(body, (str, dict)) and hasattr(body, "to_py"):
                body = body.to_py()
            event_dict = json.loads(body) if isinstance(body, str) else body
            # An exception propagates: the message is not acked and is retried.
            if await process_pipeline_event(event_dict, db, env, record_health=False):
                last_type = event_dict.get("event_type") if isinstance(event_dict, dict) else None
            msg.ack()
        if last_type:
            await record_consumer_health(db, last_type)

    async def _handle_ws(self, request):
        upgrade_header = request.headers.get("Upgrade")
        if not upgrade_header or upgrade_header.lower() != "websocket":
            return Response("Worker expected Upgrade: websocket", status=426)

        do_id = self.env.WEBSOCKET_ROOM.idFromName("global-room")
        stub = self.env.WEBSOCKET_ROOM.get(do_id)
        return await stub.fetch(request)


class WebSocketRoom(DurableObject):

    async def fetch(self, request):
        import json

        path = urlparse(str(request.url)).path

        if path == "/internal/broadcast":
            body = await request.json()
            self._broadcast(body)
            return Response("ok", status=200)

        client, server = WebSocketPair.new().object_values()
        self.ctx.acceptWebSocket(server)
        server.send(json.dumps({"type": "connected", "message": "Connected"}))
        return Response(None, status=101, web_socket=client)

    async def webSocketMessage(self, ws, message):
        pass

    async def webSocketClose(self, ws, code, reason, wasClean):
        pass

    def _broadcast(self, message_dict):
        import json
        for ws in self.ctx.getWebSockets():
            try:
                ws.send(json.dumps(message_dict, default=str))
            except Exception:
                pass
