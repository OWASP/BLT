# Design Decisions — BLT Hacker House → Cloudflare Workers Migration

**Status:** Revised — ASGI adapter, native D1, preflight-validated APIs  
**Date:** 2026-07-19  
**Audience:** Engineers implementing this migration  

---

## Target Architecture

```
Browser UI + static avatars/assets (served via [assets])
    ├─ REST (HTTP)     → FastAPI through Workers ASGI (import asgi; asgi.fetch(app, request, env))
    ├─ WebSocket       → Durable Object broadcast hub
    └─ Fallback        → /state REST endpoint

GitLab webhook / Cron pollers
    └─ Cloudflare Queue → pipeline consumer → D1 + Durable Object broadcast
```

**What stays:** FastAPI, Pydantic, `httpx`, route handlers, normalization, identity resolver, message builders.

**What changes:** `aiosqlite` → D1 native prepared statements, `asyncio.Queue` → Cloudflare Queues, background tasks → `scheduled()`, in-memory `WebSocketHub` → Durable Object, `uvicorn` → `import asgi`.

---

## Decision 1: FastAPI + Pydantic via `import asgi`

**Choice:** Keep the existing FastAPI application intact. Use Cloudflare's `asgi` module (`import asgi`) to bridge ASGI to Workers. The Worker entrypoint calls `asgi.fetch(app, request, env)`.

