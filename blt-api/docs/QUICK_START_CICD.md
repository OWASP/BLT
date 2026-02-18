# Quick Start: Enable Automatic Deployments

This guide helps repository maintainers quickly enable automatic deployments with migrations.

## Prerequisites

- Repository admin access
- Cloudflare account with Workers and D1 enabled
- API token with appropriate permissions

## Setup Steps (5 minutes)

### Step 1: Create Cloudflare API Token

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Click on your profile → **API Tokens**
3. Click **Create Token**
4. Use **Edit Cloudflare Workers** template or create custom token with:
   - Workers Scripts: Edit
   - D1: Edit
5. Copy the token (you'll only see it once!)

### Step 2: Get Your Account ID

1. In Cloudflare Dashboard, go to **Workers & Pages**
2. Copy your **Account ID** from the right sidebar

### Step 3: Add Secrets to GitHub

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add two secrets:
   - **Name**: `CLOUDFLARE_API_TOKEN`
   - **Value**: [paste your API token]
   
   - **Name**: `CLOUDFLARE_ACCOUNT_ID`
   - **Value**: [paste your account ID]

### Step 4: Enable Workflow

The workflow is already configured in `.github/workflows/deploy.yml` and will run automatically when:
- Code is pushed to the `main` branch
- You manually trigger it from the Actions tab

### Step 5: Test the Workflow (Optional)

1. Go to **Actions** tab in GitHub
2. Select **Deploy to Cloudflare Workers**
3. Click **Run workflow** → **Run workflow**
4. Watch the deployment process

## What Happens on Deploy?

Every time code is pushed to `main`:

1. ✅ GitHub Actions checks out the code
2. ✅ Installs Wrangler CLI
3. ✅ **Applies D1 migrations** (`wrangler d1 migrations apply blt-api --remote`)
4. ✅ **Deploys the worker** (`wrangler deploy`)

## Troubleshooting

### "Authentication error"
- Verify your API token is correct and has the right permissions
- Ensure the token hasn't expired

### "Database not found"
- Check that the database ID in `wrangler.toml` matches your actual database
- Verify your account ID is correct

### Workflow fails
- Check the Actions tab for error logs
- Ensure both secrets are set correctly
- Verify the D1 database exists in your Cloudflare account

## Need More Help?

See the full documentation:
- [docs/DEPLOYMENT.md](./DEPLOYMENT.md) - Complete deployment guide
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development guidelines
- [README.md](../README.md) - Project overview

## Security Note

⚠️ Never commit API tokens to the repository!
✅ Always use GitHub Secrets for sensitive credentials
