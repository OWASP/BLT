# Architecture Review — BLT-Hackerhouse

*Pre-implementation review of all planning documents. Produced 2026-06-12.*

---

## Documents Under Review

| # | Document | Created | Purpose |
|---|----------|---------|---------|
| 1 | `PROPOSAL_BREAKDOWN.md` | Early planning | Extracted goals, requirements, risks from proposal PDF |
| 2 | `FEATURE_INVENTORY.md` | Early planning | Catalogued 36 features from proposal |
| 3 | `ARCHITECTURE_EXTRACTION.md` | Early planning | Extracted components, services, data flows from proposal |
| 4 | `MIGRATION_IMPACT.md` | Mid planning | Analyzed changes needed for GitHub→GitLab, mentorship removal, Slack deferral |
| 5 | `MVP_V1_SPEC.md` | Late planning | Final MVP spec with 20 GitLab-based backend features |
| 6 | `REPOSITORY_STRUCTURE.md` | Late planning | Package boundaries, module responsibilities, dependency rules |
| 7 | `POST_MVP_BACKLOG.md` | Late planning | Consolidated all removed/deferred/post-MVP items |

---

## Outdated Assumptions

### PROPOSAL_BREAKDOWN.md

| Line/Topic | Outdated Content | Current Reality |
|------------|-----------------|-----------------|
| Project Goal #1 | "GitHub, Slack, BLT" | GitLab, BLT (Slack deferred) |
| Project Goal #4 | "GitHub, Slack, and BLT" | GitLab and BLT |
| FR1 | GitHub webhooks with HMAC-SHA256 verification | GitLab webhooks with X-Gitlab-Token verification |
| FR2 | Slack Events API callbacks | Deferred |
| FR5 | GitHub `/events` API | GitLab Events API |
| FR8 | `pr_opened`, `pr_merged`, `ci_run` | `mr_opened`, `mr_merged`, `pipeline_run` |
| FR9 | "Slack and BLT events" | BLT events only |
| FR11 | "GitHub, Slack, and BLT" | GitLab and BLT |
| FR30 | Lists "Mentor Office", "Strategy War Room" | Removed — replaced with Release Management Room, no Strategy War Room |
| FR35 | "GitHub + BLT signals" | GitLab + BLT signals |
| FR36 | "Mentor lifecycle projection" | Removed entirely |
| Data Sources table | GitHub webhooks, Slack Events API | GitLab webhooks only for push; BLT for poll |
| Assumption #6 | "does not break GitHub/Slack pipeline" | "does not break GitLab pipeline" |
| Assumption #9 | "GitHub, Slack, and BLT" | GitLab and BLT |
| Risks table | "Missed GitHub events" | "Missed GitLab events" |
| Risks table | BLT instability "does not break GitHub/Slack pipeline" | "does not break GitLab pipeline" |

**Verdict**: 17 outdated references. Document is a faithful extraction of the original proposal but is now a historical artifact. All corrected requirements live in `MVP_V1_SPEC.md`.

---

### FEATURE_INVENTORY.md

| ID | Outdated Content | Current Reality |
|----|-----------------|-----------------|
| F01 | "GitHub Webhook Ingestion" with HMAC-SHA256 | VF01: GitLab Webhook Ingestion with X-Gitlab-Token |
| F02 | "Slack Events Ingestion" | Removed from MVP |
| F06 | "GitHub Event Normalizer" | VF05: GitLab Event Normalizer |
| F07 | "Slack Event Normalizer" | Removed from MVP |
| F33 | "GitHub + BLT" leaderboard sources | VF16: GitLab + BLT |
| F34 | "Mentor Lifecycle Projection" | Removed entirely |
| F35 | "Slack exponential backoff" | Removed from MVP |
| F37 | "GitHub Events" gap detection | VF19: GitLab Events API |

**Verdict**: Uses the F01–F36 numbering system that was replaced by VF01–VF20 in `MVP_V1_SPEC.md`. The F01–F36 system is now obsolete. Corrected feature catalog lives in `MVP_V1_SPEC.md` #MVP Features Summary table and `POST_MVP_BACKLOG.md`.

---

### ARCHITECTURE_EXTRACTION.md

