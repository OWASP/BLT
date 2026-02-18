#!/bin/bash
# Script to setup local D1 database for development
echo "Setting up local D1 database..."

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "Wrangler CLI not found. Please install it first:"
    echo "   npm install -g wrangler"
    exit 1
fi

# Create local D1 database
echo "Creating local D1 database..."
wrangler d1 create blt-api --local

# Apply migrations
echo "Applying migrations..."
wrangler d1 migrations apply blt-api --local

# Check if migrations were applied
echo "Checking database tables..."
wrangler d1 execute blt-api --local --command "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

echo ""
echo "Database setup complete!"
echo ""
echo "To insert test data, run:"
echo "  wrangler d1 execute blt-api --local --file=test_data.sql"
echo ""
echo "To start the dev server:"
echo "  wrangler dev"
