# MVP V1 Specification — BLT-Hackerhouse Backend

*Based on: proposal.pdf, MIGRATION_IMPACT.md, BLT-API analysis, FEATURE_INVENTORY.md, ARCHITECTURE_EXTRACTION.md*

---

## Scope Boundaries

| Included | Excluded |
|----------|----------|
| GitLab webhook ingestion | GitHub (platform migrated) |
| BLT REST polling adapter | Slack (deferred — requirements unvalidated) |
| Event normalization pipeline | Mentorship tracking (out of scope) |
| Cross-platform identity resolution (GitLab ↔ BLT) | Mentor rooms, mentor event types, mentor lifecycle |
| Room/avatar state management | Frontend rendering engine (TBD separately) |
| WebSocket real-time broadcast | Authentication / access control |
| Leaderboard computation | Historical replay or time travel |
| Snapshot delivery on client connect | Discord, Jira, or non-GitLab/BLT integrations |
| HTTP polling fallback | Contributor achievement badges / gamification |
| Health endpoints + structured logging | Docker Compose / CI/CD (post-MVP) |
| Dead letter handling + gap detection | Unit / integration / load tests (post-MVP) |
| Retry with exponential backoff (GitLab) | |

---

## Retained Feature: VF01 — GitLab Webhook Ingestion

### Purpose
Receive real-time push events from GitLab (issues, merge requests, pipeline runs, notes). Verify authenticity via secret token. Reject invalid payloads before any processing occurs. Enqueue valid payloads for normalization.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| HTTP POST to `/webhook/gitlab` | GitLab webhook delivery | JSON body (GitLab webhook payload) |
| `X-Gitlab-Token` header | GitLab webhook configuration | String — compared against `GITLAB_WEBHOOK_SECRET` env var |
| `X-Gitlab-Event` header | GitLab webhook delivery | String — `"Push Hook"`, `"Merge Request Hook"`, `"Issue Hook"`, `"Note Hook"`, `"Pipeline Hook"`, `"Job Hook"` |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| 200 `{"status": "accepted"}` | GitLab (acknowledgement) | JSON |
| 401 `{"detail": "Invalid token"}` | GitLab (rejection) | JSON — returned before any processing |
| Validated raw payload | Internal async queue | Python `dict` of parsed JSON + `source="gitlab"` + `received_at` timestamp |

### Dependencies
- FastAPI application instance
- Environment variable: `GITLAB_WEBHOOK_SECRET`
- Constant-time string comparison (`hmac.compare_digest` or equivalent)

### Data Models
No persistence at this stage. Raw payload passed as dict.

### API Contract

**Request:**
```
POST /webhook/gitlab
Headers:
  Content-Type: application/json
  X-Gitlab-Token: <configured_secret>
  X-Gitlab-Event: "Merge Request Hook" | "Issue Hook" | "Note Hook" | "Pipeline Hook" | "Job Hook" | "Push Hook"

Body: (GitLab webhook payload — varies by event type)
```

**Success Response:**
```json
HTTP 200
{
  "status": "accepted"
}
```

**Error Response:**
```json
HTTP 401
{
  "detail": "Invalid token"
}
```

---

## Retained Feature: VF02 — BLT Polling Adapter

### Purpose
Periodically pull new contributor activity from BLT-API since there is no BLT webhook push support. Polls BLT-API endpoints with a cursor (`last_seen_id`) to fetch only new or updated records. Transforms polled records into raw dicts for normalization. Runs as an isolated background task — failures are logged and skipped without affecting the GitLab pipeline.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| `BLT_API_BASE_URL` | Environment variable | String — e.g. `https://api.owaspblt.org/v2` |
| `BLT_API_KEY` | Environment variable | String — `X-BLT-API-Key` header value |
| Polling interval | Configuration | Integer seconds — default 60 |
| `last_seen_bug_id` | SQLite metadata table | Integer — highest `bugs.id` seen in previous poll |
| `last_seen_hunt_id` | SQLite metadata table | Integer — highest hunt ID seen in previous poll |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Raw BLT records (new bugs) | Internal async queue | List of parsed JSON dicts with `source="blt"` and `received_at` |
| Raw BLT records (hunt activity) | Internal async queue | List of parsed JSON dicts with `source="blt"` and `received_at` |
| Updated `last_seen_bug_id` / `last_seen_hunt_id` | SQLite metadata table | Integer |
| Error logs | Structured logging | Logged and skipped — no pipeline breakage |

### Dependencies
- BLT-API availability (external)
- `BLT_API_KEY` for X-BLT-API-Key header
- SQLite metadata table for cursor storage
- HTTP client (`httpx` or stdlib `urllib` with async)

