# Deployment Guide

## Overview

This guide covers deploying BLT-Next to GitHub Pages for the frontend and Cloudflare Workers for the backend API.

## Prerequisites

- GitHub account with access to the repository
- Cloudflare account (free tier works)
- Git installed locally
- Node.js 18+ (for Wrangler CLI)
- Python 3.11+ (for local worker development)

## Part 1: Deploy Frontend to GitHub Pages

### Step 1: Enable GitHub Pages

1. Go to your repository on GitHub
2. Navigate to **Settings** > **Pages**
3. Under **Source**, select:
   - Source: **Deploy from a branch**
   - Branch: **main**
   - Folder: **/ (root)**
4. Click **Save**

### Step 2: Verify Workflow

The GitHub Actions workflow (`.github/workflows/pages.yml`) will automatically deploy your site.

1. Go to **Actions** tab in your repository
2. You should see a workflow run for "Deploy to GitHub Pages"
3. Wait for it to complete (usually 1-2 minutes)
4. Your site will be live at: `https://owasp-blt.github.io/BLT-Next/`

### Step 3: Custom Domain (Optional)

To use a custom domain:

1. Add a `CNAME` file in the repository root:
   ```
   blt.example.com
   ```

2. Configure DNS with your domain provider:
   ```
   CNAME record: blt.example.com → owasp-blt.github.io
   ```

3. In GitHub Pages settings, add your custom domain
4. Enable **Enforce HTTPS**

## Part 2: Deploy Backend to Cloudflare Workers

### Step 1: Install Wrangler CLI

```bash
npm install -g wrangler
```

Verify installation:
```bash
wrangler --version
```

### Step 2: Login to Cloudflare

```bash
wrangler login
```

This will open a browser window to authenticate with Cloudflare.

### Step 3: Create D1 Database (Optional)

If using Cloudflare D1 for database:

```bash
wrangler d1 create blt-database
```

Copy the database ID from the output and update `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "blt-database"
database_id = "your-database-id-here"
```

### Step 4: Set Secrets

Set environment secrets for the worker:

```bash
# JWT secret for authentication
wrangler secret put JWT_SECRET
# Enter a strong random string

# Database URL (if using external database)
wrangler secret put DATABASE_URL
# Enter your database connection string

# Encryption key
wrangler secret put ENCRYPTION_KEY
# Enter a strong random string
```

### Step 5: Configure Worker

Edit `wrangler.toml`:

1. Update `name` to your desired worker name
2. Update `route` with your custom domain (or remove for *.workers.dev)
3. Configure environment variables if needed

### Step 6: Deploy Worker

```bash
wrangler deploy
```

Your API will be deployed and you'll get a URL like:
```
https://blt-api.<YOUR_CLOUDFLARE_ACCOUNT>.workers.dev
```

Replace `<YOUR_CLOUDFLARE_ACCOUNT>` with your actual Cloudflare account subdomain.

### Step 7: Update Frontend Configuration

Update the API endpoint in `src/assets/js/main.js`:

```javascript
const CONFIG = {
    // Replace with your actual Worker URL
    API_BASE_URL: 'https://blt-api.<YOUR_CLOUDFLARE_ACCOUNT>.workers.dev',
    // Or your custom domain:
    // API_BASE_URL: 'https://api.<YOUR_DOMAIN>.com',
};
```

**IMPORTANT**: Make sure to replace the placeholder URLs with your actual endpoints before deploying to production.

Commit and push the changes:
```bash
git add src/assets/js/main.js
git commit -m "Update API endpoint"
git push
```

## Part 3: Configure CORS

### Update Allowed Origins

In `workers/main.py`, update `ALLOWED_ORIGINS`:

```python
ALLOWED_ORIGINS = [
    'https://owasp-blt.github.io',
    'https://yourdomain.com',  # Add your custom domain
    'http://localhost:8000',    # For local development
]
```

Redeploy the worker:
```bash
wrangler deploy
```

## Part 4: Database Setup

### Option A: Cloudflare D1

1. Create database (already done in Step 3)
2. Create schema:

```bash
wrangler d1 execute blt-database --file=schema.sql
```

