# Documentation Cleanup Plan — BLT-Hackerhouse

*Produced 2026-06-12. Based on ARCHITECTURE_REVIEW.md findings.*

---

## Current State

`docs/` contains 10 files: 8 markdown documents, 1 PDF (original proposal), 1 newly created DATA_MODEL.md.

---

## Categorization

### KEEP — Active Implementation References

These documents are accurate, up-to-date, and needed during implementation.

| # | Document | Role | Why Keep |
|---|----------|------|----------|
| 1 | **MVP_V1_SPEC.md** | Primary implementation specification | Contains all 20 VF features with contracts, data models, and API specs. The single source of truth for "what to build." |
| 2 | **REPOSITORY_STRUCTURE.md** | Package design and dependency rules | Module-to-feature mapping, import rules, test tree structure. Needed daily during implementation. |
| 3 | **POST_MVP_BACKLOG.md** | Deferred items reference | Consolidated list of all removed/deferred items. Prevents re-implementing things that were intentionally excluded. |
| 4 | **DATA_MODEL.md** | Complete database schema design | Column-level schema with types, constraints, indexes, and rationale. Directly informs migration SQL. |
| 5 | **ARCHITECTURE_REVIEW.md** | Review findings and recommendations | Records the transition from planning to implementation. Useful context for anyone joining mid-implementation. |
| 6 | **DOCS_CLEANUP_PLAN.md** | This document | Documents which files are active vs archived and why. |

### ARCHIVE — Historical Planning Artifacts

These documents served their purpose during planning but are now superseded. They contain outdated assumptions (GitHub, Slack, mentorship) that could confuse someone starting implementation from them.

Move to `docs/archive/`. Keep for historical reference — they document the original proposal scope and the reasoning behind scope changes.

| # | Document | Superseded By | Why Archive |
|---|----------|---------------|-------------|
| 1 | **PROPOSAL_BREAKDOWN.md** | MVP_V1_SPEC.md | 17 outdated references (GitHub, Slack, mentorship). Original requirements extraction — preserved as historical record of GSoC proposal scope. |
| 2 | **FEATURE_INVENTORY.md** | MVP_V1_SPEC.md + POST_MVP_BACKLOG.md | Obsolete F01–F36 numbering. Original feature catalog. Preserved as record of what the proposal committed to before scope changes. |
| 3 | **ARCHITECTURE_EXTRACTION.md** | MVP_V1_SPEC.md + REPOSITORY_STRUCTURE.md | 22 outdated references. Original architecture diagram. Preserved to show design evolution from proposal to final MVP spec. |
| 4 | **MIGRATION_IMPACT.md** | ARCHITECTURE_REVIEW.md | All 22 findings applied. Valuable as a record of WHY GitHub→GitLab, mentorship removal, and Slack deferral happened. |
| 5 | **Rudra_pratap_singh_🥪BLT-Hackerhouse_Proposal.pdf** | All spec docs | Original GSoC proposal PDF. Primary source material. Should be preserved for reference but is not an implementation document. |

### DELETE — None

All documents have historical or referential value. No document is outright wrong or useless. The archive preserves the full design lineage: proposal → extractions → migration analysis → corrected MVP spec → repository design → data model.

---

## Proposed Archive Structure

```
docs/
├── README.md                            # (to be refreshed from README_V2_DRAFT.md)
│
├── MVP_V1_SPEC.md                       # KEEP — implementation specification
├── REPOSITORY_STRUCTURE.md              # KEEP — package design
├── POST_MVP_BACKLOG.md                  # KEEP — deferred items
├── DATA_MODEL.md                        # KEEP — database schema
├── ARCHITECTURE_REVIEW.md               # KEEP — review findings
├── DOCS_CLEANUP_PLAN.md                 # KEEP — this document
│
├── archive/                             # Historical planning artifacts
│   ├── README.md                        # Explain what's in archive/ and why
│   ├── PROPOSAL_BREAKDOWN.md
│   ├── FEATURE_INVENTORY.md
│   ├── ARCHITECTURE_EXTRACTION.md
│   ├── MIGRATION_IMPACT.md
│   └── Rudra_pratap_singh_🥪BLT-Hackerhouse_Proposal.pdf
│
└── README_V2_DRAFT.md                   # TEMPORARY — draft for README.md refresh
```

---

## archive/README.md (Recommended Content)

```markdown
# Archived Planning Documents

These documents were created during the planning phase of BLT-Hackerhouse.
They are preserved for historical reference but are **superseded** by the
active documents in the parent directory.

## Why These Are Archived

The original GSoC proposal assumed:
- **GitHub** as the primary SCM (BLT has since migrated to **GitLab**)
- **Slack** as a required integration (now **deferred** — requirements unvalidated)
- **Mentorship tracking** as an MVP feature (now **out of scope**)

The active implementation documents reflect the corrected scope:
- `MVP_V1_SPEC.md` — 20 GitLab-based backend features
- `REPOSITORY_STRUCTURE.md` — Package design and dependency rules
- `DATA_MODEL.md` — Complete database schema
- `POST_MVP_BACKLOG.md` — All deferred/removed items

## Document Lineage

1. `Proposal.pdf` → `PROPOSAL_BREAKDOWN.md` + `FEATURE_INVENTORY.md` + `ARCHITECTURE_EXTRACTION.md`
2. Context change (GitLab migration) → `MIGRATION_IMPACT.md`
3. Applied all changes → `MVP_V1_SPEC.md` + `REPOSITORY_STRUCTURE.md` + `POST_MVP_BACKLOG.md`
4. Pre-implementation review → `ARCHITECTURE_REVIEW.md` + `DATA_MODEL.md`

Do not use archived documents for implementation decisions.
Refer to the active documents in `docs/` instead.
```

---

## Recommended .gitignore

The repository currently has no `.gitignore`. Create one at the repository root with:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
env/

# SQLite
*.db
*.sqlite
*.sqlite3

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local
.env.*.local

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
load_test_results/

# Docker (if added post-MVP)
# docker-compose.override.yml

# Archive PDFs (the proposal PDF is in docs/archive/, git can track it if small enough)
# If the PDF is >10MB, add: docs/archive/*.pdf
```

The proposal PDF is ~12 MB. If that's too large for the repository, add `docs/archive/*.pdf` to `.gitignore` and store the PDF externally. Otherwise, Git can handle it.

---

## Action Items

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 1 | Create `docs/archive/` directory | High | 1 min |
| 2 | Move 5 files to `docs/archive/` | High | 1 min |
| 3 | Create `docs/archive/README.md` | Medium | 5 min |
| 4 | Create `.gitignore` at repo root | High | 2 min |
| 5 | Delete `docs/DOCS_CLEANUP_PLAN.md` after actions complete | Low | 1 min (this doc is self-referencing — remove once executed) |
