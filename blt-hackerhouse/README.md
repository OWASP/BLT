# BLT-Hackerhouse

Real-time contributor visualization platform for OWASP BLT — now running on **Cloudflare Workers**.

HackerHouse is a realtime operational dashboard that ingests events from **GitLab** and **BLT**, normalizes them into a unified internal model, resolves contributor identity across platforms, and broadcasts live contributor movement to connected clients via WebSocket.

---

## Architecture Summary

```
Browser (static UI)  ←──  Cloudflare Workers Assets
        │
        ├─ REST ────────►  FastAPI (ASGI) → D1 Database
        ├─ WebSocket ───►  Durable Object Broadcast Hub
        └─ HTTP fallback → /state endpoint

GitLab Webhooks / Cron Pollers
        │
        └──► Cloudflare Queue → Pipeline Consumer → D1 + Broadcast
```

**Runtime**: Cloudflare Workers (Python + Pyodide)  
**API**: FastAPI via `asgi.fetch()` adapter  
**Database**: Cloudflare D1 (SQLite-compatible)  
**Real-time**: WebSocket via Durable Objects  
**Identity**: 4-stage resolution pipeline (exact → Levenshtein → Jaccard → unlinked), pure Python fuzzy matching

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ (for Wrangler CLI)
- Cloudflare account (for deployment)

### Local Development

```bash
# Install Python dev dependencies
uv sync --group dev

# Install Wrangler CLI
npm install

# Apply local D1 migrations
npx wrangler d1 migrations apply hackerhouse --local

# Start dev server
uv run pywrangler dev
```

The dev server starts at `http://127.0.0.1:8788`. All bindings (D1, Queue, Durable Objects) work locally without Cloudflare account credentials.

### Running Tests

```bash
uv run pytest backend/tests/unit -v
```

---

## Deployment

### One-time Infrastructure Setup

These steps require the maintainer's Cloudflare account and are run **once**:

```bash
# Create D1 database
npx wrangler d1 create hackerhouse
# → Copy the returned database_id into wrangler.jsonc replacing "PLACEHOLDER"

# Create pipeline queue
npx wrangler queues create pipeline-events

# Set secrets
npx wrangler secret put GITLAB_WEBHOOK_SECRET
npx wrangler secret put GITLAB_API_TOKEN
npx wrangler secret put BLT_API_KEY
npx wrangler secret put WEBSOCKET_AUTH_TOKEN
```

### Deploy

```bash
# Apply remote D1 migrations (first deploy only)
npx wrangler d1 migrations apply hackerhouse --remote

# Deploy Worker
uv run pywrangler deploy
```

---

## Environment Variables

Secrets (set via `wrangler secret put`):

| Secret | Purpose |
|--------|---------|
| `GITLAB_WEBHOOK_SECRET` | Verifies incoming GitLab webhooks |
| `GITLAB_API_TOKEN` | GitLab API access for gap detection (Phase 2) |
| `BLT_API_KEY` | BLT-API authentication |
| `WEBSOCKET_AUTH_TOKEN` | Authenticates WebSocket connections |

Vars (set in `wrangler.jsonc` → `vars`):

| Variable | Default | Description |
|----------|---------|-------------|
| `BLT_API_BASE_URL` | `https://api.owaspblt.org/v2` | BLT-API base URL |
| `GITLAB_TRACKED_PROJECT_IDS` | `""` | Comma-separated project IDs for gap detection |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `BLT_POLL_INTERVAL_SECONDS` | `60` | BLT polling interval |
| `GITLAB_POLL_INTERVAL_SECONDS` | `90` | GitLab gap detection interval |
| `GITLAB_LOOKBACK_MINUTES` | `30` | Gap detection lookback window |

---

## Repository Structure

