# Repository Structure — BLT-Hackerhouse Backend

*Designed from: MVP_V1_SPEC.md (20 backend features, 6 architectural layers)*

---

## Design Principles

1. **Layer isolation** — Each architectural layer (ingestion → normalization → identity → state → broadcast) maps to its own package with strict dependency direction. Lower layers never import from higher layers.
2. **Adapters are plugins** — GitLab and BLT integrations are adapter modules within their respective layers. Adding a new platform means adding one adapter per layer, not modifying core logic.
3. **Pure models at the bottom** — Pydantic schemas have zero dependencies on anything else. Every other package may depend on them.
4. **Storage is a shared dependency** — SQLite models and queries are a leaf package consumed by state, identity, and ingestion layers.
5. **API layer wires everything** — FastAPI routes and WebSocket endpoints live at the top and are the only package that imports from every other package.
6. **Tests mirror source** — `tests/unit/` copies the package tree. `tests/integration/` tests cross-package flows. `tests/fixtures/` holds captured payloads.

---

## Directory Tree

```
blt-hackerhouse/
│
├── backend/                          # Python FastAPI application root
│   │
│   ├── pyproject.toml                # Project metadata, dependencies, build config
│   ├── .env.example                  # Template for required environment variables
│   ├── .gitignore
│   │
│   ├── migrations/                   # SQLite DDL — numbered, sequential
│   │   ├── 001_events.sql
│   │   ├── 002_contributors.sql
│   │   ├── 003_avatar_state.sql
│   │   ├── 004_identity_mappings.sql
│   │   ├── 005_poll_cursors.sql
│   │   └── 006_dead_letter_queue.sql
│   │
│   ├── scripts/                      # Dev tooling (not production code)
│   │   ├── migrate.py                # Run pending migrations against SQLite
│   │   ├── seed.py                   # Seed database with sample contributors/events
│   │   └── run_dev.sh                # uvicorn with hot reload
│   │
│   ├── src/                          # Application source
│   │   │
│   │   ├── main.py                   # FastAPI app factory, lifespan events,
│   │   │                             #   register routes, mount WebSocket endpoint,
│   │   │                             #   start BLT polling background task,
│   │   │                             #   start gap-detection background task
│   │   │
│   │   ├── config.py                 # Settings loaded from env vars (pydantic-settings)
│   │   │                             #   GITLAB_WEBHOOK_SECRET, GITLAB_API_TOKEN,
│   │   │                             #   BLT_API_BASE_URL, BLT_API_KEY,
│   │   │                             #   POLL_INTERVAL_SECONDS, DATABASE_PATH
│   │   │
│   │   ├── models/                   # Pydantic schemas — ZERO internal dependencies
│   │   │   ├── __init__.py           # Re-exports all public models
│   │   │   ├── event.py              # Event (the canonical internal DTO)
│   │   │   ├── contributor.py        # Contributor, ContributorSnapshot
│   │   │   ├── room.py               # RoomState, RoomOccupancy, RoomMapEntry
│   │   │   ├── identity.py           # IdentityMapping, IdentityFlag
│   │   │   ├── api.py                # API response/request wrappers:
│   │   │   │                         #   PaginatedResponse, ActivityFeedItem,
│   │   │   │                         #   LeaderboardEntry, StatusResponse
│   │   │   └── websocket.py          # WebSocket message types:
│   │   │                             #   SnapshotMessage, AvatarMoveMessage,
│   │   │                             #   IdentityFlagMessage, LeaderboardUpdateMessage
│   │   │
│   │   ├── core/                     # Shared utilities — depends ONLY on models + config
│   │   │   ├── __init__.py
│   │   │   ├── logging.py            # Structured JSON logger factory
│   │   │   ├── retry.py              # async retry_with_backoff(attempts, base_delay, max_delay, jitter)
│   │   │   ├── deduplication.py      # build_idempotency_key(event), is_duplicate(key, db)
│   │   │   ├── security.py           # constant_time_compare(a, b) — for token verification
│   │   │   └── clock.py              # utc_now() helper
│   │   │
│   │   ├── storage/                  # SQLite access — depends on models + core + config
│   │   │   ├── __init__.py
│   │   │   ├── database.py           # get_db() → aiosqlite connection,
│   │   │   │                         #   run_migrations(db), lifespan setup
│   │   │   ├── queries/              # Raw SQL grouped by table
│   │   │   │   ├── __init__.py
│   │   │   │   ├── events.py         # insert_event, get_events_paginated, get_event_by_idempotency_key
│   │   │   │   ├── contributors.py   # upsert_contributor, get_contributor, get_all_contributors,
│   │   │   │   │                     #   update_score, get_leaderboard
│   │   │   │   ├── avatar_state.py   # upsert_avatar_state, get_avatar_state, get_room_occupancy,
│   │   │   │   │                     #   get_all_avatar_states
│   │   │   │   ├── identity.py       # find_by_platform_id, insert_mapping, update_confidence
│   │   │   │   ├── poll_cursors.py   # get_cursor, upsert_cursor
│   │   │   │   └── dead_letter.py    # insert_dead_letter, get_dead_letter_count, evict_oldest
│   │   │   └── migrations.py         # Discover + apply .sql files in order, track in _migrations table
│   │   │
│   │   ├── ingestion/                # Webhook + polling — depends on models + core + storage
│   │   │   ├── __init__.py
│   │   │   ├── queue.py              # asyncio.Queue[RawPayload] — single in-process queue
│   │   │   ├── gitlab_webhook.py     # verify_gitlab_token(request) → bool
│   │   │   │                         #   parse_gitlab_payload(request) → RawPayload dict
│   │   │   ├── blt_poller.py         # BLTPoller class:
│   │   │   │                         #   async run() — infinite loop, polls every N seconds
│   │   │   │                         #   _poll_bugs() → List[dict]
│   │   │   │                         #   _poll_hunts() → List[dict]
│   │   │   │                         #   _update_cursors()
│   │   │   └── gap_detector.py       # GapDetector class:
│   │   │                             #   async run() — 90s loop
│   │   │                             #   _fetch_gitlab_events(project_id, after_date)
│   │   │                             #   _process_missed_events()
│   │   │
│   │   ├── normalization/            # Event adapters — depends on models + core
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # BaseNormalizer abstract class:
│   │   │   │                         #   normalize(raw: dict) → Event
│   │   │   ├── gitlab.py             # GitLabNormalizer(BaseNormalizer):
│   │   │   │                         #   _map_event_type(payload) → str
│   │   │   │                         #   _extract_fields(payload) → dict
│   │   │   │                         #   normalize(payload) → Event(source="gitlab")
│   │   │   └── blt.py               # BLTNormalizer(BaseNormalizer):
│   │   │                             #   _map_event_type(record) → str
│   │   │                             #   _extract_fields(record) → dict
│   │   │                             #   normalize(record) → Event(source="blt")
│   │   │
│   │   ├── identity/                 # Resolution pipeline — depends on models + core + storage
│   │   │   ├── __init__.py
│   │   │   ├── resolver.py           # IdentityResolver:
│   │   │   │                         #   resolve(event: Event, db) → (contributor_id, confidence)
│   │   │   │                         #   Orchestrates 4 stages in sequence
│   │   │   ├── matchers.py           # exact_match(), levenshtein_match(), jaccard_match()
│   │   │   │                         #   Each returns Optional[(contributor_id, confidence)]
│   │   │   └── unlinked.py           # create_unlinked_identity(event, source, db) → contributor_id
│   │   │
│   │   ├── state/                    # Room routing + state reducer — depends on models + core + storage + identity
│   │   │   ├── __init__.py
│   │   │   ├── room_map.py           # ROOM_MAP dict + DEFAULT_ROOM constant
│   │   │   │                         #   route_event(event_type: str) → (floor, room)
│   │   │   ├── reducer.py            # StateReducer:
│   │   │   │                         #   async process(event: Event, db) → StateChange
│   │   │   │                         #   Steps: resolve identity, persist event,
│   │   │   │   │      update avatar_state, compute occupancy delta
│   │   │   └── pipeline.py           # Pipeline runner:
│   │   │                             #   async run_pipeline(queue, db, reducer, broadcast_hub, leaderboard)
│   │   │                             #   The main processing loop: raw → normalize → resolve → reduce → broadcast
│   │   │
│   │   ├── broadcast/                # WebSocket + leaderboard — depends on models + core + storage + state
│   │   │   ├── __init__.py
│   │   │   ├── hub.py                # BroadcastHub:
│   │   │   │                         #   register(websocket), unregister(websocket)
│   │   │   │                         #   broadcast(message: dict)
│   │   │   │                         #   send_snapshot(websocket, db)
│   │   │   │                         #   connected_clients → int
│   │   │   ├── messages.py           # build_snapshot_message(db) → dict
│   │   │   │                         #   build_avatar_move_message(contributor_id, floor, room, event_type) → dict
│   │   │   │                         #   build_identity_flag_message(suggested_link, contributor_id) → dict
│   │   │   │                         #   build_leaderboard_update_message(contributor_id, score, delta, event) → dict
│   │   │   └── leaderboard.py        # LeaderboardAccumulator:
│   │   │                             #   SCORING_RULES dict
│   │   │                             #   async process_event(event: Event, db) → score_delta
│   │   │                             #   async merge_scores(contributor_a, contributor_b, db)
│   │   │
│   │   └── api/                      # FastAPI routes + WebSocket — depends on ALL packages (wiring layer)
│   │       ├── __init__.py
│   │       ├── router.py             # Creates APIRouter, registers all sub-routers
│   │       ├── webhooks.py           # POST /webhook/gitlab
│   │       │                         #   Validates X-Gitlab-Token, enqueues raw payload
│   │       ├── websocket.py          # WS /ws
│   │       │                         #   Accepts connection, registers in hub, sends snapshot,
│   │       │                         #   keeps connection alive, unregisters on disconnect
│   │       ├── activity.py           # GET /activity — paginated event feed
│   │       ├── leaderboard_routes.py # GET /leaderboard — paginated score list
│   │       ├── status.py             # GET /status — room occupancy + identity stats + pipeline health
│   │       ├── health.py             # GET /health — per-component health check
│   │       └── state_routes.py       # GET /state — HTTP polling fallback snapshot
│   │
│   └── tests/                        # Test suite
│       ├── conftest.py               # Shared fixtures: in-memory SQLite, test client, mock queue
│       ├── fixtures/                 # Captured real payloads for adapter testing
│       │   ├── gitlab/               # GitLab webhook payloads (issue, mr_open, mr_merge, pipeline, note)
│       │   └── blt/                  # BLT-API response payloads (bugs list, hunts list)
│       ├── unit/                     # One test module per source module
│       │   ├── models/
│       │   │   ├── test_event.py
│       │   │   ├── test_websocket_messages.py
│       │   │   └── test_api.py
│       │   ├── core/
│       │   │   ├── test_retry.py
│       │   │   ├── test_deduplication.py
│       │   │   └── test_security.py
│       │   ├── storage/
│       │   │   ├── test_queries_events.py
│       │   │   ├── test_queries_contributors.py
│       │   │   └── test_migrations.py
│       │   ├── ingestion/
│       │   │   ├── test_gitlab_webhook.py
│       │   │   └── test_blt_poller.py
│       │   ├── normalization/
│       │   │   ├── test_gitlab_normalizer.py
│       │   │   └── test_blt_normalizer.py
│       │   ├── identity/
│       │   │   ├── test_resolver.py
│       │   │   └── test_matchers.py
│       │   ├── state/
│       │   │   ├── test_room_map.py
│       │   │   └── test_reducer.py
│       │   ├── broadcast/
│       │   │   ├── test_hub.py
│       │   │   ├── test_messages.py
│       │   │   └── test_leaderboard.py
│       │   └── api/
│       │       ├── test_webhooks.py
│       │       ├── test_websocket.py
│       │       ├── test_activity.py
│       │       ├── test_leaderboard_routes.py
│       │       ├── test_status.py
│       │       └── test_health.py
│       └── integration/
│           ├── test_webhook_to_state.py       # Full chain: webhook → normalize → persist → avatar_state
│           ├── test_webhook_to_websocket.py   # Full chain: webhook → broadcast to connected client
│           ├── test_identity_flow.py          # GitLab + BLT contributor resolution end-to-end
│           ├── test_snapshot_delivery.py      # Connect → receive snapshot
│           ├── test_reconnect_recovery.py     # Disconnect → reconnect → fresh snapshot
│           ├── test_idempotency.py            # Duplicate webhook → single event persisted
│           └── test_polling_fallback.py       # WebSocket down → GET /state returns snapshot
│
├── frontend/                          # (TBD separately — empty for now)
│
├── docker/                            # Docker Compose + Dockerfiles (post-MVP)
│
├── scripts/                           # Repo-level helper scripts
│   └── start.sh                       # One-command: venv setup, migrate, run backend
│
├── docs/                              # Documentation (already exists)
│   ├── MVP_V1_SPEC.md
│   ├── PROPOSAL_BREAKDOWN.md
│   ├── FEATURE_INVENTORY.md
│   ├── ARCHITECTURE_EXTRACTION.md
│   ├── MIGRATION_IMPACT.md
│   ├── POST_MVP_BACKLOG.md
│   └── REPOSITORY_STRUCTURE.md        # This file
│
└── README.md
```

