#!/bin/bash
# Pre-deployment script that applies D1 migrations
# This script is called by wrangler during the build process

set -e

echo "🗄️  Applying D1 database migrations..."

# Database name from wrangler.toml
DATABASE_NAME="${DATABASE_NAME:-blt-api}"

# Apply migrations to the remote database
wrangler d1 migrations apply "$DATABASE_NAME" --remote

echo "✅ Migrations applied successfully!"