### Data Models
| Table | Purpose |
|-------|---------|
| `poll_cursors` | Stores `source` (blt_bugs, blt_hunts), `last_seen_id`, `last_polled_at` |

### API Contract

**Polled BLT endpoints (external):**
```
GET {BLT_API_BASE_URL}/bugs?page=1&per_page=50
Headers: X-BLT-API-Key: <blt_api_key>

GET {BLT_API_BASE_URL}/hunts
Headers: X-BLT-API-Key: <blt_api_key>
```

The adapter filters results to only records with `id > last_seen_id` (client-side) since BLT-API does not currently support `?since=` query parameters on these endpoints.

---

## Retained Feature: VF03 — Event Deduplication

### Purpose
Prevent duplicate event processing from webhook retries or overlapping poll windows. Drop events already seen before they reach normalization.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Enqueued raw payload dict | Async queue (from VF01 or VF02) | Dict with `source`, `actor_id`, `event_type`, `timestamp` |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Deduplicated raw payload | Async queue → normalizer | Same dict (passed through) |
| Dropped duplicate (silent) | Log (debug level) | No further processing |

### Dependencies
- SQLite `events` table for idempotency key lookup
- Idempotency key formula: `{source}:{event_type}:{actor_id}:{timestamp}`

### Data Models
Adds a `UNIQUE` constraint on `events.idempotency_key`. A duplicate insert is caught and silently ignored — the event is dropped.

### API Contract
Internal only — no external API surface.

---

## Retained Feature: VF04 — Unified Event Schema

### Purpose
Define the single internal representation that all downstream components operate on. Every source-specific payload is converted into this model before state management, routing, or broadcast.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Deduplicated raw payload dict | Async queue | GitLab webhook JSON or BLT polled JSON |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Validated `Event` object | Async queue → state reducer + SQLite + broadcast hub | Pydantic model instance |

### Dependencies
- Pydantic (validation + serialization)
- Source-specific normalizers (VF05, VF06)

### Data Models

```python
class Event(BaseModel):
    id: str                    # UUID v4 generated at normalization time
    source: Literal["gitlab", "blt"]
    event_type: str            # issue_opened | mr_opened | mr_merged | review_requested |
                               # pipeline_run | note_added | bug_bounty_submitted | hunt_activity
    actor_id: str              # Platform-native user ID (gitlab user.id or blt user.id)
    actor_name: str            # Display name for avatar label (gitlab user.username or blt user.username)
    repository: str            # Project path (gitlab project.path_with_namespace) or BLT hunt.repo
    timestamp: datetime        # UTC, parsed from source event time
    metadata: dict             # Source-specific fields preserved for overlay/activity feed
```

### API Contract
Internal only — `Event` is the canonical data transfer object across all internal components.

---

## Retained Feature: VF05 — GitLab Event Normalizer

### Purpose
Translate GitLab webhook payloads into the unified `Event` model. Isolates all GitLab-specific field extraction and event type mapping so the core pipeline never inspects raw payloads directly.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Deduplicated GitLab webhook payload dict | Async queue | Parsed JSON with `object_kind`, `object_attributes`, `user`, `project` |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| `Event` object (source="gitlab") | Async queue | Pydantic `Event` model |

### Dependencies
- VF04 (Event schema)
- GitLab webhook payload structure knowledge

### Mapping Rules

| GitLab `object_kind` | Condition | Internal `event_type` |
|----------------------|-----------|----------------------|
| `"issue"` | `object_attributes.action` in `("open", "reopen")` | `issue_opened` |
| `"merge_request"` | `object_attributes.action == "open"` | `mr_opened` |
| `"merge_request"` | `object_attributes.action == "merge"` | `mr_merged` |
| `"merge_request"` | `object_attributes.action == "approved"` or review-related | `review_requested` |
| `"pipeline"` | `object_attributes.status` in `("running", "success", "failed")` | `pipeline_run` |
| `"note"` | Comment on issue or MR | `note_added` |
| any | No mapping match | `"unknown"` (routed to Activity Monitor) |

### Field Extraction

| Event Field | GitLab Source Path |
|-------------|-------------------|
| `actor_id` | `user.id` (integer → string) |
| `actor_name` | `user.username` |
| `repository` | `project.path_with_namespace` |
| `timestamp` | `object_attributes.created_at` or `object_attributes.updated_at` |
| `metadata` | Selected fields from `object_attributes` (title, description, url, state, source_branch, target_branch, pipeline status, note body) |

### API Contract
Internal only.

---

## Retained Feature: VF06 — BLT Event Normalizer

### Purpose
Translate BLT-API polled records into the unified `Event` model. Maps bug reports and hunt activity into workflow signals.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Polled BLT bug records | BLT Polling Adapter (VF02) | List of dicts from `GET /bugs` response |
| Polled BLT hunt records | BLT Polling Adapter (VF02) | List of dicts from `GET /hunts` response |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| `Event` object(s) (source="blt") | Async queue | Pydantic `Event` model |

