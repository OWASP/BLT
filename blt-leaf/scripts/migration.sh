#!/bin/bash
# Pre-deployment script that applies D1 migrations
# This script is called by wrangler during the build process

set -e

echo "Applying D1 database migrations..."
# Database name from wrangler.toml
DATABASE_NAME="${DATABASE_NAME:-pr_tracker}"
# Migration target: "remote" (default) or "local"
MIGRATION_TARGET="${MIGRATION_TARGET:-remote}"

if [ "$MIGRATION_TARGET" != "remote" ] && [ "$MIGRATION_TARGET" != "local" ]; then
    echo "Error: MIGRATION_TARGET must be 'remote' or 'local', got '$MIGRATION_TARGET'"
    exit 1
fi

# Support legacy WRANGLER_API_TOKEN for backwards compatibility.
if [ -z "$CLOUDFLARE_API_TOKEN" ] && [ -n "$WRANGLER_API_TOKEN" ]; then
    export CLOUDFLARE_API_TOKEN="$WRANGLER_API_TOKEN"
fi

# In non-interactive/CI or dev environments without Cloudflare authentication,
# apply migrations locally (in-process D1) so that `wrangler dev` can still start.
# Remote migrations are attempted when:
#   - CLOUDFLARE_API_TOKEN is set, OR
#   - APPLY_REMOTE_MIGRATIONS=true is explicitly set.
if [ -z "$CLOUDFLARE_API_TOKEN" ] && [ "${APPLY_REMOTE_MIGRATIONS}" != "true" ]; then
    # No API token and no explicit opt-in: apply migrations locally.
    echo "No CLOUDFLARE_API_TOKEN set – applying migrations locally (dev/test mode)."
    if wrangler d1 migrations apply "$DATABASE_NAME" --local; then
        echo "Local migrations applied successfully."
    else
        if [ -d ".wrangler/state" ]; then
            echo "Warning: Local migration step failed and a local DB state exists (.wrangler/state). This may indicate a real migration issue – please review your SQL migrations."
        else
            echo "Warning: Local migration step failed. No local DB state found (.wrangler/state absent), so this is expected in a fresh environment."
        fi
    fi
    exit 0
fi

# Apply migrations to the target database (remote or local)
if ! wrangler d1 migrations apply "$DATABASE_NAME" --$MIGRATION_TARGET; then
    echo "Error: Failed to apply migrations to database '$DATABASE_NAME'"
    echo "   Make sure the database exists and wrangler is properly authenticated"
    exit 1
fi

echo "Migrations applied successfully!"
