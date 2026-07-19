# Architecture Extraction — BLT-Hackerhouse

*Extracted from: Rudra Pratap Singh — BLT-Hackerhouse GSoC Proposal*

---

## Components

### 1. Event Ingestion Service
- **GitHub webhook endpoint** — `POST /webhook/github` on FastAPI. Receives raw payloads, verifies HMAC-SHA256 signature against `GITHUB_SECRET`. Rejects invalid signatures with 401 before any processing. Verified payloads enqueued.
- **Slack event endpoint** — `POST /webhook/slack` on FastAPI. Receives Slack Events API callbacks with verification.
- **BLT polling adapter** — Isolated background task. Polls BLT REST API every 60 seconds (`/api/issues/`, `/api/hunts/`). Uses `last_seen_id` cursor to fetch only new/updated records. Transforms into normalized Event schema.
- **Deduplication layer** — Applied after verification, before normalization. Uses idempotency key: `source + event_type + actor_id + timestamp`. Duplicate deliveries silently dropped.

### 2. Event Normalizer
- **GitHub Adapter** — Maps GitHub webhook `action` → internal event type (`issue_opened`, `pr_opened`, `pr_merged`, `review_requested`, `ci_run`). Extracts: `sender.id`, `sender.login`, `repository.full_name`.
- **Slack Adapter** — Resolves user identity via Slack Users API, extracts linked repo from message context, normalizes into Event schema.
- **BLT Adapter** — Extracts `user.id`, `user.username`, `hunt.repo` from polled records.
- **Unknown event fallback** — Routes unmapped event types to `Floor 1: Activity Monitor`.
- **Output** — Unified Pydantic `Event` model: `id (UUID)`, `source`, `event_type`, `actor_id`, `actor_name`, `repository`, `timestamp (UTC)`, `metadata (dict)`.

### 3. Identity Mapper
- **Exact match stage** — Lookup by platform-specific user ID + source. Confidence: 1.0.
- **Fuzzy username stage** — Levenshtein distance ≤ 2 on lowercase usernames against all known identities. Confidence: 0.75. Uses `rapidfuzz`.
- **Display name stage** — Jaccard/token-set similarity ≥ 0.6 on display names/aliases. Confidence: 0.60. Uses `rapidfuzz`.
- **Unlinked fallback** — Creates new identity record when no match found. Confidence: 0.0. Surfaces in UI with indicator.
- **Maintainer confirmation flow** — Sends `identity_flag` WebSocket message for fuzzy matches. Overlay UI for accept/reject.

### 4. State Layer (SQLite)
- **Four tables**: `events`, `contributors` (identities), `avatar_state`, `identity_mappings`.
- **Event persistence** — All normalized events stored with idempotency protection.
- **Avatar state** — `INSERT OR REPLACE INTO avatar_state (contributor_id, floor, room, last_event, updated_at)`. One row per contributor.
- **Gap tracking** — `last_seen_event_id` per repository for detecting missed GitHub events during downtime.
- **Migration scripts** — Included for schema provisioning.

### 5. Async Queue & State Reducer
- **In-process async queue** — Receives validated Event objects. Feeds both persistence and broadcast hub.
- **State reducer** — Applies incoming events to current room/avatar state. Updates room occupancy counts. Runs in-process (no external message broker).

### 6. WebSocket Broadcast Hub
- **Connection registry** — Tracks all active WebSocket client connections.
- **Snapshot endpoint** — On new client connect, sends full state: contributors array (id, display_name, floor, room, identity_linked, last_event, score) + room_occupancy map + generated_at timestamp.
- **Fan-out** — In-process async fan-out to all subscribed clients on each state change.
- **Message types**: `snapshot`, `avatar_move`, `identity_flag`, `leaderboard_update`.
- **Contract locked** — Message format frozen before Week 6 (no discovery phase for frontend).
- **Client resilience** — Auto-reconnect after 2s disconnect; stale indicators for out-of-order events; HTTP polling fallback when WebSocket unavailable.

### 7. Frontend Visualization Engine (Vanilla JS)
- **SVG/Canvas renderer** — Three-floor house layout with state-driven avatar positioning.
- **Room occupancy caps** — Visual cap at 12 avatars per room; `+N` counter beyond that.
- **Dirty region redraw** — Only changed rooms redrawn per update cycle, not full canvas.
- **Debouncing** — 5-second debounce window on avatar movement to prevent thrashing.
- **Leaderboard panel** — Live contributor scores, deltas, ranking.
- **Activity feed** — Chronological event display.
- **Maintainer visibility panel** — Ecosystem status indicators + room occupancy heatmap.

