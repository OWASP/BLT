# Deployment Guide

## Overview

This guide covers deploying BLT-Next as a single Cloudflare Worker that serves both static assets and backend API routes.

## Prerequisites

- Cloudflare account
- Git installed locally
- Node.js 18+
- Python 3.11+ for local worker syntax checks

## Part 1: Install Dependencies

Install project dependencies:

```bash
npm install
```

Install or use Wrangler through the project dependency:

```bash
npx wrangler --version
```

## Part 2: Login to Cloudflare

```bash
npx wrangler login
```

This opens a browser window to authenticate with Cloudflare.

## Part 3: Set Secrets

Set environment secrets for the worker:

```bash
npx wrangler secret put JWT_SECRET
npx wrangler secret put ENCRYPTION_KEY
```

Use strong production values for both secrets.

## Part 4: Configure Worker

Edit `wrangler.toml`:

1. Update `name` to your desired worker name.
2. Add a route or custom domain if you do not want to use the default `workers.dev` URL.
3. Configure environment variables under `[vars]` as needed.

The `[assets]` section serves files from `src` through the same Worker:

```toml
[assets]
directory = "src"
binding = "ASSETS"
```

## Part 5: Configure CORS

In `workers/main.py`, update `ALLOWED_ORIGINS`:

```python
ALLOWED_ORIGINS = [
    'https://blt.example.com',
    'http://localhost:8000',
]
```

Use the deployed Worker domain or your production custom domain.

## Part 6: Deploy

```bash
npm run worker:deploy
```

Your app and API will be available from the Worker URL, for example:

```text
https://blt-next.<YOUR_CLOUDFLARE_ACCOUNT>.workers.dev
```

## Part 7: Test

Test the frontend by opening the Worker URL in a browser.

Test API endpoints with curl:

```bash
curl https://blt-next.your-account.workers.dev/api/stats

curl -X POST https://blt-next.your-account.workers.dev/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

## Monitoring

In Cloudflare:

1. Go to **Workers & Pages**.
2. Open your Worker.
3. Review requests, errors, CPU time, and duration.
4. Use `npx wrangler tail` for live logs.

## Continuous Deployment

Deploy manually with:

```bash
npm run worker:deploy
```

For automated deployment, add a workflow that runs `npm ci` and `npx wrangler deploy` with `CLOUDFLARE_API_TOKEN` stored as a repository secret.

## Troubleshooting

### Worker Errors

1. Check worker logs with `npx wrangler tail`.
2. Check the Cloudflare dashboard for exception details.
3. Verify secrets and environment variables.
4. Test endpoints individually.

### CORS Errors

1. Verify allowed origins in `workers/main.py`.
2. Check the browser console for the failing origin.
3. Confirm the response includes the expected CORS headers.
4. Test with curl to isolate frontend issues.

## Production Checklist

- [ ] Worker deployed to production
- [ ] Custom domain configured, if applicable
- [ ] HTTPS enabled
- [ ] Secrets configured
- [ ] CORS configured correctly
- [ ] API endpoints tested
- [ ] Error monitoring set up
- [ ] Rate limiting configured
- [ ] Documentation updated

## Performance Optimization

1. Compress images before committing.
2. Use Workers Assets for static files.
3. Enable KV caching for stable upstream API responses.
4. Monitor and optimize slow endpoints.

## Cost Estimates

Cloudflare Workers:

- Free tier: 100,000 requests/day
- Paid: $5/month for 10 million requests

Total estimated cost: $0-10/month depending on traffic.