---

## Package Boundaries

### `src/models/` — Pure Data Schemas

**Responsibility**: Define every data structure that crosses package boundaries. No logic, no I/O, no dependencies on any other `src/` package.

**Owns**: `Event`, `Contributor`, `ContributorSnapshot`, `RoomState`, `RoomOccupancy`, `RoomMapEntry`, `IdentityMapping`, `IdentityFlag`, `PaginatedResponse`, `ActivityFeedItem`, `LeaderboardEntry`, `StatusResponse`, `HealthResponse`, `SnapshotMessage`, `AvatarMoveMessage`, `IdentityFlagMessage`, `LeaderboardUpdateMessage`

**May import from**: `pydantic`, `datetime`, `typing`, `uuid`, `enum` (stdlib only)

**Imported by**: Everything.

---

### `src/core/` — Shared Utilities

**Responsibility**: Cross-cutting helpers with no business logic. Logging, retry, deduplication key generation, constant-time comparison, clock.

**Owns**: JSON logger factory, `retry_with_backoff()`, `build_idempotency_key()`, `constant_time_compare()`, `utc_now()`

**May import from**: `models/`, `config`, stdlib (`asyncio`, `hmac`, `hashlib`, `logging`, `random`, `datetime`)

**Must NOT import from**: `storage/`, `ingestion/`, `normalization/`, `identity/`, `state/`, `broadcast/`, `api/`

