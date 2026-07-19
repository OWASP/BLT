# BLT-Hackerhouse

Real-time contributor visualization platform for OWASP BLT.

HackerHouse is a realtime operational dashboard that ingests events from **GitLab** and **BLT**, normalizes them into a unified internal model, resolves contributor identity across platforms, and broadcasts live contributor movement to connected clients. A maintainer can understand the current ecosystem state within seconds of opening the dashboard.

---

## Architecture Summary

```
GitLab Webhooks (push) ──┐
                          ├──► Ingestion ──► Normalization ──► Identity Resolution
BLT API (poll) ──────────┘                                         │
                                                                   ▼
Frontend ◄── WebSocket Broadcast ◄── State Reducer ◄──────────────┘
   ▲              ▲
   │              │
   └── REST API ──┘  (activity feed, leaderboard, status, health)
```

**Platforms**: GitLab (primary SCM), BLT API (bug bounty + hunts)  
**Database**: SQLite (single file, zero-config)  
**Real-time**: WebSocket push + HTTP polling fallback  
**Identity**: 4-stage resolution pipeline (exact → Levenshtein → Jaccard → unlinked)

---

## Current MVP Scope

| Included | Excluded |
|----------|----------|
| GitLab webhook ingestion (`X-Gitlab-Token` verification) | GitHub (platform migrated) |
| BLT REST polling adapter (60s interval, `/bugs` + `/hunts`) | Slack (deferred — unvalidated) |
| Event deduplication (idempotency keys) | Mentorship tracking (out of scope) |
| Unified Event schema (Pydantic) | Frontend rendering (provided separately) |
| GitLab + BLT event normalizers | Authentication / access control |
| 4-stage identity resolution (GitLab ↔ BLT) | Historical replay |
| Room routing (3 floors, 15 rooms, no mentorship rooms) | Discord, Jira, other integrations |
| Avatar state persistence + WebSocket broadcast | Contributor badges / gamification |
| Snapshot on connect + reconnect recovery | Docker Compose (post-MVP) |
| Activity feed API (paginated) | CI/CD (post-MVP) |
| Leaderboard computation + API | Unit/integration/load tests (post-MVP) |
| Maintainer visibility API (status + health) | |
| Exponential backoff retry + dead letter handling | |
| Gap detection via GitLab Events API | |
| Health endpoints + structured logging | |

**20 backend features**. Full specification: [`docs/MVP_V1_SPEC.md`](docs/MVP_V1_SPEC.md)  
**Deferred items**: [`docs/POST_MVP_BACKLOG.md`](docs/POST_MVP_BACKLOG.md)

---

## Repository Structure

```
blt-hackerhouse/
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── migrations/           # Sequential SQLite DDL
│   ├── scripts/              # Dev tooling (migrate, seed, run_dev)
│   ├── src/
│   │   ├── main.py           # FastAPI app factory + lifespan
│   │   ├── config.py         # pydantic-settings env loader
│   │   ├── models/           # Pure Pydantic schemas
│   │   ├── core/             # Shared utilities (retry, logging, dedup, security)
│   │   ├── storage/          # aiosqlite queries + migration runner
│   │   ├── ingestion/        # GitLab webhook, BLT poller, gap detector, queue
│   │   ├── normalization/    # GitLab + BLT event adapters
│   │   ├── identity/         # 4-stage resolution pipeline (rapidfuzz)
│   │   ├── state/            # Room map, reducer, pipeline runner
│   │   ├── broadcast/        # WebSocket hub, message builders, leaderboard
│   │   └── api/              # FastAPI routes + WebSocket endpoint
│   └── tests/
│       ├── fixtures/         # Real GitLab + BLT payloads
│       ├── unit/             # Mirrors src/ tree
│       └── integration/      # Cross-package flows
├── frontend/                 # (TBD — provided separately)
├── docs/                     # Specifications + planning artifacts
└── README.md
```

**Package dependency direction**: `api → state → {broadcast, identity, normalization, ingestion} → storage → core → models → config`  
Full design: [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md)