Example `schema.sql`:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bugs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT,
    status TEXT,
    reporter_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_id) REFERENCES users(id)
);
```

### Option B: External Database

If using PostgreSQL, MySQL, or another database:

1. Set up your database
2. Create tables using migration scripts
3. Configure connection in worker secrets
4. Update worker code to use database client

## Part 5: Testing

### Test Frontend

1. Open your GitHub Pages URL
2. Navigate through pages
3. Test forms (will show errors until API is connected)
4. Check browser console for errors

### Test API

Test endpoints using curl:

```bash
# Test stats endpoint
curl https://blt-api.your-account.workers.dev/api/stats

# Test login
curl -X POST https://blt-api.your-account.workers.dev/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

## Part 6: Monitoring

### GitHub Pages

- Monitor deployment status in Actions tab
- Check Pages settings for build status

### Cloudflare Workers

1. Go to Cloudflare Dashboard
2. Navigate to **Workers & Pages**
3. Click on your worker
4. View metrics:
   - Requests
   - Errors
   - CPU time
   - Duration

### Set Up Alerts

In Cloudflare:
1. Go to **Notifications**
2. Create alerts for:
   - High error rate
   - Increased latency
   - Rate limit exceeded

## Part 7: Continuous Deployment

### Frontend (GitHub Pages)

Automatically deploys on push to `main` branch via GitHub Actions.

### Backend (Cloudflare Workers)

**Option 1: Manual Deployment**
```bash
wrangler deploy
```

**Option 2: GitHub Actions**

Create `.github/workflows/deploy-worker.yml`:

```yaml
name: Deploy Cloudflare Worker

on:
  push:
    branches: [main]
    paths:
      - 'workers/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          workingDirectory: 'workers'
```

Add `CLOUDFLARE_API_TOKEN` to repository secrets.

## Troubleshooting

### GitHub Pages Not Updating

1. Check Actions tab for workflow failures
2. Clear browser cache
3. Wait a few minutes (CDN cache)
4. Check Pages settings

### Worker Errors

1. Check worker logs:
   ```bash
   wrangler tail
   ```

2. Check Cloudflare Dashboard for errors
3. Verify secrets are set correctly
4. Test endpoints individually

### CORS Errors

1. Verify allowed origins in worker
2. Check browser console for specific error
3. Ensure proper headers are returned
4. Test with curl to isolate issue

### Database Connection Issues

1. Verify DATABASE_URL secret
2. Check database is accessible
3. Verify credentials
4. Check firewall rules (if external DB)

## Production Checklist

- [ ] GitHub Pages deployed successfully
- [ ] Custom domain configured (if applicable)
- [ ] HTTPS enabled
- [ ] Worker deployed to production
- [ ] Secrets configured
- [ ] Database set up and migrated
- [ ] CORS configured correctly
- [ ] API endpoints tested
- [ ] Error monitoring set up
- [ ] Rate limiting configured
- [ ] Backup strategy in place
- [ ] Documentation updated

## Performance Optimization

### Frontend

1. **Enable caching headers** in `_config.yml`
2. **Compress images** before committing
3. **Use CDN for large assets**
4. **Minimize CSS/JS** (optional, but recommended for production)

### Backend

1. **Enable KV caching** for frequently accessed data
2. **Optimize database queries**
3. **Use connection pooling** for external databases
4. **Monitor and optimize slow endpoints**

## Cost Estimates

### GitHub Pages
- **Free** for public repositories

### Cloudflare Workers
- **Free tier**: 100,000 requests/day
- **Paid**: $5/month for 10 million requests
- **D1**: Free up to 5 GB

**Total estimated cost**: $0-10/month depending on traffic

## Security Considerations

1. **Always use HTTPS**
2. **Set strong JWT_SECRET**
3. **Rotate secrets regularly**
4. **Enable rate limiting**
5. **Monitor for suspicious activity**
6. **Keep dependencies updated**
7. **Use Content Security Policy**

## Support

- **Issues**: [GitHub Issues](https://github.com/OWASP-BLT/BLT-Next/issues)
- **Community**: OWASP BLT Slack
- **Docs**: [Project Documentation](../README.md)

## Next Steps

After successful deployment:

1. Test all features thoroughly
2. Set up monitoring and alerts
3. Configure backup strategy
4. Document any custom configurations
5. Train team on deployment process