| Section | Outdated Content | Current Reality |
|---------|-----------------|-----------------|
| Component 1 | GitHub webhook with HMAC-SHA256 | GitLab webhook with X-Gitlab-Token (`REPOSITORY_STRUCTURE.md` ingestion/gitlab_webhook.py) |
| Component 1 | Slack event endpoint | Removed |
| Component 2 | GitHub Adapter mapping `sender.id`, `sender.login` | GitLab Adapter mapping `user.id`, `user.username` |
| Component 2 | Slack Adapter | Removed |
| Component 3 | Identity resolution across GitHub + Slack + BLT | GitLab + BLT only |
| Component 4 | Gap tracking for "GitHub events" | GitLab Events API |
| Component 8 | "Mentor lifecycle projection" | Removed |
| Component 8 | "GitHub + BLT" leaderboard signals | GitLab + BLT |
| Services table | External: GitHub webhooks, External: Slack | External: GitLab webhooks, Slack deferred |
| Flow 1 | "GitHub Push Webhook" | Renamed to "GitLab Webhook" in MVP_V1_SPEC architecture diagram |
| Flow 2 | "Slack Push Event" | Removed |
| Flow 7 | GitHub `/events` API for gap detection | GitLab Events API |
| Event→Room table | `pr_opened`, `pr_merged` | `mr_opened`, `mr_merged` |
| Event→Room table | `mentor_assigned`, `mentor_handoff` | Removed |
| House Layout Floor 3 | "Mentor Office", "Strategy War Room" | "Release Management Room", Strategy War Room removed |
| Storage `identity_mappings` | `platform_ids` with `github_id`, `slack_id`, `blt_id` | `gitlab_id`, `blt_id` |
| WebSocket `identity_flag` | platform values `github`/`slack` | platform values `gitlab`/`blt` |

**Verdict**: 22 outdated references. The `MVP_V1_SPEC.md` architecture diagram (VF section) and `REPOSITORY_STRUCTURE.md` package design are the corrected replacements.

---

### MIGRATION_IMPACT.md

This document identified 22 required changes across features, requirements, architecture, and scope. **All 22 changes have been fully applied** to `MVP_V1_SPEC.md` and `REPOSITORY_STRUCTURE.md`.

Specific confirmations:
- ✅ GitHub → GitLab (F01, F06, F33, F37 renamed; FR1, FR8, FR35 rewritten)
- ✅ Mentorship removed (F34, FR36, Mentor Office, Strategy War Room, `mentor_assigned`, `mentor_handoff`)
- ✅ Slack deferred (F02, F07, F35, FR2, FR9)
- ✅ BLT endpoints corrected (`/api/issues/` → `/bugs`)
- ✅ All architecture diagrams updated in MVP_V1_SPEC.md

**Verdict**: This document served its purpose as a transition analysis. All findings have been applied. It is now a historical record of the migration rationale.

---

## Duplicate Information

| Information | Appears In |
|-------------|-----------|
| Feature catalog (F01–F36) | `FEATURE_INVENTORY.md` (original, outdated) |
| Feature catalog (VF01–VF20) | `MVP_V1_SPEC.md` (current, correct) |
| Architecture components list | `ARCHITECTURE_EXTRACTION.md` (original, GitHub-based) |
| Architecture components list | `MVP_V1_SPEC.md` Architecture Overview diagram (current, GitLab-based) |
| Architecture components list | `REPOSITORY_STRUCTURE.md` Module Responsibilities Map (current, mapped to files) |
| SQLite schema (4 tables) | `ARCHITECTURE_EXTRACTION.md` Storage Requirements |
| SQLite schema (6 tables, full columns) | `MVP_V1_SPEC.md` VF09 |
| ROOM_MAP + house layout | `ARCHITECTURE_EXTRACTION.md` Event Flows (mentorship rooms) |
| ROOM_MAP + house layout | `MVP_V1_SPEC.md` VF08 (corrected, no mentorship) |
| WebSocket message contract | `ARCHITECTURE_EXTRACTION.md` |
| WebSocket message contract | `MVP_V1_SPEC.md` VF11 |
| Event type → room mapping | `ARCHITECTURE_EXTRACTION.md` (GitHub events, mentorship events) |
| Event type → room mapping | `MVP_V1_SPEC.md` VF08 (GitLab events, no mentorship) |
| Requirement IDs (FR1–FR39) | `PROPOSAL_BREAKDOWN.md` |
| Requirement IDs (implicit in VF features) | `MVP_V1_SPEC.md` |
| Risk list | `PROPOSAL_BREAKDOWN.md` (GitHub/Slack referenced) |
| Scope exclusions | `PROPOSAL_BREAKDOWN.md` (original non-goals) |
| Scope exclusions | `MVP_V1_SPEC.md` Scope Boundaries table |
| Scope exclusions | `POST_MVP_BACKLOG.md` (consolidated, final) |

---

## Content Gaps

| Gap | Where It Matters | Recommendation |
|-----|-----------------|----------------|
| No data model design doc | Implementation needs column-level schema | Create `DATA_MODEL.md` — covered by this review's Task 2 |
| No API contract catalog | Implementation needs exact request/response shapes | `MVP_V1_SPEC.md` VF01–VF20 already includes API Contracts for each feature. Sufficient for implementation. |
| No environment variable catalog | `config.py` needs to know all env vars | Extract from `MVP_V1_SPEC.md` VFs — each feature declares its env deps. Create `.env.example` during implementation. |
| No error handling taxonomy | Implementation needs consistent error patterns | Not documented. Define during implementation: 401 (auth), 422 (validation), 429 (rate limit), 500 (internal), 503 (external service down). |