### 8. Analytics Overlay Components
- **Leaderboard projection** — Score accumulation from GitHub + BLT signals. Handles zero-point events and conflict resolution.
- **Mentor lifecycle projection** — assigned, handoff/pause, rematch states.
- **Metrics panel** — time-to-ecosystem-understanding, identity resolution ratio.

### 9. Deployment & Infrastructure
- **Docker Compose** — Three services: FastAPI backend, SQLite volume, static frontend (served alongside backend).
- **Optional Cloudflare Worker** — Frontend WebSocket hub for edge caching/geographic fan-out (deployment-layer addition, not an architectural change).

---

## Services

| Service | Technology | Role |
|---------|-----------|------|
| **FastAPI Backend** | Python (FastAPI) | Webhook receiver, event normalizer, identity mapper, state manager, WebSocket server, REST API for polling fallback, health endpoints |
| **SQLite** | SQLite (local file, Docker volume) | Persistent storage for events, contributor identities, avatar state, identity mappings |
| **Frontend** | Vanilla JS (SVG/Canvas) | Three-floor house renderer, WebSocket client, activity feed, leaderboard panel |
| **External: GitHub** | GitHub Webhooks + REST API | Source of issue/PR/CI/review events |
| **External: Slack** | Slack Events API + Users API | Source of coordination/message events |
| **External: BLT API** | BLT REST API (`/api/issues/`, `/api/hunts/`) | Source of bug bounty, hunt, and contributor activity data |

---

## Data Flows

### Flow 1: GitHub Push Webhook → UI Avatar Movement
```
GitHub webhook (push event)
  → POST /webhook/github
  → HMAC-SHA256 verification (reject 401 if invalid)
  → Idempotency check (drop duplicate if seen)
  → GitHub Adapter: normalize to Event model
  → Identity Mapper: resolve contributor (3-stage pipeline)
  → Async Queue: fan-out
     ├→ SQLite: persist event + update avatar_state
     └→ WebSocket Hub: broadcast avatar_move to all clients
        → Frontend Renderer: debounced SVG/Canvas update (only changed room redrawn)
```

### Flow 2: SLack Push Event → UI Update
```
Slack Events API callback
  → POST /webhook/slack
  → Slack verification
  → Slack Adapter: resolve user via Users API, extract repo context, normalize to Event
  → [Same pipeline as Flow 1 from Identity Mapper onward]
```

### Flow 3: BLT Poll → UI Update
```
BLT Polling Adapter (every 60s)
  → GET /api/issues/?since=<last_seen_id>
  → GET /api/hunts/?since=<last_seen_id>
  → BLT Adapter: transform records → Event model
  → [Same pipeline as Flow 1 from Identity Mapper onward]
  → On failure: log error, skip — does not affect GitHub/Slack pipeline
```

### Flow 4: New Client Connect → Full State
```
Client opens dashboard
  → WebSocket connect to FastAPI
  → Server sends { type: "snapshot", data: { contributors[], room_occupancy{}, generated_at } }
  → Frontend renders full house layout with all avatar positions
```

### Flow 5: WebSocket Disconnect → Recovery
```
Client WebSocket drops
  → Client waits 2s
  → Client reconnects
  → Server sends fresh snapshot (Flow 4)
  → UI restored
  → If WebSocket unavailable beyond threshold → client falls back to HTTP polling
```

### Flow 6: Identity Resolution Pipeline
```
Event arrives with actor fields
  → Stage 1: Exact match on (actor_id + source) in identity_mappings → 1.0 confidence
  → Stage 2 (if no match): Levenshtein ≤ 2 on username vs all known identities → 0.75 confidence
  → Stage 3 (if no match): Jaccard ≥ 0.6 on display name vs all known aliases → 0.60 confidence
  → Stage 4 (if no match): Create unlinked identity → 0.0 confidence, send identity_flag via WebSocket
```

### Flow 7: Gap Detection (Recovery)
```
Periodic check (every 90s)
  → Query last_seen_event_id per repository from SQLite
  → Poll GitHub /events API for events after that ID
  → Process any missed events through normal pipeline
```

