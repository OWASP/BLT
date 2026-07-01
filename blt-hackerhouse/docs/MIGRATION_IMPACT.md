# GitHub → GitLab Migration Impact Analysis

*Triggered by project context update: OWASP BLT migrated from GitHub to GitLab.*

---

## Scope Changes Summary

| Change | Impact |
|--------|--------|
| GitHub → GitLab | Primary SCM integration changes. Every GitHub reference must be replaced with GitLab equivalents. |
| Mentorship out of scope | Mentor rooms, mentor event types, mentor lifecycle projections removed from MVP. |
| Slack demoted to optional | Slack integration not blocked, but deferred until requirements validated. No Slack features in MVP scope. |
| Frontend architecture TBD | Frontend features noted but backend architecture decisions should not depend on them. |
| BLT API = source of truth | BLT API endpoints should use actual discovered endpoints, not assumed ones. |

---

## 1. Features Requiring Change

### Rename/Replace (GitHub → GitLab)

| ID | Current Name | New Name | Change Detail |
|----|-------------|----------|---------------|
| **F01** | GitHub Webhook Ingestion | **GitLab Webhook Ingestion** | Different verification mechanism: GitLab uses `X-Gitlab-Token` header secret token comparison, not HMAC-SHA256 signature. Different payload structure. Different webhook event types (Push, Merge Request, Issue, Note, Pipeline, Job). |
| **F06** | GitHub Event Normalizer | **GitLab Event Normalizer** | Field mapping changes: `sender.id` → `user.id`, `sender.login` → `user.username`, `repository.full_name` → `project.path_with_namespace`. Internal event type names change: `pr_opened` → `mr_opened`, `pr_merged` → `mr_merged`. CI event mapping differs (GitLab uses Pipeline/Job events vs GitHub Actions). |
| **F33** | Leaderboard Computation (GitHub + BLT) | **Leaderboard Computation (GitLab + BLT)** | Score sources change. GitLab MR merged events replace GitHub PR merged as scoring signal. |
| **F37** | Gap Detection for GitHub Events | **Gap Detection for GitLab Events** | GitLab Events API endpoint and response format differ from GitHub `/events`. |

### Demote from MVP to Optional/Future

| ID | Feature Name | Reason |
|----|-------------|--------|
| **F02** | Slack Events Ingestion | Slack treated as optional until requirements validated. |
| **F07** | Slack Event Normalizer | Depends on F02 being optional. |
| **F35** | Exponential Backoff Retries (Slack) | Slack adapter not in MVP scope. |

### Remove Entirely

| ID | Feature Name | Reason |
|----|-------------|--------|
| **F34** | Mentor Lifecycle Projection | Mentorship tracking explicitly out of scope for MVP. |

### Dependency Chains to Update

| Dependent Feature | Depends On | Action |
|-------------------|-----------|--------|
| F04 (Event Deduplication) | F01, F02, F03 | Change dependency F01→GitLab. F02 now optional. |
| F05 (Unified Event Schema) | F01, F02, F03 | Same. |
| F17 (Async Processing Queue) | F01-F08 | Remove F02, F07 from required deps. |
| F39 (Unit Tests) | F06-F11, F14, F33 | Replace F06 with GitLab equivalent. |
| F40 (Integration Tests) | F01-F20 | Replace F01 with GitLab equivalent. |

---

## 2. Requirements Requiring Change

### Functional Requirements

| ID | Current Text | Required Change |
|----|-------------|-----------------|
| **FR1** | Receive GitHub webhook events with HMAC-SHA256 signature verification. Invalid signatures rejected with 401. | Replace with: Receive GitLab webhook events with `X-Gitlab-Token` header verification against configured secret. Invalid/missing tokens rejected with 401. |
| **FR2** | Receive Slack event callbacks with verification via Slack Events API. | Demote to optional. Mark as: *Deferred — Slack treated as optional until requirements validated.* |
| **FR5** | Track last_seen_event_id per repository in SQLite to detect gaps during downtime. Periodic 90-second polling of /events API. | Still valid, but `/events` API is now GitLab's Events API, not GitHub's. |
| **FR8** | Map GitHub actions (opened, closed, merged) to internal event types: issue_opened, pr_opened, pr_merged, review_requested, ci_run. | Replace with: Map GitLab webhook event types to internal event types: `issue_opened`, `mr_opened`, `mr_merged`, `review_requested`, `pipeline_run`. GitLab distinguishes Push, Merge Request, Issue, Note, Pipeline, Job events with different object_kind values. |
| **FR9** | Map Slack and BLT events into equivalent workflow signals. | Slack removed from this requirement. Becomes: Map BLT events into equivalent workflow signals. |
| **FR11** | Resolve contributor identity across GitHub, Slack, and BLT using a three-stage pipeline. | Change platforms to: GitLab and BLT. |
| **FR14** | Send identity_flag WebSocket messages for fuzzy matches. | Still valid, but platforms in suggested_link change to GitLab + BLT. |
| **FR30** | House layout with mentor rooms. | **Remove**: Mentor Office, Strategy War Room. These rooms should be repurposed or removed from Floor 3. |
| **FR35** | Compute leaderboard projection from GitHub + BLT signals. | Change to: Compute leaderboard projection from GitLab + BLT signals. |
| **FR36** | Display mentor lifecycle projection: assigned, handoff/pause, rematch. | **Remove entirely** — mentorship out of MVP scope. |

