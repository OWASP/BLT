#!/bin/bash
# Pre-deployment script that applies D1 migrations
# This script is called by wrangler during the build process

set -e

echo "Applying D1 database migrations..."
# Database name from wrangler.toml
DATABASE_NAME="${DATABASE_NAME:-pr_tracker}"

# Apply migrations to the remote database
if ! wrangler d1 migrations apply "$DATABASE_NAME" --remote; then
    echo "Error: Failed to apply migrations to database '$DATABASE_NAME'"
    echo "   Make sure the database exists and wrangler is properly authenticated"
    exit 1
fi

echo "Migrations applied successfully!"
