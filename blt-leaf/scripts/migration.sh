#!/bin/bash
# Pre-deployment script that applies D1 migrations
# This script is called by wrangler during the build process

set -e

echo "Applying D1 database migrations..."
# Database name from wrangler.toml
DATABASE_NAME="${DATABASE_NAME:-pr_tracker}"

# In non-interactive/CI environments without a Cloudflare API token, apply
# migrations locally (in-process D1) so that `wrangler dev` can still start.
if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    echo "No CLOUDFLARE_API_TOKEN found – applying migrations locally (dev/test mode)."
    if wrangler d1 migrations apply "$DATABASE_NAME" --local; then
        echo "Local migrations applied successfully."
    else
        echo "Warning: Local migration step failed (this is acceptable when no local DB exists yet)."
    fi
    echo "Skipping remote migrations – not authenticated."
    exit 0
fi

# Apply migrations to the remote database
if ! wrangler d1 migrations apply "$DATABASE_NAME" --remote; then
    echo "Error: Failed to apply migrations to database '$DATABASE_NAME'"
    echo "   Make sure the database exists and wrangler is properly authenticated"
    exit 1
fi

echo "Migrations applied successfully!"