### Dependencies
- VF04 (Event schema)
- VF02 (BLT Polling Adapter)
- BLT-API response structure knowledge (from BLT-API inspection)

### Mapping Rules

| BLT Data Source | Internal `event_type` |
|-----------------|----------------------|
| New bug created (`POST /bugs` result) | `bug_bounty_submitted` |
| Bug status change (polled delta) | `bug_status_change` |
| Hunt listed (`/hunts` — active hunts) | `hunt_activity` |

### Field Extraction

| Event Field | BLT Source Path |
|-------------|----------------|
| `actor_id` | `data.user` (if present) or `data.id` as fallback |
| `actor_name` | `data.user` resolved via BLT `/users/{id}` if needed |
| `repository` | `data.hunt` resolved via BLT `/hunts/{id}` — extract repo name from hunt data |
| `timestamp` | `data.created` or `data.modified` |
| `metadata` | `{ bug_id, url, description, status, hunt_id, domain_name }` |

### API Contract
Internal only.

---

## Retained Feature: VF07 — Identity Resolution Pipeline

### Purpose
Unify contributor identity across GitLab and BLT so the same person appears as one avatar rather than two. Three-stage resolution with confidence scoring. Unresolved identities surfaced explicitly.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| `Event.actor_id` + `Event.actor_name` + `Event.source` | Normalized Event (VF04) | String fields |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Resolved `contributor_id` + `confidence` score | Event metadata (attached before state reducer) | `(str, float)` tuple |
| New unlinked identity record (if no match) | SQLite `contributors` table | Row insert |
| `identity_flag` WebSocket message (if fuzzy match) | WebSocket broadcast hub (VF14) | JSON message |

### Dependencies
- SQLite `contributors` and `identity_mappings` tables (VF09)
- `rapidfuzz` library (Levenshtein + token_set_ratio)
- WebSocket broadcast hub (VF14)

### Stages (executed in order)

**Stage 1 — Exact Platform Match**
- Lookup: `SELECT contributor_id FROM identity_mappings WHERE platform = ? AND platform_user_id = ?`
- On match: return `(contributor_id, 1.0)`
- On no match: proceed to Stage 2

**Stage 2 — Username Similarity (Levenshtein ≤ 2)**
- Compare `actor_name` (lowercased) against all known usernames in `contributors.usernames` JSON array
- `rapidfuzz.distance.Levenshtein.distance(name_a, name_b)`
- On match: return `(contributor_id, 0.75)`, insert new `identity_mappings` row, trigger `identity_flag` WebSocket message
- On no match: proceed to Stage 3

**Stage 3 — Display Name Similarity (Token Set Ratio ≥ 0.6)**
- Compare `actor_name` (lowercased) against all known aliases in `contributors.aliases` JSON array
- `rapidfuzz.fuzz.token_set_ratio(name_a, name_b) / 100`
- On match: return `(contributor_id, 0.60)`, insert new `identity_mappings` row, trigger `identity_flag` WebSocket message
- On no match: proceed to Stage 4

**Stage 4 — Unlinked Fallback**
- `INSERT INTO contributors (display_name, usernames, aliases, platform_ids, is_linked)` with initial values
- `INSERT INTO identity_mappings (platform, platform_user_id, contributor_id, confidence, confirmed_by)` with confidence=0.0
- Return `(new_contributor_id, 0.0)`

### API Contract
Internal only. Identity flag message contract (see VF14 WebSocket section).

---

## Retained Feature: VF08 — Room Routing Map

### Purpose
Route each normalized event type to a room on one of three floors. Defines the spatial mapping that determines avatar positioning.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| `Event.event_type` | Normalized Event (VF04) | String |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| `(floor, room)` tuple | State reducer (VF10) | `(int, str)` |

### Dependencies
- VF04 (Event schema)

### Data Models (static configuration)

```python
ROOM_MAP = {
    # Floor 1: Operations and Infrastructure
    "issue_opened":          {"floor": 1, "room": "issue_triage_desk"},
    "bug_bounty_submitted":  {"floor": 1, "room": "bug_bounty_terminal"},
    "pipeline_run":          {"floor": 1, "room": "cicd_server_room"},
    "deploy_event":          {"floor": 1, "room": "deployment_control_center"},

    # Floor 2: Development Workspace
    "mr_opened":             {"floor": 2, "room": "merge_request_room"},
    "note_added":            {"floor": 2, "room": "contributor_workstations"},

    # Floor 3: Review and Leadership
    "review_requested":      {"floor": 3, "room": "code_review_room"},
    "mr_merged":             {"floor": 3, "room": "release_management_room"},
    "bug_status_change":     {"floor": 3, "room": "security_audit_room"},
    "hunt_activity":         {"floor": 3, "room": "leaderboard_wall"},

    # Fallback
    # All unmapped event types (including "unknown") route here
}

DEFAULT_ROOM = {"floor": 1, "room": "activity_monitor"}
```