```
blt-hackerhouse/
├── wrangler.jsonc             # Cloudflare Workers configuration
├── pyproject.toml             # Python project metadata + dependencies
├── package.json               # Node dependencies (Wrangler CLI)
├── UI/                        # Static frontend (served via Cloudflare Assets)
│   ├── avatars/               # 10 contributor avatar PNGs
│   └── html/                  # 5 page templates + CSS/JS assets
├── backend/
│   ├── src/
│   │   ├── app.py             # FastAPI application factory (no Worker imports)
│   │   ├── worker.py          # Worker entrypoint: fetch, queue, scheduled
│   │   ├── config.py          # pydantic-settings env loader
│   │   ├── models/            # Pure Pydantic schemas (23 models)
│   │   ├── core/              # Shared utilities
│   │   │   ├── fuzzy.py       # Pure Python Levenshtein + Jaccard
│   │   │   ├── logging.py     # Structured JSON logging
│   │   │   ├── retry.py       # Exponential backoff + jitter
│   │   │   ├── security.py    # Constant-time token comparison
│   │   │   └── dedup.py       # Idempotency-key deduplication
│   │   ├── storage/
│   │   │   ├── queries.py     # D1 native prepared statements (6 query classes)
│   │   │   └── d1_utils.py    # D1 result conversion helpers
│   │   ├── ingestion/         # GitLab webhook verification
│   │   ├── normalization/     # GitLab + BLT event normalizers
│   │   ├── identity/          # 4-stage resolution pipeline
│   │   ├── state/             # Room routing map
│   │   ├── broadcast/         # Message builders + leaderboard scoring
│   │   └── api/               # FastAPI REST routes
│   ├── migrations/            # D1 SQL migrations
│   ├── tests/
│   │   └── unit/              # Unit tests (117 passing)
│   └── scripts/               # Dev tooling
├── docs/                      # Specifications + planning artifacts
└── spike-1-fastapi/           # Preflight spike results
```

---

## Database

D1 (SQLite-compatible) with 7 tables:

| Table | Purpose |
|-------|---------|
| `contributors` | Unified contributor identities |
| `identity_mappings` | Platform → contributor links |
| `events` | Normalized event log |
| `avatar_state` | Current room position per contributor |
| `poll_cursors` | Polling cursor state |
| `dead_letter_queue` | Failed events (capped at 500) |
| `health_state` | Durable health tracking (Phase 2) |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Per-component health check |
| `GET` | `/activity` | Paginated event feed (`?page=1&per_page=50`) |
| `GET` | `/leaderboard` | Paginated contributor scores (`?page=1&per_page=20`) |
| `GET` | `/status` | Room occupancy + identity stats + pipeline health |
| `GET` | `/state` | HTTP polling fallback snapshot |
| `POST` | `/webhook/gitlab` | GitLab webhook receiver (token-verified) |
| `WS` | `/ws` | WebSocket endpoint (snapshot + live updates) |

WebSocket message types: `snapshot`, `avatar_move`, `identity_flag`, `leaderboard_update`.

---

## MVP Feature Status

| Feature | Status |
|---------|--------|
| GitLab webhook ingestion | ✅ |
| BLT REST polling adapter | Phase 2 |
| Event deduplication | ✅ |
| Unified Event schema | ✅ |
| GitLab + BLT event normalizers | ✅ |
| 4-stage identity resolution | ✅ |
| Room routing (3 floors, 10 rooms) | ✅ |
| Avatar state persistence | ✅ |
| WebSocket broadcast (Durable Objects) | ✅ |
| Snapshot on connect | ✅ |
| Activity feed API | ✅ |
| Leaderboard API | ✅ |
| Status + health API | ✅ |
| Exponential backoff retry | ✅ |
| Dead letter handling | ✅ |
| Gap detection (GitLab Events API) | Phase 2 |
| Structured JSON logging | ✅ |
| Queue consumer pipeline | Phase 2 |
| Cron pollers (BLT + GitLab) | Phase 2 |

---

## Design Decisions

See [`docs/design_decision.md`](docs/design_decision.md) for the full trade-off analysis. Key decisions:

- **FastAPI + ASGI adapter** instead of rewriting routes as Worker handlers
- **D1 native prepared statements** instead of an aiosqlite-compatible adapter (fragile around transactions/row metadata)
- **Pure Python fuzzy matching** instead of rapidfuzz (no Pyodide-compatible wheel)
- **Durable Objects** for WebSocket state (survives worker restarts)
- **Cloudflare Queues** for event pipeline (replaces in-memory `asyncio.Queue`)

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| [`MVP_V1_SPEC.md`](docs/MVP_V1_SPEC.md) | Implementation specification |
| [`design_decision.md`](docs/design_decision.md) | Architecture decisions + trade-offs |
| [`implementation_plan.md`](docs/implementation_plan.md) | Phase-by-phase migration plan |
| [`REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) | Package design + dependency rules |
| [`DATA_MODEL.md`](docs/DATA_MODEL.md) | Database schema |
| [`spike-1-fastapi/SPIKE_*.md`](spike-1-fastapi/) | Preflight spike results (6 spikes) |

---

## License

MIT.

---

Built for OWASP BLT — Google Summer of Code 2026.
