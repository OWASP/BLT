# Implementation Plan — BLT Hacker House → Cloudflare Workers

**Status:** Ready for preflight spikes  
**Architecture:** FastAPI + Pydantic via `import asgi`, D1 native, Queues, Durable Object  
**Reference:** `docs/design_decision.md`  

---

## Corrected Architecture

```
src/worker.py    → class Default(WorkerEntrypoint): fetch(), scheduled(), queue()
src/app.py       → create_app() → FastAPI (no Worker imports, no lifespan)
src/storage/     → query classes take D1 binding directly (no adapter)
src/ingestion/   → polling functions (not classes), called from scheduled()
src/durable_objects/ → WebSocketRoom, getByName() for routing
```

**Module separation:** `app.py` is pure FastAPI — no `workers` imports. `worker.py` is pure Workers — imports `app` and calls `asgi.fetch(app, request, env)`. No circular dependency.

---

## Preflight Spikes (Run Before Any Phase)

Before committing to the architecture, verify each unknown separately.

### Spike 1: FastAPI ASGI

Create a minimal Worker:
```python
# spike_fastapi/src/worker.py
from workers import WorkerEntrypoint
import asgi
from .app import app

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)
```

```python
# spike_fastapi/src/app.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

```bash
cd spike_fastapi
pywrangler dev
curl http://localhost:8787/health  # Expect {"status": "healthy"}
```

**Verify:** Route decorators work. Middleware works. Error handlers work. Pydantic response models serialize correctly.

### Spike 2: Static Assets

```toml
# wrangler.toml
[assets]
directory = "../UI"
```

```bash
pywrangler dev
curl http://localhost:8787/avatars/avatar-0.png  # Expect PNG binary
curl http://localhost:8787/activity_feed.html  # Expect HTML
curl http://localhost:8787/assets/css/...  # Expect CSS
```

**Verify:** All 5 HTML pages load. All 10 avatars load. CSS/JS assets load. Paths match legacy.

### Spike 3: D1 Query

```python
async def fetch(self, request):
    result = await self.env.HH_DB.prepare("SELECT 1 AS one").first()
    return Response.json({"ok": bool(result)})
```

```bash
pywrangler dev
curl http://localhost:8787/
```

**Verify:** Query works. JsProxy → Python conversion works.

### Spike 4: Queue Send/Consume

```python
async def fetch(self, request):
    await self.env.TEST_QUEUE.send({"test": True})
    return Response.json({"queued": True})

async def queue(self, batch):
    for msg in batch.messages:
        print("Received:", msg.body)
        msg.ack()