**Changes from proposal**: "Mentor Office" → "Release Management Room". "Strategy War Room" → removed. "Pull Request Room" → "Merge Request Room". No mentorship-specific rooms.

### House Layout (retained for backend state only)

| Floor | Rooms |
|-------|-------|
| 3 — Review & Leadership | Code Review Room, Security Audit Room, Release Management Room, Leaderboard Wall, +1 TBD |
| 2 — Development Workspace | Merge Request Room, Contributor Workstations, Pair Programming Area, Debugging Room, Architecture Board |
| 1 — Operations & Infrastructure | Issue Triage Desk, Bug Bounty Terminal, CI/CD Server Room, Deployment Control Center, Activity Monitor |

### API Contract
Internal only.

---

## Retained Feature: VF09 — SQLite Schema

### Purpose
Persistent storage for events, contributor identities, avatar state, identity mappings, poll cursors, and dead letter queue. Single-file SQLite database with migration scripts.

### Dependencies
- SQLite (no external database server)
- Migration scripts (numbered SQL files)

### Data Models

**Table: `events`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | TEXT | PRIMARY KEY (UUID) |
| `source` | TEXT | NOT NULL, CHECK(source IN ('gitlab', 'blt')) |
| `event_type` | TEXT | NOT NULL |
| `actor_id` | TEXT | NOT NULL |
| `actor_name` | TEXT | NOT NULL |
| `contributor_id` | TEXT | FK → contributors(id), nullable (set after resolution) |
| `repository` | TEXT | |
| `timestamp` | TEXT | NOT NULL (ISO 8601) |
| `metadata` | TEXT | JSON blob |
| `idempotency_key` | TEXT | UNIQUE, NOT NULL |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP |

Index: `idx_events_idempotency` on `idempotency_key`.  
Index: `idx_events_contributor` on `contributor_id`.  
Index: `idx_events_timestamp` on `timestamp`.

**Table: `contributors`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | TEXT | PRIMARY KEY (UUID) |
| `display_name` | TEXT | NOT NULL |
| `usernames` | TEXT | JSON array of known usernames — e.g. `["rudra-rps", "Rudra Pratap Singh"]` |
| `aliases` | TEXT | JSON array of display name variations |
| `platform_ids` | TEXT | JSON object — e.g. `{"gitlab_id": "12345", "blt_id": "678"}` |
| `is_linked` | INTEGER | DEFAULT 0 (bool) — 1 when identity confirmed across platforms |
| `score` | INTEGER | DEFAULT 0 — accumulated contributor score |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP |
| `updated_at` | TEXT | DEFAULT CURRENT_TIMESTAMP |

**Table: `avatar_state`**
| Column | Type | Constraints |
|--------|------|-------------|
| `contributor_id` | TEXT | PRIMARY KEY, FK → contributors(id) |
| `floor` | INTEGER | NOT NULL |
| `room` | TEXT | NOT NULL |
| `last_event` | TEXT | Most recent event_type |
| `updated_at` | TEXT | DEFAULT CURRENT_TIMESTAMP |

This table uses `INSERT OR REPLACE` — one row per contributor always reflects current position.

**Table: `identity_mappings`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `platform` | TEXT | NOT NULL, CHECK(platform IN ('gitlab', 'blt')) |
| `platform_user_id` | TEXT | NOT NULL |
| `contributor_id` | TEXT | NOT NULL, FK → contributors(id) |
| `confidence` | REAL | NOT NULL — 0.0 to 1.0 |
| `confirmed_by` | TEXT | nullable — set when maintainer confirms via overlay |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP |

Unique constraint: `(platform, platform_user_id)`.

**Table: `poll_cursors`**
| Column | Type | Constraints |
|--------|------|-------------|
| `source` | TEXT | PRIMARY KEY — e.g. 'blt_bugs', 'blt_hunts' |
| `last_seen_id` | INTEGER | NOT NULL |
| `last_polled_at` | TEXT | |

**Table: `dead_letter_queue`**
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `event_id` | TEXT | Original event UUID |
| `source` | TEXT | |
| `error` | TEXT | Error message / stack trace |
| `attempts` | INTEGER | DEFAULT 1 |
| `last_attempt_at` | TEXT | |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP |

### API Contract
Internal only.

---

## Retained Feature: VF10 — Async Queue & State Reducer

