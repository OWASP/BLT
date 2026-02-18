#!/bin/bash
# Script to setup remote D1 database for production
echo "Setting up remote D1 database..."

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "Wrangler CLI not found. Please install it first:"
    echo "   npm install -g wrangler"
    exit 1
fi

# Apply migrations to remote
echo "Applying migrations to remote database..."
wrangler d1 migrations apply blt-api --remote

# Verify setup
echo "Checking database tables..."
wrangler d1 execute blt-api --remote --command "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

echo ""
echo "Remote database setup complete!"