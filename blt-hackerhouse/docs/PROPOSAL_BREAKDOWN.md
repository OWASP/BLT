# Proposal Breakdown — BLT-Hackerhouse

*Extracted from: Rudra Pratap Singh — BLT-Hackerhouse GSoC Proposal (Large Project, OWASP)*

---

## Project Goals

1. **Single live dashboard** — Provide a realtime operational view of contributor workflow state across all stages (GitHub, Slack, BLT). A maintainer should understand the current ecosystem state within 5 seconds of opening the dashboard.
2. **Bottleneck visibility** — Detect congestion and stuck contributions by unifying fragmented signals across platforms into one spatial interface.
3. **Onboarding acceleration** — Give new contributors an at-a-glance view of where help is needed and where contributions are stuck.
4. **Cross-platform identity unification** — Resolve contributor identity across GitHub, Slack, and BLT so the same person appears as one avatar rather than three.

---

## Functional Requirements

### Event Ingestion
- **FR1** — Receive GitHub webhook events with HMAC-SHA256 signature verification. Invalid signatures rejected with 401.
- **FR2** — Receive Slack event callbacks with verification via Slack Events API.
- **FR3** — Poll BLT REST endpoints (`/api/issues/`, `/api/hunts/`) on a 60-second interval with a `last_seen_id` cursor to avoid duplication.
- **FR4** — Deduplicate events across all sources using idempotency keys (`source + event_type + actor_id + timestamp`).
- **FR5** — Track `last_seen_event_id` per repository in SQLite to detect gaps during downtime. Periodic 90-second polling of `/events` API.

### Event Normalization
- **FR6** — Convert each source-specific payload into a unified internal `Event` model (source, event_type, actor_id, actor_name, repository, timestamp, metadata).
- **FR7** — Isolate platform-specific adapter logic so the core pipeline never inspects raw payloads.
- **FR8** — Map GitHub actions (opened, closed, merged) to internal event types: `issue_opened`, `pr_opened`, `pr_merged`, `review_requested`, `ci_run`.
- **FR9** — Map Slack and BLT events into equivalent workflow signals.
- **FR10** — Route unknown event types to a fallback room (`Floor 1: Activity Monitor`).

### Identity Resolution
- **FR11** — Resolve contributor identity across GitHub, Slack, and BLT using a three-stage pipeline:
  1. Exact match on platform-specific user ID (confidence 1.0).
  2. Levenshtein distance ≤ 2 on username/lowercase handles (confidence 0.75).
  3. Jaccard/token-set similarity ≥ 0.6 on display names (confidence 0.60).
- **FR12** — Create unlinked identities for contributors not matching any existing profile (confidence 0.0).
- **FR13** — Surface unresolved identities in the UI with a visible indicator. Maintainer can confirm or reject suggested links via overlay.
- **FR14** — Send `identity_flag` WebSocket messages to prompt maintainer confirmation when a fuzzy match is found.

### Room Routing & Avatar State
- **FR15** — Route each event type to a predefined room on one of three floors based on the `ROOM_MAP`.
- **FR16** — Maintain persistent avatar state per contributor (`avatar_state` table: contributor_id, floor, room, last_event, updated_at).
- **FR17** — Cap room occupancy visually at 12 avatars; display a `+N` counter beyond that.
- **FR18** — Only redraw changed rooms on each update cycle, not the full canvas (dirty region redraw).
- **FR19** — Apply a 5-second debounce window on avatar movement commits to prevent UI thrashing under burst activity.

### WebSocket Broadcast
- **FR20** — Broadcast live event updates to all subscribed clients via WebSocket.
- **FR21** — Send a snapshot of full state (contributors, room_occupancy, generated_at) to every newly connected client.
- **FR22** — Send `avatar_move` messages with contributor_id, floor, room, event_type, timestamp on each state change.
- **FR23** — Send `leaderboard_update` messages with contributor score, delta, and last_event.
- **FR24** — Lock the WebSocket message contract before Week 6 (no discovery phase for frontend integration).
- **FR25** — Support up to 200 concurrent WebSocket clients with p99 broadcast latency < 200ms.
- **FR26** — Client reconnects after 2s on disconnect; fresh snapshot sent automatically.
- **FR27** — Fall back to periodic HTTP polling when WebSocket is unavailable beyond a threshold.
- **FR28** — Flag out-of-order events with stale indicators in the activity panel.

### Frontend Visualization
- **FR29** — Render a three-floor house layout using SVG/Canvas with state-driven avatar positioning.
- **FR30** — Display five rooms per floor:
  - Floor 1: Issue Triage Desk, Bug Bounty Terminal, CI/CD Server Room, Deployment Control Center, Activity Monitor
  - Floor 2: Pull Request Room, Contributor Workstations, Pair Programming Area, Debugging Room, Architecture Board
  - Floor 3: Mentor Office, Code Review Room, Security Audit Room, Strategy War Room, Leaderboard Wall