### Purpose
Receive validated and normalized `Event` objects. Persist to SQLite. Compute room/avatar state updates. Fan out to WebSocket broadcast hub and leaderboard accumulator.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| `Event` object | Normalizers (VF05, VF06) via async queue | Pydantic `Event` |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Persisted event row | SQLite `events` table | Row insert |
| Updated avatar state | SQLite `avatar_state` table | INSERT OR REPLACE |
| Room occupancy change | WebSocket broadcast hub (VF14) | Internal signal |
| Leaderboard score update | Leaderboard accumulator (VF16) | Internal signal |

### Dependencies
- SQLite (VF09)
- Room routing map (VF08)
- WebSocket broadcast hub (VF14)
- Leaderboard accumulator (VF16)
- `asyncio.Queue` (Python stdlib — in-process, no external broker)

### Processing Logic

1. Dequeue `Event`
2. Persist to `events` table (idempotency key prevents duplicates)
3. Update `avatar_state` via `INSERT OR REPLACE`:
   ```sql
   INSERT OR REPLACE INTO avatar_state (contributor_id, floor, room, last_event, updated_at)
   VALUES (?, ?, ?, ?, ?)
   ```
   Floor and room come from `ROOM_MAP[event.event_type]` (or `DEFAULT_ROOM` for unknown).
4. Compute new room occupancy counts (query `avatar_state` grouped by room)
5. Push to WebSocket broadcast hub
6. Push to leaderboard accumulator (if event type qualifies for scoring)

### API Contract
Internal only.

---

## Retained Feature: VF11 — WebSocket Broadcast Hub

### Purpose
Manage connected WebSocket clients. Fan out state updates to all subscribed clients. Deliver full state snapshots to newly connected clients.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| State change signal (contributor moved, room occupancy changed, leaderboard updated, identity flag) | State reducer (VF10), Identity resolver (VF07), Leaderboard accumulator (VF16) | Internal signals |
| New WebSocket connection | Client browser | WebSocket handshake |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| `snapshot` message | Newly connected client | JSON (see contract below) |
| `avatar_move` message | All connected clients | JSON |
| `identity_flag` message | All connected clients | JSON |
| `leaderboard_update` message | All connected clients | JSON |

### Dependencies
- FastAPI WebSocket support
- `asyncio` for connection management
- SQLite `avatar_state` and `contributors` tables (for snapshot construction)

### Data Models

**Connection registry**: In-memory `set[WebSocket]` maintained by the hub. Add on connect, remove on disconnect.

### API Contracts

**Server → Client Messages**

**1. Snapshot** (sent once per new connection)
```json
{
  "type": "snapshot",
  "data": {
    "contributors": [
      {
        "id": "contrib_uuid",
        "display_name": "Rudra Pratap Singh",
        "floor": 2,
        "room": "merge_request_room",
        "identity_linked": true,
        "last_event": "mr_opened",
        "score": 42
      }
    ],
    "room_occupancy": {
      "issue_triage_desk": 5,
      "merge_request_room": 3,
      "code_review_room": 1
    },
    "generated_at": "2026-07-15T10:22:00Z"
  }
}
```

**2. Avatar Move** (on each state change)
```json
{
  "type": "avatar_move",
  "contributor_id": "contrib_uuid",
  "floor": 3,
  "room": "code_review_room",
  "event_type": "review_requested",
  "timestamp": "2026-07-15T10:25:00Z"
}
```

**3. Identity Flag** (fuzzy match requires maintainer confirmation)
```json
{
  "type": "identity_flag",
  "suggested_link": {
    "source_a": {"platform": "gitlab", "username": "rudra-rps"},
    "source_b": {"platform": "blt", "user_id": "42"},
    "confidence": 0.75
  },
  "contributor_id": "contrib_uuid"
}
```

**4. Leaderboard Update**
```json
{
  "type": "leaderboard_update",
  "contributor_id": "contrib_uuid",
  "score": 47,
  "delta": 5,
  "last_event": "mr_merged"
}
```

---

## Retained Feature: VF12 — Snapshot on Connect

### Purpose
Provide a complete current-state payload to every newly connected WebSocket client so the frontend can render the full house layout immediately without replaying event history.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| WebSocket connection event | Client browser | WebSocket accept |
| Current `avatar_state` rows | SQLite (VF09) | Query result |
| Current `contributors` rows | SQLite (VF09) | Query result |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| `snapshot` message | Single client (newly connected) | JSON (see VF11 contract) |

### Dependencies
- VF09 (SQLite)
- VF11 (WebSocket hub)

### Construction Query
```sql
SELECT
    c.id, c.display_name, c.is_linked, c.score,
    a.floor, a.room, a.last_event
FROM contributors c
LEFT JOIN avatar_state a ON c.id = a.contributor_id
```

Room occupancy is computed by aggregating `avatar_state` rows grouped by `room`.

