# Deployment Guide — BLT-Pool

## Deploying to Cloudflare

```bash
npx wrangler deploy
```

Apply pending D1 migrations first with `bash scripts/run-migrations.sh` (it is not run by `wrangler deploy`).

## Why this matters

Schema is managed via Wrangler migrations in `migrations/`. The worker no longer creates tables at runtime, so apply new migrations before deploying code that needs them.

## Other useful commands

```bash
# Apply migrations only
bash scripts/run-migrations.sh

# Local migration apply
npx wrangler d1 migrations apply LEADERBOARD_DB --local

# List migration status
npx wrangler d1 migrations list LEADERBOARD_DB --remote

```
