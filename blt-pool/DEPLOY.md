# Deployment Guide — BLT-Pool

## Deploying to Cloudflare

```bash
bash scripts/check_no_runtime_ddl.sh
bash scripts/run-migrations.sh
npx wrangler deploy
```

## Why this order matters

Schema is now managed via Wrangler migrations. Apply migrations first, then deploy worker code.

## Other useful commands

```bash
# Apply migrations only
bash scripts/run-migrations.sh

# Local migration apply
npx wrangler d1 migrations apply LEADERBOARD_DB --local

# List migration status
npx wrangler d1 migrations list LEADERBOARD_DB --remote

# Check for runtime DDL
bash scripts/check_no_runtime_ddl.sh
```