**Imported by**: `storage/`, `ingestion/`, `normalization/`, `identity/`, `state/`, `broadcast/`, `api/`

---

### `src/storage/` — Database Access

**Responsibility**: SQLite connection management, migration runner, typed query functions. The ONLY package that touches the database directly.

**Owns**: `get_db()`, `run_migrations()`, all query functions in `queries/`, migration SQL files

**May import from**: `models/`, `core/`, `config`, `aiosqlite`

**Must NOT import from**: `ingestion/`, `normalization/`, `identity/`, `state/`, `broadcast/`, `api/`

**Imported by**: `ingestion/` (for gap detector cursors), `identity/` (for resolution lookups), `state/` (for reducer persistence), `broadcast/` (for snapshot + leaderboard reads), `api/` (for REST endpoints that read from DB)

---

### `src/ingestion/` — External Data Intake

**Responsibility**: Receiving data from GitLab and BLT. Webhook verification, polling loops, gap detection. Enqueues raw payloads into the async queue. Does NOT normalize — that's the normalization layer's job.

**Owns**: `async Queue`, GitLab token verification, `BLTPoller`, `GapDetector`

**May import from**: `models/`, `core/`, `storage/` (for poll cursors only), `config`, `httpx`

**Must NOT import from**: `normalization/`, `identity/`, `state/`, `broadcast/`, `api/`

