# Data Model Design — BLT-Hackerhouse

*Complete relational schema for the MVP backend. Designed for SQLite via aiosqlite.*

---

## Design Principles

1. **UUIDs for distributed-friendly PKs** — All entity tables use TEXT UUID primary keys. Allows identity creation in-memory before any DB round-trip. Avoids auto-increment collision risk if scaling to multiple workers.
2. **JSON columns for flexible platform data** — `usernames`, `aliases`, and `platform_ids` stored as JSON arrays/objects instead of normalized junction tables. Justified: these are append-only lists queried in full (not individually filtered), and identity resolution loads all candidates into memory anyway. Keeps the contributor table to one row per person.
3. **SQLite types as TEXT with constraints** — SQLite has dynamic typing. All `TEXT` columns use CHECK constraints for domain validation. Booleans stored as INTEGER 0/1. Timestamps stored as ISO 8601 TEXT (SQLite has no native datetime type; TEXT enables sortable, human-readable values).
4. **No soft deletes** — MVP scale (50–200 contributors, low thousands of events) doesn't need soft deletes. `DELETE` is fine. The dead letter queue preserves failed events.
5. **Idempotency via UNIQUE constraint** — Not via application-level check-then-insert (which has a race condition). The `UNIQUE` index on `idempotency_key` makes duplicate inserts fail at the DB level. The application catches the constraint violation and treats it as a no-op.

---

## Entity-Relationship Overview

```
┌──────────┐         ┌──────────────────┐         ┌─────────────┐
│   events │         │ identity_mappings│         │ contributors │
│          │  N:1    │                  │  N:1    │             │
│  PK id   │────────▶│  PK id           │────────▶│  PK id      │
│  contrib │         │  contributor_id  │         │  score      │
│  idemp…  │         │  platform        │         │  usernames  │
│  source  │         │  platform_user_id│         │  aliases    │
│  event…  │         │  confidence      │         │  is_linked  │
└──────────┘         └──────────────────┘         └─────────────┘
                                                          │
                                                          │ 1:1
                                                          ▼
                                                   ┌─────────────┐
                                                   │ avatar_state│
                                                   │             │
                                                   │  PK contrib │
                                                   │  floor      │
                                                   │  room       │
                                                   │  last_event │
                                                   └─────────────┘

Supporting tables (no FKs to entities):

┌──────────────┐      ┌───────────────────┐
│ poll_cursors │      │ dead_letter_queue │
│              │      │                   │
│ PK source    │      │ PK id             │
│ last_seen_id │      │ event_id          │
│ last_polled  │      │ source            │
└──────────────┘      │ error             │
                      │ attempts          │
                      └───────────────────┘
```

**Cardinality notes**:
- One contributor can have 1–N `identity_mappings` (one per platform: GitLab + BLT).
- One contributor has exactly 0 or 1 `avatar_state` rows (0 if they have no events yet).
- One event has 0 or 1 contributor (0 until identity resolution runs; set to contributor_id after).
- `poll_cursors` is a key-value store, not relational.

---

## Table: `contributors`

*Unified identity — one row per real-world person, regardless of how many platforms they appear on.*