- **FR31** — Render room occupancy counts per room.
- **FR32** — Display a leaderboard panel with live contributor scores and deltas.
- **FR33** — Show activity feed payloads.
- **FR34** — Render a maintainer visibility panel with ecosystem status indicators and room occupancy heatmap.

### Leaderboard & Metrics
- **FR35** — Compute leaderboard projection from GitHub + BLT signals (correct accumulation, zero-point events, conflict resolution).
- **FR36** — Display mentor lifecycle projection: assigned, handoff/pause, rematch.
- **FR37** — Measure and display ecosystem status indicators.

### Deployment
- **FR38** — Single-command launch via Docker Compose: FastAPI backend, SQLite volume, vanilla JS frontend.
- **FR39** — Include contributor documentation for adding new event adapters.

---

## Non-Functional Requirements

| Category | Requirement |
|----------|------------|
| **Latency** | WebSocket update within 200ms of event processing (p99) |
| **Latency** | Webhook events received, verified, normalized, and persisted within 500ms |
| **Throughput** | 200 concurrent WebSocket clients sustained for 10 minutes |
| **Throughput** | 50 events/min sustained ingest rate |
| **Reliability** | 99%+ of webhook events ingested and persisted without loss |
| **Identity Accuracy** | 80%+ of contributors correctly linked across platforms |
| **Test Coverage** | 80% coverage on ingestion and normalization modules |
| **Deployment** | Zero-configuration local setup — single Docker Compose command |
| **Resilience** | Slack: exponential backoff 1s→2s→4s→8s→max 32s with 500ms jitter; dead letter queue capped at 500 events |
| **Resilience** | BLT polling adapter isolated — failures do not break GitHub/Slack pipeline |
| **Resilience** | Client WebSocket disconnect → auto-reconnect within 2s with fresh snapshot |
| **Observability** | Health endpoints and structured logging for all ingestion paths |
| **Scale** | Targets 50–200 active contributors (SQLite is appropriate for this scale) |

---

## Data Sources

| Source | Integration Method | Data Provided |
|--------|-------------------|---------------|
| **GitHub** | Webhook (push) — HMAC-SHA256 verified | Issues opened, PRs opened/merged, review requests, CI runs |
| **Slack** | Events API (push) — verified callbacks | Mentions tied to issues/PRs, message context, linked repository |
| **BLT API** | REST polling (60-second interval) via `/api/issues/` and `/api/hunts/` | Bug reports, contributor activity, ongoing hunts, `user.id`, `user.username`, `hunt.repo` |

---

## Assumptions

1. **BLT scale** — 50–200 active contributors. SQLite and a single FastAPI process are sufficient for this volume.
2. **Email match availability** — Approximately 40% of contributor pairs have exact email matches across platforms.
3. **Username similarity coverage** — Levenshtein distance ≤ 2 covers ~55% of remaining unmatched pairs.
4. **Display name similarity coverage** — Token overlap ≥ 0.6 covers a further ~20%.
5. **Unresolved remainder** — ~25% of pairs will require maintainer confirmation; this is expected and handled by the unlinked avatar indicator.
6. **BLT webhook absence** — BLT does not currently support webhook push; polling is the integration method. This is additive and does not break the GitHub/Slack pipeline.
7. **Docker Compose** — Sufficient as the sole deployment mechanism for MVP.
8. **No authentication required** — The dashboard operates without access control (listed under Non-Goals).
9. **Three-platform scope** — GitHub, Slack, and BLT only. No Discord, Jira, or other integrations.
10. **Exams buffer** — End-semester exams late May to mid-June; Weeks 1–3 are lighter (~15 hrs/wk), full pace from Week 4 (~40 hrs/wk).

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Slack API rate limits** | Medium | Exponential backoff (1s→2s→4s→8s→max 32s) with 500ms jitter. Dead letter queue capped at 500 events before drop with structured log entry. |
| **Missed GitHub events during downtime** | Medium | Track `last_seen_event_id` per repository in SQLite. Periodic 90-second polling of `/events` API to detect gaps. |
| **Contributor identity fragmentation** | High | Three-stage resolution pipeline (email → Levenshtein → Jaccard) with `rapidfuzz`. Unresolved contributors visible with explicit indicator. Maintainer confirmation flow surfaced in overlay. |
| **BLT API instability** | Low | Polling adapter is isolated. BLT signals are additive — their absence does not break GitHub/Slack pipeline. Polling errors are logged and skipped, not fatal. |
| **Canvas performance under high occupancy** | Low | Per-room avatar cap of 12 with `+N` counter. Dirty region redraw — only changed rooms updated, not full canvas. |
| **COSMIC components with breaking alpha changes** | Low | All COSMIC integrations (if added post-GSoC) isolated in adapters. Core pipeline is not COSMIC-dependent. |