---

## Event Flows

### Event Type → Room Mapping

| Event Type | Floor | Room |
|-----------|-------|------|
| `issue_opened` | 1 | Issue Triage Desk |
| `bug_bounty_submitted` | 1 | Bug Bounty Terminal |
| `ci_run` | 1 | CI/CD Server Room |
| *(deploy event)* | 1 | Deployment Control Center |
| *(unknown event)* | 1 | Activity Monitor |
| `pr_opened` | 2 | Pull Request Room |
| `review_requested` | 3 | Code Review Room |
| `pr_merged` | 3 | Mentor Office |
| `mentor_assigned` | 3 | Mentor Office |
| `mentor_handoff` | 3 | Strategy War Room |

### House Layout — Room Organization

**Floor 3: Leadership and Review**
Mentor Office · Code Review Room · Security Audit Room · Strategy War Room · Leaderboard Wall

**Floor 2: Development Workspace**
Pull Request Room · Contributor Workstations · Pair Programming Area · Debugging Room · Architecture Board

**Floor 1: Operations and Infrastructure**
Issue Triage Desk · Bug Bounty Terminal · CI/CD Server Room · Deployment Control Center · Activity Monitor

---

## Storage Requirements

### Database: SQLite (single file, Docker volume)

| Table | Purpose | Key Columns |
|-------|---------|------------|
| `events` | Normalized event log | id (UUID PK), source, event_type, actor_id, actor_name, repository, timestamp, metadata (JSON/text), idempotency_key (UNIQUE) |
| `contributors` | Unified contributor identities | id (PK), display_name, platform_ids (JSON: github_id, slack_id, blt_id), usernames (JSON array), aliases (JSON array), is_linked (bool) |
| `avatar_state` | Current position per contributor | contributor_id (PK, FK→contributors), floor, room, last_event, updated_at |
| `identity_mappings` | Platform-to-contributor mapping | platform, platform_user_id, contributor_id (FK→contributors), confidence, confirmed_by (nullable) |

### Additional persisted data
- `last_seen_event_id` per repository (stored in a metadata/config table or derived from events table)
- Dead letter queue (capped at 500 events, stored in events table with status flag or separate dead_letter table)

### Storage characteristics
- Scale: 50–200 active contributors, tens to low hundreds of events per day
- No external database server — SQLite is sufficient
- Docker volume for persistence across container restarts

---

## WebSocket Requirements

### Server (FastAPI)
- Single WebSocket endpoint accepting client connections
- Connection registry maintaining set of active WebSocket client references
- In-process async fan-out loop (not external pub/sub broker)
- Four message types pushed from server → client (no client → server messages defined beyond connect/disconnect)

### Message Contract (Locked Pre-Week 6)

**1. Snapshot** (sent on every new connection)
```json
{
  "type": "snapshot",
  "data": {
    "contributors": [
      {
        "id": "string",
        "display_name": "string",
        "floor": "int",
        "room": "string",
        "identity_linked": "bool",
        "last_event": "string",
        "score": "int"
      }
    ],
    "room_occupancy": {
      "room_name": "int"
    },
    "generated_at": "ISO8601"
  }
}
```

**2. Avatar Move** (live state change)
```json
{
  "type": "avatar_move",
  "contributor_id": "string",
  "floor": "int",
  "room": "string",
  "event_type": "string",
  "timestamp": "ISO8601"
}
```

**3. Identity Flag** (maintainer action required)
```json
{
  "type": "identity_flag",
  "suggested_link": {
    "source_a": { "platform": "string", "username": "string" },
    "source_b": { "platform": "string", "user_id": "string" },
    "confidence": "float"
  }
}
```

**4. Leaderboard Update**
```json
{
  "type": "leaderboard_update",
  "contributor_id": "string",
  "score": "int",
  "delta": "int",
  "last_event": "string"
}
```

### Scale Requirements
- 200 concurrent WebSocket clients sustained for 10 minutes (load test target)
- p99 broadcast latency < 200ms (from event processing to all clients receiving update)
- 50 events/min sustained ingest rate

### Client Resilience Behavior
- Disconnect → 2-second delay → reconnect → request fresh snapshot
- Out-of-order events flagged with stale indicators in activity panel
- WebSocket unavailable beyond threshold → fallback to periodic HTTP polling
