# Week 1 progress log

**Repo:** [Pritz395/BLT-NetGuardian](https://github.com/Pritz395/BLT-NetGuardian)

| Day | Proposal focus | Status | PR / branch |
|-----|----------------|--------|-------------|
| 1 | `ztr-finding-1` fields + error enums | Done | #1 `gsoc/week1-spec-d1` |
| 2 | JCS + signing base string | Done | #1 |
| 3 | D1 tables + constraints | Done | #1 |
| 4 | D1 migrations + CI skeleton | Done | `gsoc/week1-day4-5` |
| 5 | Canonicalization + digest helpers + tests | Done | `gsoc/week1-day4-5` |
| 6 | Property tests | Pending | — |
| 7 | Polish + mentor review | Pending | — |

## Day 4–5 artifacts

- `wrangler.toml` — `migrations_dir = "migrations/ng"`
- [d1-migrations.md](../d1-migrations.md), [scripts/d1-apply-ng-local.sh](../../scripts/d1-apply-ng-local.sh)
- `tests/ng/test_d1_migration.py` — SQLite apply + replay uniqueness
- `src/ng/envelope.py` — validate, sign, verify, clock skew, body digest
- `tests/ng/test_envelope.py`
- `GET /api/ng/health` — ingest scaffold liveness (no D1 write)

## Mentor paste (Days 4–5)

> Week 1 Days 4–5: Wired D1 migration dir in Wrangler, documented apply path, CI applies `0001_core.sql` on SQLite in tests. Added envelope validation/signing helpers with unit tests. Exposed `GET /api/ng/health` as scaffolding only — `/api/ng/ingest` remains Week 2.