### API Contract
See VF11 — `snapshot` message type.

---

## Retained Feature: VF13 — WebSocket Client Resilience

### Purpose
Handle WebSocket disconnection gracefully. Flag out-of-order events. Provide HTTP polling fallback when WebSocket is unavailable.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| WebSocket disconnect | Client browser | Connection drop |
| Out-of-order event detection | State reducer (VF10) | Sequence number gap |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Fresh snapshot on reconnect | Reconnected client | JSON (snapshot) |
| Stale indicator in event stream | All clients | Flag in next broadcast |
| HTTP polling response | Client (fallback path) | JSON snapshot via REST |

### Dependencies
- VF11 (WebSocket hub)
- VF12 (Snapshot on Connect)
- FastAPI REST endpoint for polling fallback

### Behavior Rules

1. **Disconnect** → Client reconnects after 2-second delay. Server sends fresh snapshot automatically.
2. **Out-of-order events** → Each event carries a monotonic sequence number. If a client receives event N+2 before N+1, the activity panel shows a stale indicator for room N+1's position.
3. **WebSocket unavailable > threshold (e.g. 10s)** → Client falls back to `GET /state` REST endpoint returning snapshot JSON.

### API Contract (HTTP polling fallback)

```
GET /state
Response: (same as WebSocket snapshot payload)
```

---

## Retained Feature: VF14 — Activity Feed API

### Purpose
Provide a chronological event history endpoint so the activity feed can display recent contributor actions.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Query params: `?page=1&per_page=50` | HTTP request | Integers |
| Events table | SQLite (VF09) | Query |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Paginated event list | HTTP response | JSON |

### Dependencies
- VF09 (SQLite events table)
- FastAPI REST endpoint

### API Contract

```
GET /activity?page=1&per_page=50

Response:
{
  "success": true,
  "data": [
    {
      "id": "evt_uuid",
      "source": "gitlab",
      "event_type": "mr_opened",
      "actor_name": "rudra-rps",
      "repository": "OWASP-BLT/BLT",
      "timestamp": "2026-07-15T10:22:00Z",
      "metadata": { "title": "Add webhook ingestion layer", "url": "https://gitlab.com/..." }
    }
  ],
  "pagination": { "page": 1, "per_page": 50, "count": 50, "total": 312, "total_pages": 7 }
}
```

---

## Retained Feature: VF15 — Maintainer Visibility API

### Purpose
Provide aggregated ecosystem status and room occupancy data for the maintainer visibility panel.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Room occupancy | SQLite `avatar_state` (aggregated) | Query |
| Identity resolution stats | SQLite `contributors` + `identity_mappings` | Query |
| Event pipeline health | In-memory metrics (events/min, errors, queue depth) | Internal counters |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Ecosystem status payload | HTTP response or WebSocket push | JSON |

### Dependencies
- VF09 (SQLite)
- In-memory metrics collected by ingestion pipeline

### API Contract

```
GET /status

Response:
{
  "success": true,
  "data": {
    "room_occupancy": {
      "issue_triage_desk": 5,
      "merge_request_room": 3,
      "code_review_room": 1,
      ...
    },
    "identity_stats": {
      "total_contributors": 87,
      "linked_contributors": 64,
      "unlinked_contributors": 23,
      "linkage_rate": 0.736
    },
    "pipeline_health": {
      "events_ingested_last_minute": 12,
      "gitlab_webhooks_received": 145,
      "blt_polls_completed": 8,
      "errors_last_hour": 2,
      "queue_depth": 0
    }
  }
}
```

---

## Retained Feature: VF16 — Leaderboard Computation

### Purpose
Compute contributor scores from GitLab and BLT signals. Handle zero-point events. Resolve conflicts when the same contributor has events from both platforms.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Event with scorable event_type | State reducer (VF10) | `Event` object |
| Current contributor score | SQLite `contributors.score` | Integer |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Updated `contributors.score` | SQLite | Integer |
| Leaderboard update signal | WebSocket hub (VF11) | `leaderboard_update` message |

### Dependencies
- VF09 (SQLite `contributors` table)
- VF11 (WebSocket hub)

### Scoring Rules

| Event Type | Points | Notes |
|-----------|--------|-------|
| `mr_merged` | +10 | Merge request merged |
| `mr_opened` | +2 | Merge request opened |
| `review_requested` | +5 | Performing a review |
| `issue_opened` | +3 | Issue creation |
| `bug_bounty_submitted` | +15 | Bug report submitted via BLT |
| `note_added` | +1 | Comment/discussion contribution |
| `pipeline_run` (success) | +2 | Successful CI pipeline |
| `hunt_activity` | +5 | Active hunt participation |

Zero-point events: `pipeline_run` (failed status), unknown events, duplicate events.

