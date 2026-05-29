# D1 migrations — NetGuardian (Week 1 Day 4)

## Layout

| Path | Purpose |
|------|---------|
| `schema.sql` | Legacy scanner tables (jobs, tasks, targets, vulnerabilities) |
| `migrations/ng/0001_core.sql` | GSoC ingest/triage tables (`sender_keys`, `envelopes`, `findings`, …) |

`wrangler.toml` sets `migrations_dir = "migrations/ng"` for `wrangler d1 migrations apply`.

## Local apply

```bash
# Legacy scanner schema (if not already applied)
wrangler d1 execute blt-netguardian --local --file=schema.sql

# NetGuardian core (single-file apply)
./scripts/d1-apply-ng-local.sh

# Or wrangler migrations tracking
wrangler d1 migrations apply blt-netguardian --local
```

## Remote (staging)

```bash
wrangler d1 migrations apply blt-netguardian --remote
```

Replace `blt-netguardian` with your D1 database name if different.

## CI

`tests/ng/test_d1_migration.py` applies `0001_core.sql` to in-memory SQLite and asserts tables + replay uniqueness.
