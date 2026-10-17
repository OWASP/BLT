#!/bin/bash
# Script to setup local D1 database for development
set -e

echo "Setting up local D1 database for development..."
echo ""

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "Wrangler CLI not found. Please install it first:"
    echo "   npm install -g wrangler"
    exit 1
fi

DATABASE_NAME="blt-api"

# Apply migrations to local database
echo "Applying migrations to local database..."
if wrangler d1 migrations apply "$DATABASE_NAME" --local; then
    echo "Migrations applied successfully!"
else
    echo "Note:: If migrations were already applied, this is expected."
fi

echo ""
echo "Checking database tables..."
wrangler d1 execute "$DATABASE_NAME" --local --command "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

echo ""
echo "Database setup complete!"
echo ""
echo "Next steps:"
echo "  1. Load test data:"
echo "     wrangler d1 execute $DATABASE_NAME --local --file=test_data.sql"
echo ""
echo "  2. Start the dev server:"
echo "     wrangler dev --port 8787"
echo ""
echo "  3. Test the API:"
echo "     curl http://localhost:8787"
echo ""