### Conflict Resolution
When a contributor exists in both GitLab and BLT with different scores, the contributor's unified score is the sum of scores from both platform identities. Resolution happens at identity linkage time — when two identities are linked, their scores merge.

### API Contract

```
GET /leaderboard?page=1&per_page=20

Response:
{
  "success": true,
  "data": [
    { "contributor_id": "uuid", "display_name": "...", "score": 142, "rank": 1 },
    ...
  ],
  "pagination": { ... }
}
```

WebSocket update contract: see VF11 — `leaderboard_update` message type.

---

## Retained Feature: VF17 — Health Endpoints & Structured Logging

### Purpose
Provide operational visibility into all ingestion paths. Expose health status for monitoring.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Internal health checks | Each pipeline component | Status probes |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Health endpoint response | HTTP | JSON |
| Structured log entries | stdout / log file | JSON lines |

### Dependencies
- FastAPI
- Python `logging` module with JSON formatter

### API Contract

```
GET /health

Response:
{
  "status": "healthy" | "degraded" | "unhealthy",
  "components": {
    "gitlab_webhook": { "status": "healthy", "last_event_at": "ISO8601" },
    "blt_polling": { "status": "healthy", "last_poll_at": "ISO8601", "last_seen_bug_id": 1234 },
    "database": { "status": "healthy", "event_count": 5432 },
    "websocket": { "status": "healthy", "connected_clients": 5 },
    "identity_resolver": { "status": "healthy", "resolution_cache_size": 87 }
  },
  "uptime_seconds": 3600
}
```

---

## Retained Feature: VF18 — Exponential Backoff & Retry (GitLab)

### Purpose
Handle transient failures in outbound requests (GitLab Events API for gap detection, BLT API polling). Retry with exponential backoff and jitter.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Failed HTTP request | GitLab Events API or BLT API call | Exception / non-2xx response |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Retried request | External API | HTTP |
| Dead letter entry (after max retries) | SQLite `dead_letter_queue` | Row insert |
| Structured log entry | Logging | JSON line |

### Dependencies
- `asyncio.sleep`
- SQLite `dead_letter_queue` table (VF09)

### Retry Strategy
- Delays: 1s → 2s → 4s → 8s → max 32s
- Jitter: ±500ms random
- Max attempts: 5
- On exhaustion: event written to `dead_letter_queue` with error context

### API Contract
Internal only.

---

## Retained Feature: VF19 — Gap Detection (GitLab Events API)

### Purpose
Detect events missed during downtime by periodically polling GitLab's Events API and comparing against last known event ID per project.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| `GITLAB_API_TOKEN` | Environment variable | String |
| `last_seen_event_id` per tracked project | SQLite metadata | Integer |
| GitLab Events API | External | REST |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Missed events | Normalization pipeline | Raw event dicts |
| Updated `last_seen_event_id` | SQLite metadata | Integer |

### Dependencies
- GitLab API token with `read_api` scope
- SQLite metadata table (extend `poll_cursors` or add `project_cursors` table)
- VF05 (GitLab normalizer)

### Polling Logic
1. Every 90 seconds, query `GET /api/v4/projects/{id}/events?after={last_seen_date}` for each tracked project
2. Any events with IDs higher than `last_seen_event_id` are processed through the normal pipeline
3. Update cursor

### API Contract
Internal only. External endpoint: GitLab Events API.

---

## Retained Feature: VF20 — Dead Letter Handling

### Purpose
Capture events that cannot be processed after all retries are exhausted. Store with error context for later investigation or replay.

### Inputs
| Input | Source | Format |
|-------|--------|--------|
| Failed Event | Any pipeline stage after max retries (VF18) | `Event` + error context |

### Outputs
| Output | Destination | Format |
|--------|-------------|--------|
| Dead letter row | SQLite `dead_letter_queue` | Row insert |
| Structured log entry (WARNING level) | Logging | JSON line |
| Drop (if queue ≥ 500) | — | Event discarded with CRITICAL log entry |

### Dependencies
- SQLite `dead_letter_queue` table (VF09)

### Queue Limit
Capped at 500 entries. When full, oldest entries evicted (FIFO) before inserting new — logged at CRITICAL.

### API Contract
Internal only.

---

## Architecture Overview (Backend Only)