```

**Verify:** Message sent in `fetch()` arrives in `queue()`. Body is a dict, not a JSON string. Ack works.

### Spike 5: DO WebSocket Prototype

Build the full flow: Worker intercepts `/ws` → `getByName("test")` → DO `fetch()` → `WebSocketPair.new()` → `acceptWebSocket()` → send snapshot → return 101.

**Verify:**
- `getByName()` resolves DO
- `do_stub.fetch(request.url, {method, headers})` triggers DO's `fetch()`
- `WebSocketPair.new()` creates valid pair
- `acceptWebSocket()` accepts server side
- `ctx.getWebSockets()` returns connected clients
- DO survives hibernation (client stays connected after idle)

### Spike 6: rapidfuzz Packaging

```python
# Minimal Worker with rapidfuzz
from rapidfuzz import distance
result = distance.Levenshtein.distance("hello", "hallo")
```

```bash
pywrangler dev
# Check if import succeeds or raises ImportError
```

**Verify:** Import succeeds. Sample comparison works. CPU time logged.

---

## Phase 0 — Lock Contracts and Inventory

**Goal:** Capture every API response and WebSocket message the frontend depends on. Document all static asset paths. Exit with written compatibility checklist.

**Keep `scripts/run_dev.py`** — needed to run the legacy backend for fixture capture.

### Tasks

1. **Start legacy backend**
   ```bash
   cd backend && uv run python scripts/run_dev.py
   ```

2. **Capture REST fixtures**
   ```bash
   mkdir -p docs/fixtures
   curl http://localhost:8000/health        > docs/fixtures/health.json
   curl http://localhost:8000/status        > docs/fixtures/status.json
   curl "http://localhost:8000/activity?page=1&per_page=50" > docs/fixtures/activity.json
   curl "http://localhost:8000/leaderboard?page=1&per_page=20" > docs/fixtures/leaderboard.json
   curl http://localhost:8000/state         > docs/fixtures/state.json
   curl -X POST http://localhost:8000/webhook/gitlab \
     -H "X-Gitlab-Token: test-token" \
     -H "Content-Type: application/json" \
     -d @docs/fixtures/sample_webhook.json   > docs/fixtures/webhook_response.json
   ```

3. **Capture WebSocket message shapes**
   - Connect WebSocket client
   - Capture snapshot message (first after connect)
   - Simulate webhook → capture avatar_move
   - Capture leaderboard_update on score change
   - Capture identity_flag on fuzzy match
   - Save to `docs/fixtures/ws_*.json`

4. **Inventory static assets (use actual paths)**
   ```
   /index.html
   /activity_feed.html
   /leaderboard.html
   /status_health.html
   /threejs.html
   /assets/css/*
   /assets/js/*
   /avatars/avatar-0.png through avatar-9.png
   ```
   `/index.html` serves as the homepage (HackerHouse dashboard).

5. **Write compatibility checklist** (`docs/fixtures/COMPATIBILITY.md`)
   - Every endpoint path and HTTP method
   - Every response field with type
   - Every WebSocket message type with fields
   - Statement: "Contracts cannot change without explicit frontend coordination"

### Exit gate

`docs/fixtures/COMPATIBILITY.md` exists. All 6 REST fixtures captured. All 4 WebSocket message fixtures captured. Static asset paths documented. rapidfuzz spike result known.

---

## Phase 1 — Stateless HTTP + Native D1 (Read-Only)

**Goal:** Deploy a Worker that serves the UI via `[assets]`, responds to all REST read endpoints from D1, and has no process-level state. FastAPI routes stay in `src/api/routes.py`. Query layer refactored to D1 native API.

### Tasks

1. **Split `src/main.py` into `src/app.py` and `src/worker.py`**

   **`src/app.py`** (FastAPI — no Worker imports):
   ```python
   from fastapi import FastAPI, Request
   from .api.routes import router
   from .storage.queries import (
       EventQueries, ContributorQueries, AvatarStateQueries,
       CursorQueries, DeadLetterQueries,
   )

   def create_app() -> FastAPI:
       app = FastAPI()
       app.include_router(router)
       return app

   app = create_app()

   # Dependency: get D1 binding from request scope (set by asgi.fetch)
   async def get_db(request: Request):
       return request.scope["env"].HH_DB
   ```

   **`src/worker.py`** (Workers — no FastAPI imports, only imports `app`):
   ```python
   from workers import WorkerEntrypoint
   import asgi
   from urllib.parse import urlparse
   from .app import app

   class Default(WorkerEntrypoint):
       async def fetch(self, request):
           path = urlparse(str(request.url)).path

           if path == "/ws" or path.startswith("/ws?"):
               return self._ws_stub(request)  # Stub — Phase 5

           # ASGI translates Worker Request → FastAPI
           return await asgi.fetch(app, request, self.env)

       async def scheduled(self, controller, env, ctx):
           pass  # Phase 4

       async def queue(self, batch):
           pass  # Phase 4

       def _ws_stub(self, request):
           from workers import Response
           return Response.new("WebSocket not available yet", status=501)
   ```

2. **Remove from old `src/main.py`:**
   - `lifespan` context manager (entire block)
   - `StaticFiles` mounts
   - `@app.websocket("/ws")`
   - `app.state.*` assignments
   - `settings` imports at module level (move to per-request resolution — see task 6)
   - Keep `from .api.routes import router` and `app.include_router(router)`

3. **Refactor `src/storage/queries.py` to native D1**

   Each query class takes the D1 binding directly — NOT a `Database` wrapper:

   ```python
   class EventQueries:
       def __init__(self, db):
           self._db = db

       async def insert(self, event):
           stmt = self._db.prepare("""
               INSERT OR IGNORE INTO events (
                   id, source, event_type, actor_id, actor_name,
                   contributor_id, repository, timestamp, metadata, idempotency_key
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           """).bind(
               str(event.id), event.source, event.event_type,
               event.actor_id, event.actor_name,
               str(event.contributor_id) if event.contributor_id else None,
               event.repository, event.timestamp.isoformat(),
               dumps_json(event.metadata), event.idempotency_key,
           )
           await stmt.run()
           id_result = await self._db.prepare(
               "SELECT last_insert_rowid() AS id"
           ).first()
           return id_result.to_py()["id"] if id_result else None

       async def list_activity(self, page, per_page):
           offset = (page - 1) * per_page
           total_row = await self._db.prepare(
               "SELECT COUNT(*) AS total FROM events"
           ).first()
           total = total_row.to_py()["total"] if total_row else 0

           result = await self._db.prepare("""
               SELECT * FROM events
               ORDER BY timestamp DESC, sequence_number DESC
               LIMIT ? OFFSET ?
           """).bind(per_page, offset).all()
           rows = [r.to_py() for r in (result.results or [])]
           return [_row_to_event(r) for r in rows], total
   ```

   Apply same refactor to: `ContributorQueries`, `AvatarStateQueries`, `IdentityQueries`, `CursorQueries`, `DeadLetterQueries`.

4. **Remove `src/storage/connection.py`** completely. No `Database` class. No `get_database()` singleton. No WAL pragmas. No file paths.

5. **Update route handlers to use `get_db` dependency**

   ```python
   # In src/api/routes.py
   from .storage.queries import EventQueries

   @router.get("/activity")
   async def list_activity(
       request: Request,
       db = Depends(get_db),  # D1 binding injected from request.scope
       page: int = Query(default=1, ge=1),
       per_page: int = Query(default=50, ge=1, le=100),
   ):
       events, total = await EventQueries(db).list_activity(page, per_page)
       ...
   ```

6. **Resolve configuration per-request**

   pydantic-settings `Settings` class reads from `os.environ`. In Workers, Wrangler injects secrets/vars into `os.environ` via the ASGI adapter. Verify in preflight Spike 1. If this doesn't work, create a dependency that reads from `request.scope["env"]`:

   ```python
   async def get_settings(request: Request):
       env = request.scope["env"]
       return Settings(
           gitlab_webhook_secret=getattr(env, "GITLAB_WEBHOOK_SECRET", ""),
           gitlab_api_token=getattr(env, "GITLAB_API_TOKEN", ""),
           blt_api_key=getattr(env, "BLT_API_KEY", ""),
           blt_api_base_url=getattr(env, "BLT_API_BASE_URL", ""),
           websocket_auth_token=getattr(env, "WEBSOCKET_AUTH_TOKEN", ""),
           ...
       )
   ```

7. **Create `wrangler.toml`** in `backend/`:

   ```toml
   name = "hackerhouse"
   main = "src/worker.py"
   compatibility_date = "2025-07-01"
   compatibility_flags = ["python_workers"]

   [assets]
   directory = "../UI"

   [[d1_databases]]
   binding = "HH_DB"
   database_name = "hackerhouse"
   database_id = "<from wrangler d1 create>"
   migrations_dir = "migrations"

   [vars]
   BLT_API_BASE_URL = "https://api.owaspblt.org/v2"
   GITLAB_TRACKED_PROJECT_IDS = ""
   LOG_LEVEL = "INFO"
   BLT_POLL_INTERVAL_SECONDS = "60"
   GITLAB_POLL_INTERVAL_SECONDS = "90"
   GITLAB_LOOKBACK_MINUTES = "30"

   [observability.logs]
   enabled = true
   invocation_logs = true
   persist = true
   ```

8. **Set up secrets**
   ```bash
   wrangler secret put GITLAB_WEBHOOK_SECRET
   wrangler secret put GITLAB_API_TOKEN
   wrangler secret put BLT_API_KEY
   wrangler secret put WEBSOCKET_AUTH_TOKEN
   ```

9. **Apply migrations to D1**
   ```bash
   wrangler d1 migrations apply hackerhouse --local
   wrangler d1 migrations apply hackerhouse --remote --env staging
   ```

10. **Add `health_state` migration**
    ```sql
    -- migrations/0002_health_state.sql
    CREATE TABLE IF NOT EXISTS health_state (
        component TEXT NOT NULL,
        field     TEXT NOT NULL,
        value     TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (component, field)
    );
    ```

11. **Deploy to staging**
    ```bash
    pywrangler deploy --env staging
    ```

12. **Verify UI against staging**
    - Open each HTML page: `/activity_feed.html`, `/leaderboard.html`, etc. (homepage at `/`)
    - Verify all 10 avatars load at `/avatars/avatar-N.png`
    - Verify CSS/JS assets load at `/assets/css/*` and `/assets/js/*`
    - Verify API endpoints return data matching Phase 0 fixtures

### Exit gate

Worker serves UI + REST read endpoints from D1. All paths match legacy. Payloads match fixtures. `pywrangler deploy` succeeds. No `app.state`, no `lifespan`, no process-level state.

---

## Phase 2 — Queue + Cron Pipeline

**Goal:** Webhook handler enqueues to Queue. Consumer processes events through full pipeline. Cron pollers replace background tasks. Health/status read from D1.

### Tasks

1. **Create and bind Queue**
   ```bash
   wrangler queues create pipeline-events
   ```
   ```toml
   [[queues.producers]]
   binding = "PIPELINE_QUEUE"
   queue = "pipeline-events"

   [[queues.consumers]]
   queue = "pipeline-events"
   max_batch_size = 10
   max_batch_timeout = 5
   max_retries = 5
   ```

2. **Update webhook handler to enqueue**
   ```python
   @router.post("/webhook/gitlab")
   async def gitlab_webhook(request: Request, ...):
       # Verification unchanged
       event = normalize_gitlab_payload(payload)

       # Enqueue JSON-compatible dict (not a string)
       env = request.scope["env"]
       await env.PIPELINE_QUEUE.send(event.model_dump(mode="json"))

       return {"status": "accepted"}
   ```

3. **Implement consumer in `src/worker.py`**

   ```python
   async def queue(self, batch):
       for msg in batch.messages:
           try:
               event_data = msg.body  # Already a dict
               event = Event(**event_data)
               await process_pipeline_event(event, self.env)
               msg.ack()
           except RecoverableError:
               msg.retry()
           except TerminalError as exc:
               await record_dead_letter(event_data, str(exc), self.env)
               msg.ack()
   ```

4. **Port pipeline to standalone function** (`src/pipeline/processor.py`)
   ```python
   async def process_pipeline_event(event: Event, env):
       db = env.HH_DB

       # 1. Dedup + persist
       inserted = await EventQueries(db).insert(event)
       if not inserted:
           return  # Duplicate — skip silently

       # 2. Identity resolution
       resolver = IdentityResolver(db)
       result = await resolver.resolve(event)

       # 3. Avatar state
       room = resolve_room(event.event_type)
       await AvatarStateQueries(db).upsert(AvatarState(
           contributor_id=result.contributor_id, floor=room.floor,
           room=room.room, last_event=event.event_type,
       ))

       # 4. Leaderboard
       delta = SCORING_RULES.get(event.event_type, 0)
       if event.event_type == "pipeline_run" and event.metadata.get("status") != "success":
           delta = 0
       if delta:
           contributor = await ContributorQueries(db).get(result.contributor_id)
           if contributor:
               contributor.add_score(delta)
               await ContributorQueries(db).upsert(contributor)

       # 5. Broadcast (Phase 5 — stub for now)
       # await broadcast_to_do(env, ...)

       # 6. Record health event
       await update_health_state(db, "pipeline", "last_event_at", utc_now_iso())
   ```

5. **Drop global sequence counter**
   - Remove `_sequence` / `_lock` from pipeline
   - Events ordered by `timestamp` + `idempotency_key` instead
   - `sequence_number` column becomes optional/best-effort or removed

6. **Implement error classification**
   ```python
   class RecoverableError(Exception): pass   # D1 transient → retry
   class TerminalError(Exception): pass      # Validation/invariant → DLQ + ack
   ```

7. **Add cron trigger**
   ```toml
   [triggers]
   crons = ["*/5 * * * *"]
   ```

8. **Implement `scheduled()` handler**
   ```python
   async def scheduled(self, controller, env, ctx):
       db = env.HH_DB
       # Poll BLT
       blt_count = await poll_blt_source(env)
       # Poll GitLab gaps
       gitlab_count = await poll_gitlab_gaps(env)
       logger.info("scheduled complete", extra={"blt": blt_count, "gitlab": gitlab_count})
   ```

9. **Port pollers to standalone functions**

   Move from class-based to function-based. Keep `httpx.AsyncClient` — same HTTP fetching logic. Publish via `env.PIPELINE_QUEUE.send(event.model_dump(mode="json"))`. Write health state to D1 after each cycle:

   ```python
   async def poll_blt_source(env):
       db = env.HH_DB
       cursor = await CursorQueries(db).get("blt_bugs")
       last_seen = cursor[0] if cursor else 0

       async with httpx.AsyncClient(
           base_url=getattr(env, "BLT_API_BASE_URL", ""),
           headers={"X-BLT-API-Key": getattr(env, "BLT_API_KEY", "")},
       ) as client:
           records, new_high = await fetch_all_pages(client, "/bugs", last_seen)

       for record in records:
           event = normalize_blt_bug(record)
           await env.PIPELINE_QUEUE.send(event.model_dump(mode="json"))

       if new_high > last_seen:
           await CursorQueries(db).upsert("blt_bugs", new_high)

       # Persist health state
       await upsert_health_state(db, "blt_polling", "last_poll_at", utc_now_iso())
       await upsert_health_state(db, "blt_polling", "last_cursor", str(new_high))

       return len(records)
   ```

   Same pattern for `poll_gitlab_gaps()`.

10. **Update `/health` to read from D1**
    ```python
    @router.get("/health")
    async def health(request: Request, db = Depends(get_db)):
        blt_last_poll = await read_health_state(db, "blt_polling", "last_poll_at")
        blt_last_error = await read_health_state(db, "blt_polling", "last_error")
        gitlab_last_poll = await read_health_state(db, "gitlab_detector", "last_poll_at")
        event_count = await EventQueries(db).count()

        return HealthResponse(
            status="healthy",
            components={
                "gitlab_webhook": {"status": "healthy", "last_event_at": ...},
                "gitlab_gap_detector": {"status": "healthy", "last_poll_at": gitlab_last_poll, ...},
                "blt_polling": {"status": "healthy", "last_poll_at": blt_last_poll, ...},
                "database": {"status": "healthy", "event_count": event_count},
                "websocket": {"status": "healthy", "connected_clients": 0},  # Until Phase 5
                "identity_resolver": {"status": "healthy", ...},
            },
            uptime_seconds=0.0,
        )
    ```

11. **Update `/status` — keep `queue_depth`**
    ```python
    @router.get("/status")
    async def status(request: Request, db = Depends(get_db)):
        ...
        return StatusResponse(data=StatusData(
            ...
            pipeline_health=PipelineHealth(
                ...
                queue_depth=None,  # Preserved field; value from Queue API when available
            ),
        ))
    ```

12. **Remove deleted files:**
    - `src/state/queue.py`
    - `src/state/pipeline.py` (moved to `src/pipeline/processor.py`)

### Exit gate

Webhook → Queue → D1 → activity feed visible. Cron polls enqueue events. Health/status read from D1. Worker restart doesn't lose queued work or poll progress.

---

## Phase 3 — Durable Object WebSockets

**Goal:** WebSocket connections survive Worker restarts. Pipeline broadcasts reach connected clients. All message formats match Phase 0 fixtures. `/state` fallback remains.

### Tasks

1. **Create `src/durable_objects/websocket_room.py`**

   ```python
   from workers import DurableObject
   import json
   from urllib.parse import urlparse

   class WebSocketRoom(DurableObject):
       def __init__(self, state, env):
           self.ctx = state
           self.env = env

       async def fetch(self, request):
           path = urlparse(str(request.url)).path

           if path == "/internal/broadcast":
               body = await request.json()
               for ws in self.ctx.getWebSockets():
                   try:
                       ws.send(json.dumps(body))
                   except Exception:
                       pass
               return Response("ok", status=200)

           # WebSocket upgrade
           from workers import WebSocketPair
           pair = WebSocketPair.new()
           server_ws, client_ws = pair[0], pair[1]

           self.ctx.acceptWebSocket(server_ws)

           # Build snapshot from D1
           db = self.env.HH_DB
           contributors = await ContributorQueries(db).list_all()
           avatars = await AvatarStateQueries(db).list_all()
           occupancy = await AvatarStateQueries(db).occupancy()
           snapshot = build_snapshot(contributors, avatars, occupancy)
           server_ws.send(json.dumps(snapshot, default=str))

           from workers import Response
           return Response(None, status=101, webSocket=client_ws)

       async def webSocketMessage(self, ws, message):
           pass  # Client keepalive only

       async def webSocketClose(self, ws, code, reason, wasClean):
           pass  # Hibernation tracks via ctx.getWebSockets()
   ```

2. **Register DO in `wrangler.toml`**
   ```toml
   [[durable_objects.bindings]]
   name = "WEBSOCKET_ROOM"
   class_name = "WebSocketRoom"
   script_name = "hackerhouse"

   [[migrations]]
   tag = "v1"
   new_classes = ["WebSocketRoom"]
   ```

3. **Implement WebSocket interception in `src/worker.py`**
   ```python
   async def fetch(self, request):
       path = urlparse(str(request.url)).path
       if path == "/ws" or path.startswith("/ws?"):
           return await self._handle_ws(request)
       return await asgi.fetch(app, request, self.env)

   async def _handle_ws(self, request):
       # Token auth
       parsed = urlparse(str(request.url))
       from urllib.parse import parse_qs
       token = (parse_qs(parsed.query).get("token") or [None])[0]
       expected = getattr(self.env, "WEBSOCKET_AUTH_TOKEN", "")
       if not token or not hmac.compare_digest(token, expected):
           return Response("Unauthorized", status=401)

       # Route to DO via getByName()
       do_stub = self.env.WEBSOCKET_ROOM.getByName("global-room")
       return await do_stub.fetch(request.url, {
           "method": "GET",
           "headers": dict((k.lower(), v) for k, v in request.headers.items()),
       })
   ```

4. **DO stub.fetch() request format:**
   The exact URL, method, headers dict format for `do_stub.fetch()` must be verified in the preflight spike (Spike 5). Adjust based on actual behavior.

5. **Wire pipeline → DO broadcast**

   In `process_pipeline_event()`, after leaderboard update:
   ```python
   do_stub = env.WEBSOCKET_ROOM.getByName("global-room")
   move_msg = build_avatar_move(event, room.floor, room.room)
   await do_stub.fetch(
       "http://do.internal/internal/broadcast",
       {"method": "POST", "body": json.dumps(move_msg)},
   )
   ```

   If identity flag was produced:
   ```python
   flag_msg = build_identity_flag(result.flag)
   await do_stub.fetch(
       "http://do.internal/internal/broadcast",
       {"method": "POST", "body": json.dumps(flag_msg)},
   )
   ```

   If score changed:
   ```python
   score_msg = build_leaderboard_update(contributor.id, contributor.score, delta, event.event_type)
   await do_stub.fetch(
       "http://do.internal/internal/broadcast",
       {"method": "POST", "body": json.dumps(score_msg)},
   )
   ```

6. **Keep `/state` as HTTP fallback** — unchanged from Phase 1-2.

7. **Test WebSocket flow**
   - Connect with valid token → receive snapshot
   - Send webhook → receive avatar_move broadcast
   - Disconnect → reconnect → fresh snapshot
   - Invalid token → HTTP 401 (not WS close frame)
   - Missing token → HTTP 401
   - `/state` polling fallback returns current snapshot

### Exit gate

WebSocket connections survive hibernation. All four message types match fixtures. `/state` fallback works. `getByName()` routing proven.

---

## Phase 4 — Testing

**Goal:** All three levels pass. Staging fully isolated from production.

### Tasks

1. **Unit tests** — adapt existing `backend/tests/`
   - Mock D1 binding: `MockD1Binding` with `prepare().bind().all()` returning preset data
   - Mock Queue binding: `MockQueue` capturing `.send()` calls
   - Mock DO stub: `MockDOStub` capturing broadcast calls
   - Run: `uv run pytest`

2. **Integration tests** — new `tests/integration/`
   - `wrangler dev` + local D1
   - Apply migrations: `wrangler d1 migrations apply hackerhouse --local`
   - Test webhook → Queue → consumer → D1
   - Test cron handler → Queue → D1
   - Test DO broadcast

3. **Browser acceptance**
   - Load all 5 HTML pages from staging URL
   - Verify API data renders (activity, leaderboard, status, health, state)
   - Verify empty states, error states, pagination
   - Connect WebSocket → verify snapshot + live updates + reconnect
   - Test `/state` fallback

4. **Staging environment**
   ```bash
   wrangler d1 create hackerhouse-staging
   wrangler queues create pipeline-events-staging
   wrangler secret put GITLAB_WEBHOOK_SECRET --env staging
   wrangler secret put GITLAB_API_TOKEN --env staging
   wrangler secret put BLT_API_KEY --env staging
   wrangler secret put WEBSOCKET_AUTH_TOKEN --env staging
   pywrangler deploy --env staging
   ```

### Exit gate

All unit tests pass. Integration tests cover webhook-to-queue-to-D1 and cron-to-queue-to-D1. Browser acceptance passes against staging.

---

## Phase 5 — Production Deploy

**Goal:** Production Worker deployed. Git Builds CI/CD configured (without auto-migration). Runbooks documented.

### Tasks

1. **Production secrets**
   ```bash
   wrangler secret put GITLAB_WEBHOOK_SECRET
   wrangler secret put GITLAB_API_TOKEN
   wrangler secret put BLT_API_KEY
   wrangler secret put WEBSOCKET_AUTH_TOKEN
   ```

2. **Protected migration step** (manual — not in Git Builds)
   ```bash
   wrangler d1 migrations apply hackerhouse --remote
   ```

3. **Deploy**
   ```bash
   pywrangler deploy
   ```

4. **Verify production**
   - All HTML pages load
   - API responses match fixtures
   - WebSocket connects + broadcasts
   - Health/status healthy
   - `wrangler tail` shows no errors

5. **Configure Git Builds** (Cloudflare Dashboard, not wrangler.toml)
   - Root directory: `backend/`
   - Build command: (none — Python Workers are deployed via pywrangler)
   - Deploy command: `pywrangler deploy`
   - Branch builds: deploy previews
   - **Production branch: do NOT run migrations in Git Builds.** Migrations are a separate, protected step.

6. **Document runbooks** (`docs/RUNBOOKS.md`)
   - Deploy: `pywrangler deploy`
   - Migrate: `wrangler d1 migrations apply hackerhouse --remote`
   - Rollback: `wrangler rollback`
   - Secret rotation: `wrangler secret put KEY`, `pywrangler deploy`
   - Logs: `wrangler tail`
   - Queue health: `wrangler queues view pipeline-events`

### Exit gate

Production deployed. Manual migration step documented. Rollback tested. Runbooks written.

---

## File Manifest

### Created
```
backend/src/worker.py              ← Default(WorkerEntrypoint): fetch, scheduled, queue
backend/src/durable_objects/
  __init__.py
  websocket_room.py                ← WebSocketRoom(DurableObject)