| Column | Type | Constraints | Rationale |
|--------|------|-------------|-----------|
| `id` | TEXT | PRIMARY KEY | UUID v4 generated at identity creation time. Not an auto-increment integer — enables offline UUID generation in the identity resolver before any DB write. |
| `display_name` | TEXT | NOT NULL | Primary display name shown in the house UI. Set from the first observed `actor_name` for this contributor. Can be updated if a better name is resolved later. |
| `usernames` | TEXT | NOT NULL, DEFAULT '[]' | JSON array of lowercase usernames collected across all platforms. Example: `["rudra-rps", "rudra_pratap_singh"]`. Used by Stage 2 of identity resolution (Levenshtein distance lookup). New usernames appended when new platform identities link to this contributor. |
| `aliases` | TEXT | NOT NULL, DEFAULT '[]' | JSON array of display name variations. Example: `["Rudra Pratap Singh", "Rudra Singh"]`. Used by Stage 3 of identity resolution (Jaccard token-set similarity). |
| `platform_ids` | TEXT | NOT NULL, DEFAULT '{}' | JSON object mapping platform → platform-native user ID. Example: `{"gitlab_id": "12345", "blt_id": "678"}`. Populated as identity mappings are created. Used to check if a platform identity is already linked before creating a duplicate mapping. |
| `is_linked` | INTEGER | NOT NULL, DEFAULT 0, CHECK(is_linked IN (0, 1)) | 0 = identity only confirmed on one platform (or unlinked). 1 = confirmed linked across at least two platforms. Set to 1 automatically when a second `identity_mappings` row is created for this contributor with a different platform. |
| `score` | INTEGER | NOT NULL, DEFAULT 0 | Accumulated contributor score for leaderboard. Updated atomically on each scorable event: `UPDATE contributors SET score = score + ? WHERE id = ?`. |
| `created_at` | TEXT | NOT NULL, DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | ISO 8601 UTC. Set once at row creation. |
| `updated_at` | TEXT | NOT NULL, DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | ISO 8601 UTC. Updated on every change (display_name change, new username appended, score change, is_linked toggled). Application MUST explicitly set this in UPDATE statements — SQLite triggers could handle it but explicit is clearer for aiosqlite. |

**Indexes**:

| Index Name | Columns | Purpose |
|-----------|---------|---------|
| `idx_contributors_score` | `score DESC` | Leaderboard queries: `SELECT id, display_name, score FROM contributors ORDER BY score DESC LIMIT 20` |
| `idx_contributors_is_linked` | `is_linked` | Status dashboard: count linked vs unlinked contributors |

**Why JSON columns instead of normalized tables?**

Alternative design: `contributor_usernames(contributor_id, username)` and `contributor_platform_ids(contributor_id, platform, platform_user_id)` as separate tables. This would be correct for a traditional RDBMS. But here:

