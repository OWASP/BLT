# Deployment Guide

## One-Click Deployment (Recommended)

The easiest way to deploy BLT-Leaf is using the Deploy to Cloudflare button:

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/OWASP-BLT/BLT-Leaf)

**What happens when you click the button:**
1. You'll be prompted to log in to Cloudflare (or create a free account)
2. Cloudflare will fork this repository to your GitHub account
3. A new D1 database will be automatically provisioned
4. The database schema will be initialized on the first request
5. Your application will be deployed and ready to use

**No manual configuration required!** The database is automatically set up and the application is ready to track PRs.

---

## Manual Deployment

If you prefer manual deployment or need more control, follow these steps:

## Quick Start

1. **Install Wrangler**
```bash
npm install -g wrangler
# or
npm install
```

2. **Login to Cloudflare**
```bash
wrangler login
```

3. **Create Database**
```bash
wrangler d1 create pr-tracker
```

Copy the database ID from the output and update `wrangler.toml`:
```toml
[[d1_databases]]
binding = "DB"
database_name = "pr_tracker"
database_id = "YOUR_DATABASE_ID_HERE"  # Replace with your actual database ID
```

**Note:** The repository includes a placeholder database_id. If you're deploying via the Deploy to Cloudflare button, the database_id is automatically replaced during deployment. For manual deployment, replace the placeholder with your actual database ID from the previous step.

4. **Initialize Database Schema**

The database schema is automatically initialized when you first access the application. However, if you prefer to initialize it manually, you can run:

```bash
wrangler d1 execute pr-tracker --file=./schema.sql
```

**Note:** If you're deploying via the Deploy to Cloudflare button, schema initialization happens automatically on first use.

5. **Test Locally**
```bash
wrangler dev
```

6. **Deploy to Production**
```bash
wrangler deploy
```

## Testing the Application

Once deployed, you can test the application by:

1. Opening the deployed URL in your browser
2. Entering a GitHub PR URL (e.g., `https://github.com/facebook/react/pull/12345`)
3. Viewing the PR details including:
   - State (Open/Closed/Merged)
   - Merge status
   - Files changed
   - Check results
   - Review status
   - Author information

## GitHub API Considerations

- The application uses GitHub's REST API v3
- Unauthenticated requests have a rate limit of 60 requests/hour
- For higher limits, add a GitHub token as an environment variable:

```bash
wrangler secret put GITHUB_TOKEN
```

Then update the Python code to use the token in API requests.

## Database Maintenance

View data in your database:
```bash
wrangler d1 execute pr-tracker --command "SELECT * FROM prs"
```

Clear all data:
```bash
wrangler d1 execute pr-tracker --command "DELETE FROM prs"
```

## Troubleshooting

### Issue: Database not found
Solution: Make sure you've created the database and updated the database_id in wrangler.toml

### Issue: API rate limit exceeded
Solution: Add a GitHub personal access token to increase the rate limit

### Issue: PR data not loading
Solution: Check browser console for errors and verify the PR URL format is correct
