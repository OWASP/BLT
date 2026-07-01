# Feature Inventory — BLT-Hackerhouse

*Extracted from: Rudra Pratap Singh — BLT-Hackerhouse GSoC Proposal*

---

| # | Feature Name | Description | Dependencies | Complexity | MVP or Future |
|---|-------------|-------------|--------------|------------|---------------|
| F01 | **GitHub Webhook Ingestion** | Receive GitHub webhooks, verify HMAC-SHA256 signature, reject invalid with 401, enqueue valid payloads | FastAPI, GitHub secret | Medium | MVP |
| F02 | **Slack Events Ingestion** | Receive Slack event callbacks with verification, ingest mentions tied to issues/PRs | FastAPI, Slack Events API, Slack signing secret | Medium | MVP |
| F03 | **BLT Polling Adapter** | Poll BLT REST API every 60s (`/api/issues/`, `/api/hunts/`) with `last_seen_id` cursor; transform into normalized events | BLT API availability, HTTP client | Medium | MVP |
| F04 | **Event Deduplication** | Drop duplicate webhook deliveries using idempotency key (`source + event_type + actor_id + timestamp`) | F01, F02, F03 | Low | MVP |
| F05 | **Unified Event Schema** | Convert all source-specific payloads into a single Pydantic `Event` model (id, source, event_type, actor_id, actor_name, repository, timestamp, metadata) | F01, F02, F03 | Medium | MVP |
| F06 | **GitHub Event Normalizer** | Map GitHub webhook actions to internal event types: `issue_opened`, `pr_opened`, `pr_merged`, `review_requested`, `ci_run` | F01, F05 | Low | MVP |
| F07 | **Slack Event Normalizer** | Map Slack event payloads to normalized Event schema with resolved repo context | F02, F05 | Medium | MVP |
| F08 | **BLT Event Normalizer** | Map BLT polled records to normalized Event schema | F03, F05 | Medium | MVP |
| F09 | **Identity Resolution — Exact Match** | Match contributor via platform-specific user ID (confidence 1.0) | SQLite identity table, contributor data | Low | MVP |
| F10 | **Identity Resolution — Levenshtein** | Match contributor via username similarity (Levenshtein distance ≤ 2, confidence 0.75) | `rapidfuzz`, SQLite identity table | Medium | MVP |
| F11 | **Identity Resolution — Jaccard** | Match contributor via display name token-overlap (Jaccard ≥ 0.6, confidence 0.60) | `rapidfuzz`, SQLite identity table | Medium | MVP |
| F12 | **Unlinked Identity Handling** | Create unlinked identities for unresolved contributors; surface in UI with indicator | F09, F10, F11 | Low | MVP |
| F13 | **Identity Flag WebSocket Message** | Send `identity_flag` messages to prompt maintainer confirmation of fuzzy matches | F10, F11, WebSocket broadcast | Medium | MVP |
| F14 | **Room Routing Map** | Route each event_type to a predefined room on one of three floors via `ROOM_MAP` | F05 | Low | MVP |
| F15 | **Avatar State Persistence** | Store and update contributor position (contributor_id, floor, room, last_event, updated_at) in SQLite `avatar_state` table | SQLite, F14 | Low | MVP |
| F16 | **SQLite Schema** | Four tables: `events`, `contributors`, `avatar_state`, `identity_mappings` with migration scripts | SQLite | Medium | MVP |
| F17 | **Async Processing Queue** | In-process async queue that fans events out to the broadcast hub | F01-F08 | Medium | MVP |
| F18 | **State Reducer** | Apply normalized events to room/avatar state, update occupancy | F15, F17 | Medium | MVP |
| F19 | **WebSocket Broadcast Hub** | FastAPI WebSocket endpoint; manage connection registry; fan-out events to all subscribed clients | FastAPI WebSocket support, F17 | High | MVP |
| F20 | **Snapshot on Connect** | Send full state snapshot (contributors, room_occupancy, generated_at) to every newly connected client | F15, F19 | Medium | MVP |
| F21 | **Avatar Move Message** | WebSocket message: `type: avatar_move` with contributor_id, floor, room, event_type, timestamp | F19 | Low | MVP |
| F22 | **Leaderboard Update Message** | WebSocket message: `type: leaderboard_update` with contributor_id, score, delta, last_event | F19, leaderboard computation | Low | MVP |
| F23 | **WebSocket Auto-Reconnect** | Client reconnects after 2s on disconnect; receives fresh snapshot | F19, F20 | Medium | MVP |
| F24 | **HTTP Polling Fallback** | Client falls back to periodic HTTP polling when WebSocket unavailable | F19, REST endpoints | Medium | MVP |
| F25 | **Stale Data Indicators** | Flag out-of-order events with stale indicators in activity panel | F19, F18 | Low | MVP |
| F26 | **Three-Floor SVG/Canvas Renderer** | Render house layout with three floors, state-driven avatar positioning via SVG/Canvas | F19, F21, vanilla JS | High | MVP |
| F27 | **Room Occupancy Display** | Show occupancy count per room; +N counter when > 12 avatars | F26 | Low | MVP |
| F28 | **Dirty Region Redraw** | Only redraw rooms that changed on each update cycle, not full canvas | F26 | Medium | MVP |
| F29 | **Avatar Debouncing** | 5-second debounce window on avatar movement commits to prevent UI thrashing | F26, F21 | Low | MVP |
| F30 | **Activity Feed** | Display chronological activity feed payloads in UI | F06-F08, F19 | Medium | MVP |
| F31 | **Leaderboard Panel** | Live contributor scores, deltas, ranking, and leaderboard wall display | F22, F35-F37 | Medium | MVP |
| F32 | **Maintainer Visibility Panel** | Ecosystem status indicators and room occupancy heatmap | F19, F27 | Medium | MVP |
| F33 | **Leaderboard Computation** | Correct accumulation from GitHub + BLT signals; zero-point events filtering; conflict resolution | F05, F15 | Medium | MVP |
| F34 | **Mentor Lifecycle Projection** | Display mentor assignment states: assigned, handoff/pause, rematch | F05, mentor events | Medium | MVP |
| F35 | **Exponential Backoff Retries** | Slack retry: 1s→2s→4s→8s→max 32s with 500ms jitter | F02 | Low | Future (Week 9) |
| F36 | **Dead Letter Handling** | Dead letter queue capped at 500 events before drop with structured log entry | F17 | Medium | Future (Week 9) |
| F37 | **Gap Detection for GitHub Events** | Track `last_seen_event_id` per repo; periodic 90s polling of `/events` API | F01, SQLite | Medium | Future (Week 9) |
| F38 | **Health Endpoints** | Health check endpoints for all ingestion paths with structured logging | FastAPI, F01-F08 | Low | Future (Week 9) |
| F39 | **Unit Tests** | pytest tests for event adapters (real fixture payloads), identity resolver (all 4 match cases), room routing (all 10 event types), leaderboard projection | pytest, F06-F11, F14, F33 | Medium | Future (Week 10) |
| F40 | **Integration Tests** | Full chain: webhook → HMAC → normalization → SQLite → WebSocket broadcast; snapshot delivery; idempotency verification | F01-F20 | High | Future (Week 10) |
| F41 | **Load Tests** | Locust: 200 concurrent WebSocket clients for 10 min, 50 events/min ingest, p99 < 200ms broadcast latency | F19, locust | High | Future (Week 10) |
| F42 | **Docker Compose Deployment** | Single-command launch: FastAPI, SQLite volume, vanilla JS frontend | Docker, F26, F19 | Medium | Future (Week 11) |
| F43 | **Contributor Documentation** | Docs for adding new event adapters | — | Low | Future (Week 11) |
| F44 | **Maintainer Identity Confirmation Flow** | Overlay UI for maintainer to confirm or reject suggested identity links | F12, F13, F26 | Medium | Future (Week 11) |

---

**Summary**: 24 MVP features, 12 Post-MVP/future features. Total: 36 features.
