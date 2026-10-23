# BLT Timer Web Setup Guide

This guide starts BLT Timer Web with a local Cloudflare Worker and D1 database.

## Prerequisites

- Python 3.11 or newer.
- Node.js with `npx`.
- Wrangler 3 or newer.
- A Cloudflare account for production deployment.

## Local development

Run the automated checks before starting the Worker.

```bash
python -m unittest discover tests -v
python -m py_compile src/auth.py src/worker.py
```

Create a local environment file.

```bash
cp .env.example .dev.vars
python -c "import secrets; print('SESSION_SECRET=' + secrets.token_urlsafe(48))"
```

Copy the generated `SESSION_SECRET` line into `.dev.vars`.

Apply the clean baseline migration and start the Worker.

```bash
./migrate.sh dev
npx wrangler dev
```

Open `http://localhost:8787/login` and create an account.

The timer and saved work logs are now ready for local testing.

## Isolated local D1 validation

Use a temporary directory when you need a fresh local D1 database without touching Wrangler's default local state.

```bash
export BLT_D1_PERSIST_TO="$(mktemp -d /tmp/blt-timer-d1.XXXXXX)"
./migrate.sh dev
npx wrangler dev --local --persist-to "$BLT_D1_PERSIST_TO"
```

The fresh local database receives only `migrations/0001_initial.sql`.

## Production deployment

Log in to Cloudflare and create a new empty D1 database for BLT Timer Web.

```bash
npx wrangler login
npx wrangler d1 create blt-timer-web
```

Copy the returned database name and ID into the `DB` binding in `wrangler.toml`.

Set the session secret, then apply the baseline migration and deploy with the production script.

```bash
npx wrangler secret put SESSION_SECRET --env production
./deploy.sh
```

## Verification

After deployment, open the deployed `/login` page and create a test account.

Confirm that a saved work log appears in history and that both export formats download successfully.

Use `GET /health` to confirm that the Worker is reachable.