### Non-Functional Requirements

| Current | Change |
|---------|--------|
| "BLT polling adapter isolated — failures do not break GitHub/Slack pipeline" | Change to: "...failures do not break GitLab pipeline." |
| Slack exponential backoff requirement | Demote to optional/future. |

---

## 3. Assumptions Requiring Change

| # | Current Assumption | New Reality |
|---|-------------------|-------------|
| 6 | "BLT webhook absence does not break the GitHub/Slack pipeline" | Change to: "...does not break the GitLab pipeline." Slack removed. |
| 7 | Docker Compose sufficient as sole deployment mechanism for MVP | Still valid. |
| 9 | "Three-platform scope — GitHub, Slack, and BLT only" | Change to: **Two-platform scope for MVP — GitLab and BLT.** Slack deferred. |

---

## 4. Risks Requiring Change

| Current Risk | Required Change |
|-------------|-----------------|
| **"Missed GitHub events during downtime"** | Rename to "**Missed GitLab events during downtime**". Mitigation: GitLab Events API endpoint differs from GitHub's. Verify GitLab supports comparable gap-detection endpoint. |
| **"BLT API instability"** — mentions "does not break GitHub/Slack pipeline" | Change to: "...does not break GitLab pipeline." |
| Slack API rate limits risk | Demote to optional/future. |

---

## 5. Architecture Components Requiring Change

### Event Ingestion Service

| Element | Current (GitHub) | Required (GitLab) |
|---------|-----------------|-------------------|
| Endpoint | `POST /webhook/github` | `POST /webhook/gitlab` |
| Verification | HMAC-SHA256 via `X-Hub-Signature-256` header | Secret token comparison via `X-Gitlab-Token` header |
| Payload structure | GitHub webhook format (`action`, `pull_request`, `issue`, `repository`) | GitLab webhook format (`object_kind`, `object_attributes`, `user`, `project`) |
| Identifier fields | `sender.id`, `sender.login` | `user.id`, `user.username` |
| Repo field | `repository.full_name` | `project.path_with_namespace` |

### Event Normalizer — GitLab Adapter

| Mapping | GitHub Field | GitLab Field | Internal Event |
|---------|-------------|-------------|----------------|
| Issue opened | `action: "opened"` + `issue` present | `object_kind: "issue"` + `object_attributes.action: "open"` | `issue_opened` |
| MR opened | `action: "opened"` + `pull_request` present | `object_kind: "merge_request"` + `object_attributes.action: "open"` | `mr_opened` |
| MR merged | `action: "closed"` + `pull_request.merged: true` | `object_kind: "merge_request"` + `object_attributes.action: "merge"` | `mr_merged` |
| Review requested | GitHub-specific event type | `object_kind: "merge_request"` + note/approval patterns, or use GitLab MR `reviewers` changes | `review_requested` |
| CI run | GitHub Actions `workflow_run` / `check_run` | `object_kind: "pipeline"` or `object_kind: "job"` | `pipeline_run` |

### Identity Mapper

| Aspect | Current | Required |
|--------|---------|----------|
| Platforms in resolution | GitHub, Slack, BLT | GitLab, BLT |
| `identity_mappings.platform` values | `github`, `slack`, `blt` | `gitlab`, `blt` |
| `contributors.platform_ids` JSON keys | `github_id`, `slack_id`, `blt_id` | `gitlab_id`, `blt_id` |

### Event Type → Room Mapping

| Current Event Type | Room | Action |
|-------------------|------|--------|
| `pr_opened` | Floor 2: Pull Request Room | Rename event to `mr_opened`. Room can be renamed to "Merge Request Room" or kept as "Pull Request Room" (minor). |
| `pr_merged` | Floor 3: Mentor Office | Rename event to `mr_merged`. **Room must be repurposed** — "Mentor Office" is mentorship-related. |
| `review_requested` | Floor 3: Code Review Room | Still valid for GitLab MR review requests. |
| `mentor_assigned` | Floor 3: Mentor Office | **REMOVE** — mentorship out of scope. |
| `mentor_handoff` | Floor 3: Strategy War Room | **REMOVE** — mentorship out of scope. |

### House Layout — Floor 3 Changes

**Current Floor 3**: Mentor Office · Code Review Room · Security Audit Room · Strategy War Room · Leaderboard Wall