backend/src/pipeline/
  __init__.py
  processor.py                     ← process_pipeline_event() standalone function
backend/wrangler.toml              ← Cloudflare configuration
backend/migrations/0002_health_state.sql
docs/design_decision.md
docs/implementation_plan.md
docs/fixtures/                     ← API contract captures
docs/RUNBOOKS.md
```

### Modified
```
backend/src/main.py → src/app.py   ← Removed lifespan, StaticFiles, WS, app.state. Added get_db dep.
backend/src/storage/queries.py     ← Refactored to D1 native API (takes binding, not Database)
backend/src/api/routes.py          ← Added Depends(get_db); webhook enqueues to Queue; health reads from D1 tables
backend/src/ingestion/blt_poller.py   ← Class → function; env.PIPELINE_QUEUE.send(); health state to D1
backend/src/ingestion/gap_detector.py ← Class → function; same pattern
backend/pyproject.toml             ← Added workers-py; removed uvicorn, aiosqlite; keep rapidfuzz if spike passes
```

### Deleted
```
backend/src/storage/connection.py  ← No Database class. No WAL. No file paths.
backend/src/state/queue.py         ← Replaced by Cloudflare Queues
backend/src/state/pipeline.py      ← Moved to src/pipeline/processor.py
backend/src/broadcast/hub.py       ← Replaced by Durable Object
```

### Unchanged
```
backend/src/normalization/         ← All files
backend/src/identity/              ← Unchanged (if rapidfuzz spike passes)
backend/src/core/                  ← security, dedup, logging, retry
backend/src/broadcast/messages.py  ← Message builders
backend/src/broadcast/leaderboard.py ← Scoring rules
backend/src/state/room_map.py      ← Room routing
backend/src/models/                ← All Pydantic models
backend/src/api/websocket.py       ← Unused (replaced by DO); can delete after Phase 3
backend/tests/                     ← Adapted for D1/Queue/DO mocks
backend/scripts/run_dev.py         ← KEPT for Phase 0 fixture capture; can delete after
UI/                                ← All static files unchanged
```

---

## Revised Phase Order Summary

| Phase | What | Exit Gate |
|---|---|---|
| **Spikes** | Prove ASGI, assets, D1, Queue, DO, rapidfuzz | All 6 spikes pass |
| **0** | Capture fixtures, inventory assets | COMPATIBILITY.md written |
| **1** | Stateless HTTP + native D1 (read-only) | Worker serves UI + API from D1. No lifespan. |
| **2** | Queue + cron pipeline | Webhook→Queue→D1 works. Cron polls. |
| **3** | DO WebSockets | WS survives hibernation. Broadcasts work. |
| **4** | Testing | All 3 levels pass. Staging isolated. |
| **5** | Production | Deployed + runbooks written. |

Every phase keeps the UI usable. No big-bang rewrite.