**Imported by**: `api/` (routes call ingestion to enqueue), `main.py` (starts background tasks), `state/pipeline.py` (reads from queue)

---

### `src/normalization/` — Payload → Event Transformation

**Responsibility**: Convert raw platform-specific payloads into the unified `Event` model. One adapter per platform. Isolates all platform-specific field extraction and event-type mapping.

**Owns**: `BaseNormalizer`, `GitLabNormalizer`, `BLTNormalizer`

**May import from**: `models/`, `core/`, `uuid`

**Must NOT import from**: `storage/`, `ingestion/`, `identity/`, `state/`, `broadcast/`, `api/`

**Imported by**: `state/pipeline.py` (calls normalizers for each raw payload)

---

### `src/identity/` — Contributor Resolution

**Responsibility**: Resolve contributor identity across GitLab and BLT. Implements the 4-stage pipeline (exact → Levenshtein → Jaccard → unlinked). Returns `(contributor_id, confidence)` for every event.

**Owns**: `IdentityResolver`, `exact_match()`, `levenshtein_match()`, `jaccard_match()`, `create_unlinked_identity()`

**May import from**: `models/`, `core/`, `storage/` (for identity_mappings + contributors queries), `rapidfuzz`

**Must NOT import from**: `ingestion/`, `normalization/`, `state/`, `broadcast/`, `api/`