**Required changes**: "Mentor Office" and "Strategy War Room" are mentorship-specific rooms that must be removed or repurposed. Candidates for replacement rooms (if needed):
- *Release Management Room* (for deploy/merge events)
- *Integration Testing Room*
- Merge the space into expanded Code Review Room and Leaderboard Wall

### Data Flows

| Flow | Change Required |
|------|----------------|
| **Flow 1: GitHub Push → UI** | Rename to **Flow 1: GitLab Webhook → UI**. HMAC-SHA256 verification → `X-Gitlab-Token` header verification. GitHub Adapter → GitLab Adapter. |
| **Flow 2: Slack → UI** | Demote to optional. Mark as *deferred*. |
| **Flow 7: Gap Detection** | GitHub `/events` API → GitLab Events API. Verify GitLab has equivalent paginated event stream endpoint. |

### Services Table

| Current | Required |
|---------|----------|
| External: GitHub (Webhooks + REST API) | External: GitLab (Webhooks + Events API) |
| External: Slack (Events API + Users API) | External: Slack (Optional — deferred) |

### Storage — `identity_mappings` Table

`platform_ids` column currently holds `{ "github_id": "...", "slack_id": "...", "blt_id": "..." }`. Change to `{ "gitlab_id": "...", "blt_id": "..." }` for MVP. Slack IDs can be added later.

### WebSocket Message Contract

The four message types (`snapshot`, `avatar_move`, `identity_flag`, `leaderboard_update`) are structurally sound and do not require schema changes. However:
- `identity_flag.suggested_link` platform values change from `github`/`slack` to `gitlab`/`blt`.
- The event_type values in `avatar_move` messages change from PR terminology to MR terminology.

---

## 6. BLT API Endpoint Verification

The proposal references `/api/issues/` and `/api/hunts/` as BLT polling targets. Based on actual BLT-API inspection:

| Assumed Endpoint | Actual BLT-API Endpoint | Notes |
|-----------------|------------------------|-------|
| `/api/issues/` | `/bugs` or `/v2/bugs` | BLT calls them "bugs", not "issues". BLT-API has full CRUD on bugs with pagination, status/domain/verified filters, and search. |
| `/api/hunts/` | `/hunts` or `/v2/hunts` | Valid. BLT-API proxies hunt data from Django backend. |

The polling adapter should use `/bugs` (not `/api/issues/`) as the primary BLT data source.

---

## 7. Previous BLT Contributions Context

The proposal lists 10 merged BLT PRs. Those PRs were made against GitHub. With the migration to GitLab, these are historical contributions. The BLT-API codebase we inspected is the current source of truth — a Python Cloudflare Worker with its own REST API structure, models, and authentication. Any adapter code should integrate against this BLT-API, not assumptions from the proposal.

---

## 8. Summary of Required Actions

### Must Change (blocking MVP correctness)

1. **F01** — Replace GitHub webhook endpoint with GitLab webhook endpoint. Different verification (token header instead of HMAC-SHA256).
2. **F06** — Replace GitHub normalizer with GitLab normalizer. Different field mappings, different event type names (MR not PR).
3. **F33** — Leaderboard computation sources: GitLab + BLT, not GitHub + BLT.
4. **FR1** — Rewrite to describe GitLab webhook verification.
5. **FR8** — Rewrite to describe GitLab event type mapping.
6. **FR35** — Leaderboard from GitLab + BLT signals.
7. **Assumption 9** — Two-platform scope (GitLab + BLT).
8. **All architecture docs** — Replace every GitHub field reference (`sender.id`, `sender.login`, `repository.full_name`) with GitLab equivalents (`user.id`, `user.username`, `project.path_with_namespace`).
9. **Event type names** — `pr_opened`→`mr_opened`, `pr_merged`→`mr_merged`, `ci_run`→`pipeline_run`.

### Must Remove (mentorship out of scope)

10. **F34** — Mentor Lifecycle Projection.
11. **FR36** — Mentor lifecycle projection display.
12. **Floor 3 rooms** — Mentor Office, Strategy War Room. Need replacement rooms.
13. **Event types** — `mentor_assigned`, `mentor_handoff`.
14. **Analytics overlay** — Mentor lifecycle projection component.

### Must Demote (Slack optional)

15. **F02** — Slack Events Ingestion → move from MVP to future.
16. **F07** — Slack Event Normalizer → move from MVP to future.
17. **F35** — Slack exponential backoff → future.
18. **FR2** — Slack callbacks → mark as deferred.
19. **FR9** — Slack event mapping → remove Slack reference.

### Must Verify

20. **BLT endpoints** — Use `/bugs` and `/v2/bugs`, not `/api/issues/`.
21. **GitLab Events API** — Verify GitLab has a pageable event stream for gap detection (Flow 7 equivalent).
22. **GitLab webhook event types** — Confirm exact `object_kind` values and nested action fields for all needed event types.
