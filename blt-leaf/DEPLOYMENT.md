# Deployment Guide

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
database_name = "pr-tracker"
database_id = "YOUR_DATABASE_ID_HERE"
```

4. **Initialize Database Schema**
```bash
wrangler d1 execute pr-tracker --file=./schema.sql
```

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