---

## Recommendations

### Documents to Retain as Long-Term References

| Document | Reason |
|----------|--------|
| **MVP_V1_SPEC.md** | Primary implementation specification. All 20 features with contracts, data models, dependencies. **Must stay.** |
| **REPOSITORY_STRUCTURE.md** | Package design, dependency rules, module-to-feature mapping. **Must stay.** |
| **POST_MVP_BACKLOG.md** | Consolidated deferred/removed items. Reference for future planning. **Should stay.** |

### Documents to Archive

| Document | Reason |
|----------|--------|
| **PROPOSAL_BREAKDOWN.md** | Faithful extraction of the original proposal but superseded by MVP_V1_SPEC.md. Contains 17 outdated GitHub/Slack/mentorship references. Historical value only — preserves what the proposer originally committed to. |
| **FEATURE_INVENTORY.md** | Uses obsolete F01–F36 numbering. Superseded by VF01–VF20 in MVP_V1_SPEC.md and POST_MVP_BACKLOG.md. Historical value only. |
| **ARCHITECTURE_EXTRACTION.md** | Contains 22 outdated references (GitHub, Slack, mentorship rooms). Superseded by MVP_V1_SPEC.md architecture diagram + REPOSITORY_STRUCTURE.md package design. Historical value only. |
| **MIGRATION_IMPACT.md** | Transition document. All 22 findings fully applied. Useful as migration rationale record but not needed for implementation. |

### Documents to Delete

None. All documents have historical or transitional value. The three original extraction documents plus the migration analysis document should be archived, not deleted.

### Proposed Archive Structure

```
docs/
├── archive/                              # Planning artifacts (historical reference)
│   ├── PROPOSAL_BREAKDOWN.md            # Original proposal extraction
│   ├── FEATURE_INVENTORY.md             # Original feature catalog (F01-F36)
│   ├── ARCHITECTURE_EXTRACTION.md       # Original architecture extraction
│   └── MIGRATION_IMPACT.md              # Migration analysis (fully applied)
│
├── MVP_V1_SPEC.md                       # ACTIVE — implementation specification
├── REPOSITORY_STRUCTURE.md              # ACTIVE — package design
├── POST_MVP_BACKLOG.md                  # ACTIVE — deferred items reference
├── DATA_MODEL.md                        # ACTIVE — (to be created)
├── ARCHITECTURE_REVIEW.md               # ACTIVE — this document
├── DOCS_CLEANUP_PLAN.md                 # ACTIVE — (to be created)
└── README_V2_DRAFT.md                   # ACTIVE — (to be created)
```

### Implementation Priority Order

Per `MVP_V1_SPEC.md` and `REPOSITORY_STRUCTURE.md`, the recommended implementation order:

1. **Models** — `src/models/` — All Pydantic schemas. Zero dependencies. Unblocks everything.
2. **Config** — `src/config.py` — Environment variable loading.
3. **Core** — `src/core/` — Logging, security, dedup, retry, clock. Depends on models.
4. **Storage** — `src/storage/` — Database setup, migrations, query functions. Depends on models + core.
5. **Ingestion** — `src/ingestion/` — Webhook verification, BLT poller, queue, gap detector. Depends on storage + core.
6. **Normalization** — `src/normalization/` — GitLab and BLT adapters. Depends on models + core.
7. **Identity** — `src/identity/` — Resolution pipeline with rapidfuzz. Depends on storage + models.
8. **State** — `src/state/` — Pipeline runner, reducer, room map. Depends on identity + normalization + storage + broadcast.
9. **Broadcast** — `src/broadcast/` — WebSocket hub, message builders, leaderboard. Depends on storage + models.
10. **API** — `src/api/` — FastAPI routes. Depends on everything (wiring layer).
11. **Main** — `src/main.py` — App factory, lifespan, route registration.

---

## Summary

| Metric | Count |
|--------|-------|
| Documents reviewed | 7 |
| Outdated references found in proposal-era docs | 56+ (17 in PROPOSAL_BREAKDOWN, 8 in FEATURE_INVENTORY, 22 in ARCHITECTURE_EXTRACTION, plus migration document) |
| Documents superseded | 4 (PROPOSAL_BREAKDOWN, FEATURE_INVENTORY, ARCHITECTURE_EXTRACTION, MIGRATION_IMPACT) |
| Documents to keep active | 3 (MVP_V1_SPEC, REPOSITORY_STRUCTURE, POST_MVP_BACKLOG) |
| Documents to archive | 4 (all proposal-era extractions + migration analysis) |
| Content gaps identified | 4 (data model, env var catalog, error taxonomy, API contract catalog — only data model needs a new doc, others already covered) |
| Implementation phases | 11 (models → config → core → storage → ingestion → normalization → identity → state → broadcast → api → main) |