**Correct API (from Cloudflare's FastAPI Workers example):**

```python
# src/worker.py — Worker entrypoint (separate from app factory)
from workers import WorkerEntrypoint
import asgi
from .app import app  # FastAPI application (no Worker imports)

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        """The Cloudflare Python Workers HTTP handler is fetch(), not on_fetch()."""
        path = urlparse(str(request.url)).path

        # Intercept WebSocket before ASGI routing
        if path == "/ws":
            return await self._handle_ws_upgrade(request)

        # All REST routes → FastAPI via ASGI
        return await asgi.fetch(app, request, self.env)

    async def scheduled(self, controller, env, ctx):
        """Cron trigger. Signature: (self, controller, env, ctx)."""
        await run_polling_cycle(env)

    async def queue(self, batch):
        """Queue consumer."""
        for msg in batch.messages:
            await process_pipeline_message(msg, self.env)
```

**What is removed:** `uvicorn` dependency, `lifespan` context manager, `StaticFiles` mounts, `app.state.*`, `@app.websocket("/ws")`.

**Modules split:**
- `src/app.py` — `create_app() -> FastAPI` (pure FastAPI, no Worker imports)
- `src/worker.py` — `class Default(WorkerEntrypoint)` (Worker-specific: `fetch`, `scheduled`, `queue`)

---

## Decision 2: Native D1 Queries — No Adapter Layer

**Choice:** Refactor `storage/queries.py` to use D1's native prepared-statement API directly. Do not build a cursor-compatible adapter around D1 — it will become fragile around transactions, async context managers, row metadata, and writes.

**Why an adapter fails:**
- D1 has no real `BEGIN/COMMIT` transactions in the aiosqlite sense
- D1 cursors are not stateful iterators (`fetchone()` can't be called repeatedly on the same statement)
- `row_factory`, `lastrowid`, `rowcount` semantics differ
- `executescript()` for migrations has no D1 equivalent

**Instead: refactor each query class to D1's API.**

```python
# BEFORE (aiosqlite):
class EventQueries:
    async def list_activity(self, page, per_page):
        offset = (page - 1) * per_page
        async with self.db.conn.execute(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_event(r) for r in rows], ...

# AFTER (D1):
class EventQueries:
    def __init__(self, d1_binding):   # Takes D1 binding, not Database
        self._db = d1_binding

    async def list_activity(self, page, per_page):
        offset = (page - 1) * per_page
        result = await self._db.prepare(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        ).bind(per_page, offset).all()
        rows = [r.to_py() for r in (result.results or [])]
        return [_row_to_event(r) for r in rows], ...

    async def insert(self, event):
        stmt = self._db.prepare(
            "INSERT OR IGNORE INTO events (...) VALUES (?, ?, ...)"
        ).bind(...)
        await stmt.run()
        # Get last row id
        id_result = await self._db.prepare(
            "SELECT last_insert_rowid() AS id"
        ).first()
        return id_result.to_py()["id"] if id_result else None
```

**Migration runner:** Explicit `wrangler d1 migrations apply` step in CI. No `run_migrations()` in application code. No `executescript()` needed.

**Database access per request:**

```python
# src/app.py
def create_app() -> FastAPI:
    app = FastAPI()
    ...

# In route handlers — DB accessed via request.scope (set by ASGI adapter)
async def get_db(request: Request):
    env = request.scope.get("env")  # Injected by asgi.fetch()
    return env.HH_DB     # D1 binding — pass directly to query classes
```

No `Database` wrapper class. No `get_database()` singleton. Query classes receive the raw D1 binding.

---

## Decision 3: Queues with Per-Message Ack

**Choice:** Webhook and cron publish JSON-compatible dicts (`model_dump(mode="json")`) to the Queue. Consumer acks each message after durable D1 work succeeds. Messages that fail with recoverable errors are retried; terminal errors go to dead-letter + ack.

**Producer:**
```python
await env.PIPELINE_QUEUE.send(event.model_dump(mode="json"))
```

**Consumer:**
```python
async def queue(self, batch):
    for msg in batch.messages:
        try:
            event_data = msg.body  # Already a dict, not a JSON string
            event = Event(**event_data)
            await process_event(event, self.env)
            msg.ack()
        except RecoverableError:
            msg.retry()
        except TerminalError:
            await record_dead_letter(event_data, str(e), self.env)
            msg.ack()
```

---

## Decision 4: `scheduled(controller, env, ctx)` for Cron

**Correct signature:** `async def scheduled(self, controller, env, ctx)` — NOT `scheduled(self, event)`.

```python
async def scheduled(self, controller, env, ctx):
    db = env.HH_DB
    blt_count = await poll_blt_api(env)
    gitlab_count = await poll_gitlab_gaps(env)
    logger.info("poll complete", extra={"blt": blt_count, "gitlab": gitlab_count})
```

State persisted in D1 (`poll_cursors` table + new `health_state` table). No in-memory poller objects.

---

## Decision 5: Durable Object with `getByName()`

**Correct API:** Python Workers DO uses `getByName()`, not `idFromName()`.

```python
# Worker → DO routing
do_stub = env.WEBSOCKET_ROOM.getByName("global-room")
return await do_stub.fetch(request.url, {
    "method": "GET",
    "headers": dict(request.headers),
})
```

**DO class:**
```python
class WebSocketRoom(DurableObject):
    async def fetch(self, request):
        path = urlparse(str(request.url)).path
        if path == "/internal/broadcast":
            body = await request.json()
            self._broadcast(body)
            return Response.new("ok", status=200)
        # WebSocket upgrade
        pair = WebSocketPair.new()
        self.ctx.acceptWebSocket(pair[0])
        snapshot = await build_snapshot(self.env.HH_DB)
        pair[0].send(json.dumps(snapshot))
        return Response.new(None, status=101, webSocket=pair[1])

    def _broadcast(self, message_dict):
        for ws in self.ctx.getWebSockets():
            try:
                ws.send(json.dumps(message_dict))
            except Exception:
                pass
```

**Preflight spike required:** Prove `do_stub.fetch()` request construction works before Phase 5. The exact URL, method, headers, and body format for internal DO calls must be verified.

---

## Decision 6: No Custom Router — FastAPI Routes Preserved

All existing routes in `src/api/routes.py` stay. The ASGI layer handles Worker Request → ASGI translation. Only `/ws` is intercepted before ASGI.

---

## Decision 7: Static Assets — Preserve Actual URLs

**Actual files in UI/:**
```
UI/index.html  (→ homepage, HackerHouse dashboard)
UI/activity_feed.html
UI/leaderboard.html
UI/status_health.html
UI/threejs.html
UI/assets/css/*
UI/assets/js/*
UI/avatars/avatar-0.png ... avatar-9.png
```

Wrangler `[assets]` serves these at their root-relative paths:

```toml
[assets]
directory = "./UI"
```

This serves `/index.html`, `/activity_feed.html`, `/avatars/avatar-0.png`, `/assets/css/...` etc.

**Do not** add a `Path.read_text()` route for `/`. Workers filesystem is not the repo filesystem. Workers Assets handles static file serving.

---

## Decision 8: Authentication — Unchanged

Three verification points, identical to legacy. All use `hmac.compare_digest`.

---

## Decision 9: Protected Production Migrations

Migrations run as explicit deployment step — never in `[build]` hooks, never in Git Builds for preview branches.

```bash
# CI pipeline (production only):
wrangler d1 migrations apply hackerhouse --remote
wrangler deploy
```

Git Builds for PR previews do NOT apply migrations.

---

## Decision 10: rapidfuzz — Verify Before Commit

Preflight spike: deploy a minimal Worker that imports rapidfuzz. If compatible, keep it. If not, pure-Python fallback behind the same `IdentityResolver` interface.

---

## Decision 11: CORS — Same-Origin by Default

No permissive CORS. Same-origin Worker UI doesn't need it.

---

## Decision 12: Testing — Three Levels

Unit (pytest with mocked D1/Queue/DO), integration (wrangler dev + local D1), browser acceptance (staging Worker URL).

---

## Decision 13: No Global Sequence Counter

Queue delivery is at-least-once and concurrent. A durable sequence counter in D1 would be a contention point. Drop strict global ordering. The `sequence_number` field becomes optional — best-effort only from `event.timestamp` ordering in queries.

---

## Decision 14: `queue_depth` Preserved in /status

The `/status` response keeps `queue_depth` as a field. Value is the current Queue backlog (queried via Cloudflare API or set to `null`/`0` temporarily until Queue metrics API is available). Never silently omit a frontend-expected field.

---

## Trade-Off Summary

| Trade-Off | Gain | Lose |
|---|---|---|
| Native D1 (no adapter) | Clean, predictable query API. No fragile emulation layer. | Must refactor every query class (~15 methods). |
| `asgi.fetch()` | Official Cloudflare API. FastAPI routes work unchanged. | Must split app/worker modules. |
| `scheduled(controller, env, ctx)` | Correct Workers Python API. | Poll state must be D1-backed. |
| `getByName()` for DO | Correct Python Workers DO API. | Must verify stub.fetch() request format in preflight spike. |
| Drop global sequence counter | No D1 write contention. Simpler consumer. | No strict ordering guarantee (acceptable — events are timestamp-ordered anyway). |
| `pywrangler` for deploy | Correct Python package bundling. | Not `npx wrangler`. |
| Protected migrations | No accidental production schema changes from PR previews. | Manual production migration step. |

---

## Preflight Spikes (Before Phase 0)

| Spike | Verify |
|---|---|
| FastAPI ASGI | `import asgi; asgi.fetch(app, request, env)` serves a health route |
| Static assets | `[assets]` serves `/avatars/avatar-0.png` and `/activity_feed.html` |
| D1 query | `env.HH_DB.prepare("SELECT 1").first()` returns data |
| Queue send/consume | `env.QUEUE.send({...})` → `queue(batch)` receives it |
| DO WebSocket | `getByName()` → `fetch()` upgrade → `acceptWebSocket()` → snapshot → broadcast |
| rapidfuzz | `from rapidfuzz import distance` succeeds in `wrangler dev` |
