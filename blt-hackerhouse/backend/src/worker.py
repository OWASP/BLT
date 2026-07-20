"""Cloudflare Workers entrypoint.

Routes WebSocket to Durable Object, delegates all REST routes
to FastAPI via the ASGI adapter. Also handles cron (scheduled)
and Queue consumer messages.
"""

from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response, DurableObject
from js import WebSocketPair
import asgi

from app import app


class Default(WorkerEntrypoint):

    async def fetch(self, request):
        path = urlparse(str(request.url)).path

        if path == "/ws" or path.startswith("/ws?"):
            return await self._handle_ws(request)

        return await asgi.fetch(app, request, self.env)

    async def scheduled(self, controller, env, ctx):
        pass

    async def queue(self, batch, env, ctx):
        for msg in batch.messages:
            print("QUEUE", msg.body)
            msg.ack()

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
            return Response.new("ok", status=200)

        client, server = WebSocketPair.new().object_values()
        self.ctx.acceptWebSocket(server)
        server.send("Connected")
        return Response.new(None, status=101, web_socket=client)

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
