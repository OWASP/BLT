#!/bin/bash

# BLT-Leaf Local Development Setup Script
echo "🍃 BLT-Leaf Local Setup"
echo "========================"

# Check wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler not found. Install it with: npm install -g wrangler"
    exit 1
fi

# Login check
echo ""
echo "📋 Step 1: Checking Cloudflare login..."
wrangler whoami 2>/dev/null || wrangler login

# Create or get existing D1 database
echo ""
echo "📋 Step 2: Setting up D1 database..."
DB_OUTPUT=$(wrangler d1 create pr-tracker 2>&1)

if echo "$DB_OUTPUT" | grep -q "already exists"; then
    echo "ℹ️  Database already exists, fetching ID..."
    DB_ID=$(wrangler d1 list 2>/dev/null | grep "pr-tracker" | awk -F'│' '{gsub(/ /,"",$2); print $2}')
else
    DB_ID=$(echo "$DB_OUTPUT" | grep "database_id" | awk -F'"' '{print $2}')
fi

if [ -n "$DB_ID" ]; then
    echo "✅ Database ID found: $DB_ID"
    echo ""
    echo "📋 Step 3: Updating wrangler.toml with database_id..."
    sed -i "s/database_id = \".*\"/database_id = \"$DB_ID\"/" wrangler.toml
    echo "✅ wrangler.toml updated"
else
    echo "❌ Could not find database ID. Please run 'wrangler d1 list' manually."
    exit 1
fi

# Apply schema locally
echo ""
echo "📋 Step 4: Applying database schema locally..."
wrangler d1 execute DB --local --file=./schema.sql  # <-- Changed this line
echo "✅ Schema applied successfully"

# Setup .env file
echo ""
echo "📋 Step 5: Setting up .env file..."
if [ ! -f .env ]; then
    cp env.example .env
    echo "✅ Created .env file from env.example"
    echo "💡 Optional: Add your GITHUB_TOKEN to .env to increase API rate limit from 60 to 5,000/hour"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Setup complete!"
echo "👉 Run 'wrangler dev' to start the local development server"
echo "🌐 Open http://localhost:8787 in your browser"