---

## Database

SQLite with 6 tables:

| Table | Purpose | Rows (expected) |
|-------|---------|----------------|
| `contributors` | Unified identities | 50–200 |
| `identity_mappings` | Platform → contributor links | 100–400 |
| `events` | Normalized event log | 500–3,000 |
| `avatar_state` | Current room position | 50–200 |
| `poll_cursors` | Polling cursor state | 2–10 |
| `dead_letter_queue` | Failed events (capped 500) | 0–500 |

Full schema: [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)

---

## Development Setup

### Prerequisites

- Python 3.12+
- Git

### Quick Start

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your GitLab webhook secret, BLT API key, etc.

# Initialize database
python scripts/migrate.py

# Run development server
python scripts/run_dev.sh
# or: uvicorn src.main:app --reload --port 8000
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITLAB_WEBHOOK_SECRET` | Yes | Secret token for GitLab webhook verification |
| `GITLAB_API_TOKEN` | For gap detection | GitLab personal access token with `read_api` scope |
| `BLT_API_BASE_URL` | Yes | BLT-API base URL (e.g. `https://api.owaspblt.org`) |
| `BLT_API_KEY` | Yes | API key for `X-BLT-API-Key` header |
| `DATABASE_PATH` | No (default: `./blt_hackerhouse.db`) | SQLite database file path |
| `POLL_INTERVAL_SECONDS` | No (default: `60`) | BLT polling interval |
| `LOG_LEVEL` | No (default: `INFO`) | Python logging level |

### Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest --cov=src --cov-report=term-missing
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhook/gitlab` | GitLab webhook receiver (token-verified) |
| `GET` | `/activity` | Paginated event feed (`?page=1&per_page=50`) |
| `GET` | `/leaderboard` | Paginated contributor scores (`?page=1&per_page=20`) |
| `GET` | `/status` | Room occupancy + identity stats + pipeline health |
| `GET` | `/health` | Per-component health check |
| `GET` | `/state` | HTTP polling fallback snapshot |
| `WS` | `/ws` | WebSocket endpoint (snapshot + live updates) |

WebSocket message types: `snapshot`, `avatar_move`, `identity_flag`, `leaderboard_update`.

---

## Roadmap

### MVP (Current)
- [x] Architecture design + data model
- [ ] Models + config layer
- [ ] Core utilities (logging, dedup, retry, security)
- [ ] Storage layer (SQLite schema + query functions)
- [ ] GitLab webhook ingestion
- [ ] BLT polling adapter
- [ ] Event normalizers (GitLab + BLT)
- [ ] Identity resolution pipeline
- [ ] Room routing + state reducer
- [ ] WebSocket broadcast hub
- [ ] REST API endpoints
- [ ] Health + logging + dead letter handling
- [ ] Gap detection + retry

### Post-MVP
- [ ] Unit + integration + load tests
- [ ] Docker Compose deployment
- [ ] Contributor documentation
- [ ] Frontend integration (when provided)
- [ ] Slack integration (if requirements validated)

Full backlog: [`docs/POST_MVP_BACKLOG.md`](docs/POST_MVP_BACKLOG.md)

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| [`MVP_V1_SPEC.md`](docs/MVP_V1_SPEC.md) | Implementation specification — all 20 features with contracts |
| [`REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) | Package design, module responsibilities, dependency rules |
| [`DATA_MODEL.md`](docs/DATA_MODEL.md) | Complete database schema with column-level design |
| [`POST_MVP_BACKLOG.md`](docs/POST_MVP_BACKLOG.md) | All deferred/removed items |
| [`ARCHITECTURE_REVIEW.md`](docs/ARCHITECTURE_REVIEW.md) | Pre-implementation review findings |
| [`docs/archive/`](docs/archive/) | Historical planning artifacts (original proposal extractions) |

---

## License

To be determined.

---

## Acknowledgments

Built as part of Google Summer of Code 2026 for OWASP BLT.  
Lead Mentor: Donnie Brown.  
Applicant: Rudra Pratap Singh.
