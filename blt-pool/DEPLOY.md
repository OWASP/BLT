# Deployment Guide — BLT-Pool

## Deploying to Cloudflare

```bash
npx wrangler deploy
```

`wrangler.toml` runs `scripts/run-migrations.sh` automatically during `wrangler deploy`.

## Why this matters

Schema is managed via Wrangler migrations, and deploy now applies migrations through Wrangler config before publishing worker code.

## Other useful commands

```bash
# Apply migrations only
bash scripts/run-migrations.sh

# Local migration apply
npx wrangler d1 migrations apply LEADERBOARD_DB --local

# List migration status
npx wrangler d1 migrations list LEADERBOARD_DB --remote

```
