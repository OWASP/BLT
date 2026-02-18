#!/bin/bash
# Deployment script that runs D1 migrations before deploying to Cloudflare Workers
# Usage: ./deploy.sh [--env environment]

set -e  # Exit on error

echo "🚀 BLT-API Deployment Script"
echo "=============================="
echo ""

# Parse command line arguments
ENV_FLAG=""
if [ "$1" = "--env" ] && [ -n "$2" ]; then
    ENV_FLAG="--env $2"
    echo "📦 Environment: $2"
else
    echo "📦 Environment: default (production)"
fi

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Error: Wrangler CLI not found"
    echo "   Install it with: npm install -g wrangler"
    exit 1
fi

echo ""
echo "🗄️  Step 1: Applying D1 database migrations..."
echo "================================================"
wrangler d1 migrations apply blt-api --remote $ENV_FLAG

if [ $? -ne 0 ]; then
    echo "❌ Migration failed! Deployment aborted."
    exit 1
fi

echo ""
echo "✅ Migrations applied successfully!"
echo ""
echo "☁️  Step 2: Deploying to Cloudflare Workers..."
echo "================================================"
wrangler deploy $ENV_FLAG

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed!"
    exit 1
fi

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🎉 Your worker is now live!"