```
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL SOURCES                         │
│  ┌──────────────┐                    ┌────────────────────┐ │
│  │ GitLab        │                    │ BLT-API            │ │
│  │ Webhook (push)│                    │ REST (poll)        │ │
│  └──────┬───────┘                    └────────┬───────────┘ │
└─────────┼──────────────────────────────────────┼────────────┘
          │                                      │
          ▼                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   INGESTION LAYER                            │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ GitLab Webhook   │  │ BLT Polling  │  │ Deduplication │ │
│  │ (VF01)           │  │ Adapter      │  │ (VF03)        │ │
│  │ X-Gitlab-Token   │  │ (VF02)       │  │ idempotency   │ │
│  └────────┬─────────┘  └──────┬───────┘  └───────┬───────┘ │
└───────────┼───────────────────┼──────────────────┼─────────┘
            │                   │                  │
            ▼                   ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  NORMALIZATION LAYER                         │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ GitLab Normalizer│  │ BLT Normalizer   │                │
│  │ (VF05)           │  │ (VF06)           │                │
│  └────────┬─────────┘  └────────┬─────────┘                │
│           │                     │                           │
│           └──────────┬──────────┘                           │
│                      ▼                                      │
│               ┌─────────────┐                               │
│               │ Event Schema│ (VF04)                        │
│               └──────┬──────┘                               │
└──────────────────────┼──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  IDENTITY LAYER                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Identity Resolution (VF07)                            │  │
│  │ Stage 1: Exact → Stage 2: Levenshtein →               │  │
│  │ Stage 3: Jaccard → Stage 4: Unlinked                  │  │
│  └──────────────────────┬───────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   STATE LAYER                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐    │
│  │ Room Route │  │ Async Queue│  │ SQLite (VF09)       │    │
│  │ Map (VF08) │  │+Reducer    │  │ events              │    │
│  │            │  │ (VF10)     │  │ contributors        │    │
│  └────────────┘  └─────┬──────┘  │ avatar_state        │    │
│                         │         │ identity_mappings   │    │
│                         │         │ poll_cursors        │    │
│                         │         │ dead_letter_queue   │    │
│                         │         └────────────────────┘    │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   BROADCAST LAYER                            │
│  ┌──────────────────────┐  ┌────────────────────────────┐  │
│  │ WebSocket Hub (VF11) │  │ Leaderboard Acc. (VF16)    │  │
│  │ snapshot             │  │ scoring + ranking           │  │
│  │ avatar_move          │  └────────────────────────────┘  │
│  │ identity_flag        │                                   │
│  │ leaderboard_update   │  ┌────────────────────────────┐  │
│  └──────────────────────┘  │ Health + Logging (VF17)    │  │
│                             │ Gap Detection (VF19)       │  │
│  ┌──────────────────────┐  │ Backoff/Retry (VF18)       │  │
│  │ REST API (VF14,VF15) │  │ Dead Letter (VF20)         │  │
│  │ /activity            │  └────────────────────────────┘  │
│  │ /leaderboard         │                                   │
│  │ /status              │                                   │
│  │ /health              │                                   │
│  │ /state (poll f/back) │                                   │
│  └──────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  FRONTEND   │
                   │  (TBD)      │
                   └─────────────┘
```

---

## MVP Features Summary

| # | Feature | Key Deliverable |
|---|---------|----------------|
| VF01 | GitLab Webhook Ingestion | `POST /webhook/gitlab` with token verification |
| VF02 | BLT Polling Adapter | Background task polling `/bugs` + `/hunts` every 60s |
| VF03 | Event Deduplication | Idempotency key enforcement in `events` table |
| VF04 | Unified Event Schema | Pydantic `Event` model |
| VF05 | GitLab Event Normalizer | GitLab `object_kind` → internal event_type mapping |
| VF06 | BLT Event Normalizer | BLT bug/hunt records → internal event_type mapping |
| VF07 | Identity Resolution | 4-stage pipeline: exact → Levenshtein → Jaccard → unlinked |
| VF08 | Room Routing Map | 15 rooms across 3 floors, no mentorship rooms |
| VF09 | SQLite Schema | 6 tables: events, contributors, avatar_state, identity_mappings, poll_cursors, dead_letter_queue |
| VF10 | Async Queue & State Reducer | In-process async queue, INSERT OR REPLACE avatar state |
| VF11 | WebSocket Broadcast Hub | Connection registry, fan-out, 4 message types |
| VF12 | Snapshot on Connect | Full state JSON on new WebSocket connection |
| VF13 | Client Resilience | 2s reconnect + HTTP `/state` polling fallback |
| VF14 | Activity Feed API | `GET /activity` paginated event history |
| VF15 | Maintainer Visibility API | `GET /status` room occupancy + pipeline health |
| VF16 | Leaderboard Computation | Scoring from GitLab + BLT, `GET /leaderboard` |
| VF17 | Health Endpoints | `GET /health` with per-component status |
| VF18 | Backoff & Retry | Exponential backoff 1s→32s with jitter for outbound calls |
| VF19 | Gap Detection | 90s GitLab Events API polling for missed events |
| VF20 | Dead Letter Handling | Capped queue (500 max), structured log on drop |

**Total: 20 features — all backend, all MVP.**
