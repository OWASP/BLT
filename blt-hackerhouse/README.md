# BLT-Hackerhouse

**Live Site:** [https://hackerhouse.owaspblt.org/](https://hackerhouse.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-HackerHouse](https://git.owaspblt.org/BLT/BLT-HackerHouse)

Real-time contributor visualization platform for OWASP BLT — now running on **Cloudflare Workers**.

HackerHouse is a realtime operational dashboard that ingests the BLT monorepo's activity from **git.owaspblt.org** (the forge), plus optional **BLT** and **GitLab webhook** events, normalizes them into a unified internal model, resolves contributor identity across platforms, and broadcasts live contributor movement to connected clients via WebSocket.

## Sources

| Source | `source` | How | Events |
|--------|----------|-----|--------|
| Forge: git.owaspblt.org, `owasp-blt/BLT` | `forge` | Polled every 5 minutes (blt-cron calls `POST /__scheduled`; `scheduled()` runs the same poll) | `commit_pushed` (new commits on `main`), `issue_opened`, `issue_closed`, `note_added` (issue and pull comments, reviews), `mr_opened`, `mr_merged` |
| GitLab webhook (optional, external) | `gitlab` | `POST /webhook/gitlab` with `X-Gitlab-Token` = `GITLAB_WEBHOOK_SECRET` | `issue_opened`, `mr_opened`, `mr_merged`, `review_requested`, `pipeline_run`, `note_added` |
| BLT API | `blt` | Normalizers only; the poller is not built (Phase 2) | `bug_bounty_submitted`, `bug_status_change`, `hunt_activity` |

The forge poller (`backend/src/ingestion/forge_poller.py`) reads the public, anonymous API:
`history?ref=main` (60 commits a page, paged by parent), the issue ledger
`.forkmesh/issues/{open,closed}/<n>/issue-<n>.json` on `main` (`tree` + `blobs`, 50 files a request)
and the pull ledger `.forkmesh/pulls/<n>/` on the `forkmesh/pulls` branch (a 404 means no pulls yet).
A commit is attributed to a project folder by its `<folder>:` subject prefix (checked against the
repository's top-level folders), otherwise to `BLT`. Bot authors (`FORGE_BOT_AUTHORS`, and names
ending in `[bot]`) and merge commits are skipped.

Its cursor is one `poll_cursors` row (`source = 'forge'`): the last commit sha and time, the git
oids of the issue and pull folders, and the folder list. A run reads only what changed and writes
the cursor only when it changed, so an idle run is 2 forge requests, 1 D1 read and no D1 writes.
The first run imports the last `FORGE_BACKFILL_DAYS` (7) days, at most `FORGE_MAX_EVENTS` (300)
events. A run stops at 40 forge requests (the free plan allows 50 subrequests) and continues on the
next run. Each event carries a stable `dedup_key` (commit sha, issue event id, pull file), so the
queue consumer's `INSERT OR IGNORE` on the idempotency key makes a repeated delivery a no-op.

To see what a first run would import, without writing anywhere:

```bash
python backend/scripts/forge_dry_run.py
```

---

## Architecture Summary

```
Browser (static UI)  ←──  Cloudflare Workers Assets
        │
        ├─ REST ────────►  FastAPI (ASGI) → D1 Database
        ├─ WebSocket ───►  Durable Object Broadcast Hub
        └─ HTTP fallback → /state endpoint

Forge poller (blt-cron → POST /__scheduled, every 5 min)
GitLab webhook (optional)
        │
        └──► Cloudflare Queue → Pipeline Consumer → D1 + Broadcast
```

**Runtime**: Cloudflare Workers (Python + Pyodide)<br>
**API**: FastAPI via `asgi.fetch()` adapter  
**Database**: Cloudflare D1 (SQLite-compatible)<br>
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
npx wrangler secret put CRON_SECRET            # the same value blt-cron has
npx wrangler secret put GITLAB_WEBHOOK_SECRET  # optional: only for a GitLab webhook
npx wrangler secret put BLT_API_KEY            # optional
npx wrangler secret put WEBSOCKET_AUTH_TOKEN
```

### Deploy

```bash
# 1. Apply remote D1 migrations first (first deploy, and before any deploy that adds a migration).
#    003_forge_source.sql rebuilds events and identity_mappings to allow source 'forge'.
npx wrangler d1 migrations apply hackerhouse --remote

# 2. Deploy the Worker
uv run pywrangler deploy

# 3. Deploy blt-cron (from the repository root), which calls POST /__scheduled every 5 minutes
scripts/deploy.sh blt-cron
```

Code that writes `source = 'forge'` must not run before migration 003: the consumer's inserts
would fail the CHECK constraint and the backfill would end in the queue's retries. A push to
`main` deploys the Worker through the repository's Deploy workflow, which does not apply
migrations, so apply them before merging. For staging, add `--env staging` to the commands.

There is no `triggers` block in `wrangler.jsonc`: the account's only cron trigger is blt-cron's
(see `blt-cron/README.md`). `CRON_SECRET` must be set on both Workers with the same value; without
it `/__scheduled` answers 403.

---

## Environment Variables

Secrets (set via `wrangler secret put`):

| Secret | Purpose |
|--------|---------|
| `CRON_SECRET` | Authenticates blt-cron's `POST /__scheduled` (`X-BLT-Cron-Secret`); same value as on blt-cron |
| `GITLAB_WEBHOOK_SECRET` | Optional: verifies incoming GitLab webhooks |
| `BLT_API_KEY` | Optional: BLT-API authentication (the BLT poller is Phase 2) |
| `WEBSOCKET_AUTH_TOKEN` | Authenticates WebSocket connections |

Vars (set in `wrangler.jsonc` → `vars`):

| Variable | Default | Description |
|----------|---------|-------------|
| `FORGE_URL` | `https://git.owaspblt.org` | Forge instance |
| `FORGE_REPO` | `owasp-blt/BLT` | Repository (`owner/name`) polled |
| `FORGE_REF` | `main` | Branch whose commits become events |
| `FORGE_BOT_AUTHORS` | `owasp-blt-actions,forkmesh` | Authors skipped (comma-separated; `*[bot]` is always skipped) |
| `FORGE_BACKFILL_DAYS` | `7` | Window the first run (no cursor) imports |
| `FORGE_MAX_EVENTS` | `300` | Most events one run enqueues (the newest are kept) |
| `BLT_API_BASE_URL` | `https://api.owaspblt.org/v2` | BLT-API base URL |
| `LOG_LEVEL` | `INFO` | Python logging level |

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
│   │   ├── ingestion/         # Forge poller, GitLab webhook verification
│   │   ├── normalization/     # Forge, GitLab and BLT event normalizers
│   │   ├── identity/          # 4-stage resolution pipeline
│   │   ├── state/             # Room routing map
│   │   ├── broadcast/         # Message builders + leaderboard scoring
│   │   └── api/               # FastAPI REST routes
│   ├── migrations/            # D1 SQL migrations
│   ├── tests/
│   │   └── unit/              # Unit tests (the in-memory D1 applies backend/migrations/)
│   └── scripts/               # Dev tooling (forge_dry_run.py: print what the poller would import)
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
| `poll_cursors` | Polling cursor state (`forge`: JSON cursor in `metadata`) |
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
| `POST` | `/webhook/gitlab` | Optional GitLab webhook receiver (token-verified) |
| `POST` | `/__scheduled` | Runs the forge poll; blt-cron only (`X-BLT-Cron-Secret`) |
| `WS` | `/ws` | WebSocket endpoint (snapshot + live updates) |

WebSocket message types: `snapshot`, `avatar_move`, `identity_flag`, `leaderboard_update`.

---

## MVP Feature Status

| Feature | Status |
|---------|--------|
| Forge (git.owaspblt.org) poller | ✅ |
| GitLab webhook ingestion (optional) | ✅ |
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
| Structured JSON logging | ✅ |
| Queue consumer pipeline | ✅ |
| BLT poller | Phase 2 |

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

Built for OWASP BLT 