1. **Identity resolution loads all candidates into memory anyway** — The resolver does `SELECT * FROM contributors` to run fuzzy matching. Normalizing usernames doesn't reduce the data loaded.
2. **No filtering on JSON fields** — We never run `WHERE username = 'rudra-rps'` (that's what `identity_mappings` is for). JSON columns are only read in full.
3. **Simpler code** — Appending a username is `json.loads(row['usernames']).append(new_name)` then `json.dumps()`. No multi-table transaction.
4. **SQLite has first-class JSON support** — `json_extract()`, `json_array_length()`, `json_each()` are available if needed later.

---

## Table: `identity_mappings`

*Maps a platform-specific user ID to a unified contributor. One row per platform identity. Enables Stage 1 exact matching and maintains linkage confidence.*

| Column | Type | Constraints | Rationale |
|--------|------|-------------|-----------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Simple auto-increment. Used only for internal row identity — never exposed in API responses. |
| `platform` | TEXT | NOT NULL, CHECK(platform IN ('gitlab', 'blt')) | Which platform this mapping is for. Currently only two values. Adding Slack later means adding `'slack'` to the CHECK constraint. |
| `platform_user_id` | TEXT | NOT NULL | The platform's native user identifier. GitLab: integer user ID as string (e.g. `"12345"`). BLT: user ID from BLT-API (`user.id` field as string). |
| `contributor_id` | TEXT | NOT NULL, REFERENCES contributors(id) | FK to the unified contributor. This is the link that says "GitLab user 12345 is the same person as contributor UUID abc-123". |
| `confidence` | REAL | NOT NULL, CHECK(confidence >= 0.0 AND confidence <= 1.0) | How confident the resolver is that this mapping is correct. 1.0 = exact platform ID match. 0.75 = Levenshtein fuzzy match. 0.60 = Jaccard fuzzy match. 0.0 = unlinked (no match found — new contributor created). |
| `confirmed_by` | TEXT | nullable | Set when a maintainer manually confirms or rejects a fuzzy match via the overlay UI. Null means not yet reviewed. Value is the maintainer's identifier or "auto". Could store the action: `"confirmed"` or `"rejected"`. |
| `created_at` | TEXT | NOT NULL, DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | Row creation timestamp. |

**Indexes**:

| Index Name | Columns | Purpose |
|-----------|---------|---------|
| `uq_identity_platform_user` | `(platform, platform_user_id)` UNIQUE | Stage 1 exact match: `SELECT contributor_id, confidence FROM identity_mappings WHERE platform = ? AND platform_user_id = ?`. UNIQUE prevents duplicate mappings for the same platform identity. |
| `idx_identity_contributor` | `contributor_id` | Reverse lookup: "which platforms is contributor X linked to?" Used when a new mapping is confirmed and we need to update `contributors.platform_ids` and check `is_linked`. |

**UNIQUE constraint behavior**: If a GitLab user ID is already mapped to contributor A and the resolver tries to create a new mapping to contributor B, the INSERT fails with a constraint violation. The application catches this and treats it as: this identity is already resolved. This prevents duplicate mappings silently.

---

## Table: `events`

*Normalized event log. One row per ingested event from any source. The canonical record of all contributor activity.*

| Column | Type | Constraints | Rationale |
|--------|------|-------------|-----------|
| `id` | TEXT | PRIMARY KEY | UUID v4 generated at normalization time (VF04). Used as the canonical event identifier in API responses, activity feed, and dead letter queue references. |
| `source` | TEXT | NOT NULL, CHECK(source IN ('gitlab', 'blt')) | Which platform this event came from. |
| `event_type` | TEXT | NOT NULL | Internal event type: `issue_opened`, `mr_opened`, `mr_merged`, `review_requested`, `pipeline_run`, `note_added`, `bug_bounty_submitted`, `bug_status_change`, `hunt_activity`, `unknown`. |
| `actor_id` | TEXT | NOT NULL | Platform-native user ID at time of ingestion. GitLab: `user.id` (integer → string). BLT: `data.user` or `data.id` from polled record. Retained even after identity resolution for debugging — "who was the raw actor?" |
| `actor_name` | TEXT | NOT NULL | Display name at time of ingestion. GitLab: `user.username`. BLT: resolved username or ID fallback. |
| `contributor_id` | TEXT | nullable, REFERENCES contributors(id) | Set AFTER identity resolution runs. NULL when event is first persisted, then updated. Allows event to be stored before identity is resolved (the reducer sets this field as a separate step). |
| `repository` | TEXT | NOT NULL, DEFAULT '' | GitLab: `project.path_with_namespace` (e.g. `"OWASP-BLT/BLT"`). BLT: repo name extracted from hunt data. |
| `timestamp` | TEXT | NOT NULL | ISO 8601 UTC. When the event happened on the source platform (not when we ingested it). Parsed from source payload (`object_attributes.created_at` for GitLab, `data.created` for BLT). |
| `metadata` | TEXT | NOT NULL, DEFAULT '{}' | JSON blob of source-specific fields preserved for the activity feed and overlay. GitLab: `{title, description, url, state, source_branch, target_branch, pipeline_status, note_body}`. BLT: `{bug_id, url, description, status, hunt_id, domain_name}`. |
| `idempotency_key` | TEXT | NOT NULL, UNIQUE | Format: `{source}:{event_type}:{actor_id}:{timestamp}`. Example: `"gitlab:mr_opened:12345:2026-07-15T10:22:00Z"`. Enforced via UNIQUE constraint — duplicate webhook deliveries cause INSERT failure, which the application catches and silently drops. |
| `sequence_number` | INTEGER | NOT NULL, AUTOINCREMENT alternative | Monotonically increasing number assigned at insert time. Used by the WebSocket layer for out-of-order detection on the client side. SQLite's `rowid` could serve this purpose, but an explicit column avoids relying on internal implementation details. |
| `created_at` | TEXT | NOT NULL, DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | When we persisted this event (may differ from `timestamp` which is when it happened at the source). |

**Indexes**:

| Index Name | Columns | Purpose |
|-----------|---------|---------|
| `uq_events_idempotency` | `(idempotency_key)` UNIQUE | Deduplication. Also serves as a lookup index. |
| `idx_events_contributor` | `contributor_id` | "All events for contributor X" queries (user profile, activity filtering). |
| `idx_events_timestamp` | `timestamp DESC` | Activity feed: `SELECT * FROM events ORDER BY timestamp DESC LIMIT 50`. Most common query. |
| `idx_events_source_type` | `(source, event_type)` | Filtering activity feed by source or event type: `WHERE source = 'gitlab'` or `WHERE event_type = 'mr_merged'`. |
| `idx_events_sequence` | `sequence_number` | Used by gap detector to find events after a certain sequence number. |

**Why store metadata as JSON text instead of normalized columns?**

The `metadata` fields vary significantly by source and event type. A GitLab `mr_opened` event has `source_branch` and `target_branch`. A BLT `bug_bounty_submitted` event has `bug_id` and `domain_name`. Normalizing this into separate columns would require either (a) dozens of nullable columns, or (b) an EAV pattern with a separate `event_metadata` table. JSON blob is simpler, directly matches the Pydantic `Event.metadata: dict` field, and SQLite can query inside JSON with `json_extract()` if needed later.

---

## Table: `avatar_state`

*Current position of each contributor in the three-floor house. One row per contributor (INSERT OR REPLACE pattern).*

| Column | Type | Constraints | Rationale |
|--------|------|-------------|-----------|
| `contributor_id` | TEXT | PRIMARY KEY, REFERENCES contributors(id) | One row per contributor. Using contributor_id as PK means `INSERT OR REPLACE` naturally upserts — no separate UPDATE vs INSERT logic needed. |
| `floor` | INTEGER | NOT NULL, CHECK(floor BETWEEN 1 AND 3) | Which floor the avatar is on: 1 (Operations), 2 (Development), 3 (Review & Leadership). |
| `room` | TEXT | NOT NULL | Room identifier matching `ROOM_MAP` keys: `issue_triage_desk`, `merge_request_room`, `code_review_room`, etc. |
| `last_event` | TEXT | NOT NULL | Most recent `event_type` that caused this contributor to move. Displayed in the UI: "Last seen: mr_merged". |
| `updated_at` | TEXT | NOT NULL, DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | When this position was last updated. Used by the snapshot builder to include `generated_at` and by the frontend to show "last active X minutes ago". |

**Indexes**:

| Index Name | Columns | Purpose |
|-----------|---------|---------|
| `idx_avatar_room` | `(floor, room)` | Room occupancy query: `SELECT room, COUNT(*) as count FROM avatar_state GROUP BY floor, room`. |
| `idx_avatar_updated` | `updated_at` | Cleanup/staleness detection: find avatars that haven't moved in N hours. |

**No separate index on `contributor_id`** — it's the PK, which SQLite already indexes.

**Why INSERT OR REPLACE instead of UPSERT?**

`INSERT OR REPLACE` is simpler and idempotent. The reducer doesn't need to check if a row already exists — it just issues `INSERT OR REPLACE INTO avatar_state (...) VALUES (...)` with the new position. If the contributor already had a row, it's replaced. If they didn't, it's inserted. This matches the "one row per contributor, always current position" model perfectly.

---

## Table: `poll_cursors`

*Tracks the last-seen record ID for each polling source. Enables the BLT polling adapter to fetch only new records.*

| Column | Type | Constraints | Rationale |
|--------|------|-------------|-----------|
| `source` | TEXT | PRIMARY KEY | Unique identifier for the polling source. Values: `"blt_bugs"`, `"blt_hunts"`. Could be extended with `"gitlab_project_{id}"` for the gap detector. |
| `last_seen_id` | INTEGER | NOT NULL, DEFAULT 0 | Highest record ID seen in the previous poll. BLT bugs: `bugs.id`. BLT hunts: hunt ID from `/hunts` response. Starts at 0 (fetch all records on first poll). |
| `last_polled_at` | TEXT | nullable | ISO 8601 UTC. When the last successful poll completed. NULL if never polled. Used by health endpoint to detect stalled pollers. |

**Indexes**: None needed. Single-row lookup by PK.

**This is a key-value table, not a relational table** — the `source` column is the key. Could be implemented as an in-memory dict for the MVP, but persisting it ensures poll state survives restarts.

---

## Table: `dead_letter_queue`

*Failed events that could not be processed after all retries. Capped at 500 rows.*

| Column | Type | Constraints | Rationale |
|--------|------|-------------|-----------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Simple auto-increment. |
| `event_id` | TEXT | NOT NULL | UUID of the Event that failed. References `events.id` (but no FK — the event might not have been persisted if failure happened before INSERT). |
| `source` | TEXT | NOT NULL | Which source the event came from (`gitlab` or `blt`). |
| `error` | TEXT | NOT NULL | Error message and/or stack trace. Human-readable for debugging. |
| `attempts` | INTEGER | NOT NULL, DEFAULT 1 | How many times processing was attempted before failure. Includes the initial attempt plus retries. |
| `last_attempt_at` | TEXT | NOT NULL | ISO 8601 UTC. When the last failed attempt occurred. |
| `created_at` | TEXT | NOT NULL, DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | When this dead letter entry was created. |

**Indexes**:

| Index Name | Columns | Purpose |
|-----------|---------|---------|
| `idx_dead_letter_created` | `created_at` | FIFO eviction: `DELETE FROM dead_letter_queue WHERE id = (SELECT id FROM dead_letter_queue ORDER BY created_at ASC LIMIT 1)` when queue exceeds 500. |

**Capping logic**: Before INSERT, check `SELECT COUNT(*) FROM dead_letter_queue`. If ≥ 500, DELETE the oldest row (by `created_at`) first. Then INSERT the new row. This is done in a transaction to prevent race conditions.

---

## Table: `schema_migrations`

*Tracks which migration scripts have been applied. Standard practice for sequential migration systems.*

| Column | Type | Constraints | Rationale |
|--------|------|-------------|-----------|
| `version` | TEXT | PRIMARY KEY | Migration filename without extension: `"001"`, `"002"`, etc. |
| `applied_at` | TEXT | NOT NULL, DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | When this migration was run. |

This table is created by the migration runner itself (`storage/migrations.py`) on first run — it's not part of the 001 migration file.

---

## Relationships Summary

| Parent | Child | Type | FK Column |
|--------|-------|------|-----------|
| `contributors` | `identity_mappings` | 1:N | `identity_mappings.contributor_id` |
| `contributors` | `events` | 1:N | `events.contributor_id` (nullable) |
| `contributors` | `avatar_state` | 1:1 | `avatar_state.contributor_id` (PK = FK) |

No FKs between support tables (`poll_cursors`, `dead_letter_queue`, `schema_migrations`) and entity tables.

---

## Query Patterns (Validation)

Every query needed by MVP features can be expressed cleanly with this schema:

| Feature | Query |
|---------|-------|
| **Stage 1 identity match** | `SELECT contributor_id FROM identity_mappings WHERE platform = ? AND platform_user_id = ?` — covered by `uq_identity_platform_user` |
| **Stage 2+3 identity match** | `SELECT id, usernames, aliases FROM contributors` — full scan, expected < 200 rows |
| **Create identity mapping** | `INSERT INTO identity_mappings (...)` — UNIQUE prevents duplicates |
| **Create unlinked contributor** | `INSERT INTO contributors (...)` + `INSERT INTO identity_mappings (...)` |
| **Persist event** | `INSERT INTO events (...)` — UNIQUE on idempotency_key catches duplicates |
| **Update avatar state** | `INSERT OR REPLACE INTO avatar_state (...)` |
| **Room occupancy** | `SELECT room, COUNT(*) FROM avatar_state GROUP BY room` — covered by `idx_avatar_room` |
| **Snapshot** | `SELECT c.id, c.display_name, c.is_linked, c.score, a.floor, a.room, a.last_event FROM contributors c LEFT JOIN avatar_state a ON c.id = a.contributor_id` |
| **Activity feed** | `SELECT * FROM events ORDER BY timestamp DESC LIMIT ? OFFSET ?` — covered by `idx_events_timestamp` |
| **Leaderboard** | `SELECT id, display_name, score FROM contributors WHERE score > 0 ORDER BY score DESC LIMIT ?` — covered by `idx_contributors_score` |
| **Score update** | `UPDATE contributors SET score = score + ?, updated_at = ? WHERE id = ?` |
| **Poll cursor** | `SELECT last_seen_id FROM poll_cursors WHERE source = ?` + `INSERT OR REPLACE INTO poll_cursors (...)` |
| **Dead letter insert** | `INSERT INTO dead_letter_queue (...)` |
| **Dead letter eviction** | `DELETE FROM dead_letter_queue WHERE id = (SELECT id FROM dead_letter_queue ORDER BY created_at ASC LIMIT 1)` |
| **Health: event count** | `SELECT COUNT(*) FROM events` |
| **Health: linked %** | `SELECT COUNT(*) FILTER (WHERE is_linked = 1) * 100.0 / COUNT(*) FROM contributors` |

---

## Migration Order

| File | Creates |
|------|---------|
| `001_contributors.sql` | `contributors` table + indexes |
| `002_identity_mappings.sql` | `identity_mappings` table + indexes + FK to contributors |
| `003_events.sql` | `events` table + indexes + FK to contributors |
| `004_avatar_state.sql` | `avatar_state` table + indexes + FK to contributors |
| `005_poll_cursors.sql` | `poll_cursors` table |
| `006_dead_letter_queue.sql` | `dead_letter_queue` table + index |

Rationale for ordering: `contributors` first because `identity_mappings` and `events` and `avatar_state` all reference it. Support tables (`poll_cursors`, `dead_letter_queue`) last since they have no FKs.

---

## Data Types Reference (SQLite)

| Logical Type | SQLite Declaration | Notes |
|-------------|-------------------|-------|
| UUID | `TEXT` | Stored as 36-char string. No native UUID type. |
| ISO 8601 timestamp | `TEXT` | Sortable lexicographically. Application enforces format. |
| Boolean | `INTEGER` with CHECK IN (0, 1) | SQLite has no boolean. 0/1 with constraint. |
| JSON array/object | `TEXT` | Application serializes with `json.dumps()`. SQLite `json_*` functions available for queries. |
| Enum (platform, source) | `TEXT` with CHECK IN (...) | Application-level enum enforced at DB level. |
| Integer | `INTEGER` | Native SQLite integer (64-bit signed). |
| Float | `REAL` | Native SQLite float (8-byte IEEE). |

---

## Estimated Row Counts at MVP Scale

| Table | Estimated Rows | Growth Rate |
|-------|---------------|-------------|
| `contributors` | 50–200 | ~1/week |
| `identity_mappings` | 100–400 | ~2× contributors (one row per platform per person) |
| `events` | 500–3,000 | ~10–30/day |
| `avatar_state` | 50–200 | Exactly one per contributor |
| `poll_cursors` | 2–10 | Fixed (one per data source) |
| `dead_letter_queue` | 0–500 | Rare (capped) |

Total DB size: < 10 MB. Indexes: < 2 MB. Well within SQLite's comfort zone (SQLite handles databases up to 140 TB).
