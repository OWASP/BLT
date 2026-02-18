# Continuous Deployment Setup

This document describes the automated deployment process for BLT-API to Cloudflare Workers.

## Overview

The BLT-API uses GitHub Actions to automatically deploy to Cloudflare Workers whenever changes are pushed to the `main` branch. The deployment process includes:

1. **Automatic Database Migrations**: D1 migrations are applied automatically before deployment
2. **Worker Deployment**: The worker code is deployed to Cloudflare's global network

## Workflow

The deployment workflow (`.github/workflows/deploy.yml`) runs on:
- Every push to the `main` branch
- Manual trigger via workflow dispatch

### Deployment Steps

1. Checkout the code
2. Setup Node.js environment
3. Install Wrangler CLI
4. **Apply D1 database migrations** (`wrangler d1 migrations apply blt-api --remote`)
5. Deploy the worker (`wrangler deploy`)

## Required Secrets

To enable automated deployments, the following secrets must be configured in your GitHub repository:

### `CLOUDFLARE_API_TOKEN`

An API token with permissions to deploy Workers and manage D1 databases.

**How to create:**
1. Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Go to **My Profile** → **API Tokens**
3. Click **Create Token**
4. Use the **Edit Cloudflare Workers** template or create a custom token with these permissions:
   - Account: **Workers Scripts:Edit**
   - Account: **D1:Edit**
   - Account: **Workers Routes:Edit** (if using routes)
5. Copy the generated token

### `CLOUDFLARE_ACCOUNT_ID`

Your Cloudflare account ID.

**How to find:**
1. Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select any website or go to **Workers & Pages**
3. The Account ID is displayed on the right sidebar
4. Copy the Account ID

### Adding Secrets to GitHub

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add both secrets:
   - Name: `CLOUDFLARE_API_TOKEN`, Value: Your API token
   - Name: `CLOUDFLARE_ACCOUNT_ID`, Value: Your account ID

## Manual Deployment

If you need to deploy manually:

```bash
# Login to Cloudflare
wrangler login

# Apply migrations
wrangler d1 migrations apply blt-api --remote

# Deploy
wrangler deploy
```

## Environment-Specific Deployment

The workflow deploys to the default (production) environment. To deploy to specific environments:

```bash
# Development
wrangler d1 migrations apply blt-api --remote --env development
wrangler deploy --env development

# Production (explicit)
wrangler d1 migrations apply blt-api --remote --env production
wrangler deploy --env production
```

## Database Migrations

### Migration Files

Migrations are stored in the `migrations/` directory as SQL files:
- `0001_init.sql` - Initial schema
- `0002_add_bugs.sql` - Bugs table and related tables
- Future migrations will be numbered sequentially

### Creating New Migrations

```bash
# Create a new migration
wrangler d1 migrations create blt-api <description>

# Edit the generated .sql file in migrations/

# Test locally first
wrangler d1 migrations apply blt-api --local

# Commit the migration file
git add migrations/
git commit -m "Add migration: <description>"
git push
```

When you push to `main`, the GitHub Action will automatically apply the new migration to production before deploying.

### Migration Safety

- Migrations are applied in order and tracked in the `d1_migrations` table
- Each migration runs only once
- Failed migrations will prevent deployment
- Always test migrations locally before pushing to production

## Monitoring Deployments

### GitHub Actions

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. View the latest workflow runs
4. Check logs for any errors

### Cloudflare Dashboard

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Navigate to **Workers & Pages**
3. Select your worker (`blt-api`)
4. View deployment history and logs

## Troubleshooting

### Migration Failures

If migrations fail during deployment:

1. Check the GitHub Actions logs for specific error messages
2. Test the migration locally:
   ```bash
   wrangler d1 migrations apply blt-api --local
   ```
3. Fix the migration SQL file
4. Push the fix

### Deployment Failures

If the worker deployment fails:

1. Verify your Cloudflare API token has the correct permissions
2. Check that the account ID is correct
3. Ensure the D1 database exists and is properly configured in `wrangler.toml`
4. Review the GitHub Actions logs for specific errors

### Rollback

If you need to rollback a deployment:

1. Revert the problematic commits
2. Push to `main` to trigger a new deployment
3. For database changes, you may need to create a new migration that reverts the changes

**Note**: D1 migrations cannot be automatically rolled back. Plan migrations carefully and test thoroughly before deploying.

## Security Best Practices

1. **Never commit API tokens** to the repository
2. **Rotate API tokens regularly** (every 90 days recommended)
3. **Use minimal permissions** for API tokens
4. **Review workflow logs** to ensure no secrets are exposed
5. **Limit branch protection** - only allow deployments from `main`

## Local Development

The CI/CD setup doesn't affect local development:

```bash
# Local database
wrangler d1 migrations apply blt-api --local
wrangler d1 execute blt-api --local --file=test_data.sql

# Local server
wrangler dev --port 8787
```

## Additional Resources

- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [Wrangler CLI Documentation](https://developers.cloudflare.com/workers/wrangler/)
- [D1 Database Documentation](https://developers.cloudflare.com/d1/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