**Imported by**: `state/` (reducer calls resolver after normalization)

---

### `src/state/` — Core Pipeline & Room State

**Responsibility**: The central processing loop. Routes events to rooms. Updates avatar state. Coordinates identity resolution, persistence, and broadcast fan-out. This is where `Event` objects become state changes.

**Owns**: `ROOM_MAP`, `DEFAULT_ROOM`, `StateReducer`, `route_event()`, `run_pipeline()`

**May import from**: `models/`, `core/`, `storage/`, `identity/`, `broadcast/` (for hub + leaderboard signals), `normalization/`

**Must NOT import from**: `ingestion/`, `api/` (the pipeline reads from the queue; it doesn't call ingestion directly)

**Imported by**: `main.py` (starts the pipeline runner)

---

### `src/broadcast/` — Real-Time Delivery

**Responsibility**: WebSocket connection management. Fan-out of state changes. Snapshot construction. Leaderboard accumulation and scoring.

**Owns**: `BroadcastHub`, message builders, `LeaderboardAccumulator`, `SCORING_RULES`

**May import from**: `models/`, `core/`, `storage/` (for snapshot + leaderboard reads)

**Must NOT import from**: `ingestion/`, `normalization/`, `identity/`, `state/`, `api/`

**Imported by**: `state/reducer.py` (calls hub to broadcast after state change), `api/websocket.py` (wires hub to FastAPI WebSocket endpoint)

---

### `src/api/` — HTTP + WebSocket Presentation

**Responsibility**: FastAPI route handlers. WebSocket endpoint. This is the ONLY package that imports from every other package — it wires the application together. No business logic here — only request parsing, validation, and delegation.

**Owns**: All `@app.get/post` handlers, WebSocket endpoint, `APIRouter` assembly

**May import from**: EVERY other package (it's the wiring layer)

**Must NOT be imported by**: Any other `src/` package

**Imported by**: `main.py` (mounts the router onto the FastAPI app)

---

### `src/config.py` — Environment Configuration

**Responsibility**: Load and validate all environment variables. Single source of truth for configuration.

**Owns**: `Settings` (pydantic-settings model)

**May import from**: `pydantic_settings`, `pathlib`

**Imported by**: All packages that need configuration.

---

### `src/main.py` — Application Entry Point

**Responsibility**: FastAPI app factory. Lifespan events (database init, start background tasks). Route registration. The `uvicorn` target.

**Owns**: `create_app()`, lifespan context manager, route mounting

**May import from**: `config`, `storage/`, `ingestion/`, `state/`, `api/`

**Must NOT be imported by**: Any package (it's the entry point)

---

## Dependency Rules Summary

```
                    ┌─────────────┐
                    │   api/      │  (wiring layer — imports everything)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ state/   │ │broadcast/│ │ingestion/│
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
        ┌────┴────────────┴────────────┴────┐
        │                                   │
        ▼                                   ▼
  ┌──────────┐                        ┌──────────┐
  │identity/ │                        │normalization/│
  └────┬─────┘                        └─────┬─────┘
       │                                    │
       └──────────┬─────────────────────────┘
                  │
                  ▼
            ┌──────────┐
            │ storage/ │  (SQLite access)
            └────┬─────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
 ┌──────────┐        ┌──────────┐
 │  core/   │        │ models/  │
 └──────────┘        └──────────┘
       │                   │
       └─────────┬─────────┘
                 │
                 ▼
           ┌──────────┐
           │ config   │
           └──────────┘
```

**No circular dependencies. All arrows point downward.**

| Package | May Import From |
|---------|----------------|
| `api/` | Everything |
| `state/` | `models`, `core`, `config`, `storage`, `identity`, `normalization`, `broadcast` |
| `broadcast/` | `models`, `core`, `config`, `storage` |
| `ingestion/` | `models`, `core`, `config`, `storage` |
| `identity/` | `models`, `core`, `config`, `storage` |
| `normalization/` | `models`, `core`, `config` |
| `storage/` | `models`, `core`, `config` |
| `core/` | `models`, `config` |
| `models/` | stdlib, pydantic |
| `config` | pydantic-settings, stdlib |

---

## Module Responsibilities Map

| VF # | Feature | Primary Module |
|------|---------|---------------|
| VF01 | GitLab Webhook Ingestion | `api/webhooks.py` + `ingestion/gitlab_webhook.py` |
| VF02 | BLT Polling Adapter | `ingestion/blt_poller.py` |
| VF03 | Event Deduplication | `core/deduplication.py` + `storage/queries/events.py` |
| VF04 | Unified Event Schema | `models/event.py` |
| VF05 | GitLab Event Normalizer | `normalization/gitlab.py` |
| VF06 | BLT Event Normalizer | `normalization/blt.py` |
| VF07 | Identity Resolution | `identity/resolver.py` + `identity/matchers.py` + `identity/unlinked.py` |
| VF08 | Room Routing Map | `state/room_map.py` |
| VF09 | SQLite Schema | `migrations/*.sql` + `storage/database.py` + `storage/migrations.py` |
| VF10 | Async Queue & State Reducer | `state/pipeline.py` + `state/reducer.py` + `ingestion/queue.py` |
| VF11 | WebSocket Broadcast Hub | `broadcast/hub.py` |
| VF12 | Snapshot on Connect | `broadcast/messages.py` + `broadcast/hub.py` |
| VF13 | Client Resilience | `api/websocket.py` + `api/state_routes.py` |
| VF14 | Activity Feed API | `api/activity.py` + `storage/queries/events.py` |
| VF15 | Maintainer Visibility API | `api/status.py` + `storage/queries/` |
| VF16 | Leaderboard Computation | `broadcast/leaderboard.py` + `api/leaderboard_routes.py` |
| VF17 | Health Endpoints | `api/health.py` |
| VF18 | Backoff & Retry | `core/retry.py` |
| VF19 | Gap Detection | `ingestion/gap_detector.py` |
| VF20 | Dead Letter Handling | `storage/queries/dead_letter.py` + `state/reducer.py` (writes on failure) |

---

## Key Design Decisions

1. **In-process queue (`asyncio.Queue`), not Redis/RabbitMQ** — Sufficient for 50–200 contributors. No external broker dependency. Enables single-command local setup.

2. **`aiosqlite` for async SQLite access** — Python's built-in `sqlite3` is synchronous. `aiosqlite` wraps it for use with `asyncio`. No ORM — raw parameterized SQL with typed query functions.

3. **No ORM** — Query functions in `storage/queries/` return plain dicts. Pydantic models are used for validation at package boundaries. Keeps the data layer explicit and testable.

4. **Normalizers as classes with abstract base** — The `BaseNormalizer` defines the contract. `GitLabNormalizer` and `BLTNormalizer` implement it. Adding Slack later means creating `SlackNormalizer(BaseNormalizer)` — no changes to the pipeline.

5. **Pipeline runner in `state/`, not `main.py`** — The processing loop (`raw → normalize → resolve → reduce → broadcast`) is a standalone async function. `main.py` just starts it as a background task. This makes the pipeline testable independently of FastAPI.

6. **WebSocket hub as a shared singleton** — Created during app startup. Injected into the state reducer (for broadcast) and the WebSocket route handler (for connection management). Avoids circular imports by living in `broadcast/` — a leaf package for both consumers.

7. **Fixture payloads committed to repo** — Real GitLab webhook payloads and BLT-API response samples live in `tests/fixtures/`. Adapter unit tests run against these without mocking external APIs.
