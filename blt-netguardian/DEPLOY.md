# Deployment Guide for BLT-NetGuardian

## Architecture Overview

BLT-NetGuardian uses a split architecture:
- **Frontend**: Static HTML/CSS/JS hosted on GitHub Pages
- **Backend**: Python worker running on Cloudflare Workers

## Frontend Deployment (GitHub Pages)

### 1. Enable GitHub Pages

1. Go to your repository settings on GitHub
2. Navigate to "Pages" in the left sidebar
3. Under "Source", select "Deploy from a branch"
4. Choose the branch (e.g., `main`) and root folder (`/`)
5. Click "Save"

### 2. Your Site Will Be Available At

```
https://owasp-blt.github.io/BLT-NetGuardian/
```

The frontend includes:
- `index.html` - Main scan submission interface
- `dashboard.html` - Job monitoring dashboard
- `vulnerabilities.html` - Vulnerability database viewer
- `assets/` - CSS and JavaScript files

### 3. Configure API Endpoint

Edit `assets/js/config.js` and update the `API_BASE_URL` to point to your deployed Cloudflare Worker:

```javascript
const CONFIG = {
    API_BASE_URL: 'https://blt-netguardian.your-subdomain.workers.dev',
    // ...
};
```

## Backend Deployment (Cloudflare Workers)

### Prerequisites

- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) installed
- Cloudflare account

### 1. Install Wrangler

```bash
npm install -g wrangler
```

### 2. Login to Cloudflare

```bash
wrangler login
```

### 3. Create KV Namespaces

```bash
# Production namespaces
wrangler kv:namespace create "JOB_STATE"
wrangler kv:namespace create "TASK_QUEUE"
wrangler kv:namespace create "VULN_DB"
wrangler kv:namespace create "TARGET_REGISTRY"

# Preview namespaces (for testing)
wrangler kv:namespace create "JOB_STATE" --preview
wrangler kv:namespace create "TASK_QUEUE" --preview
wrangler kv:namespace create "VULN_DB" --preview
wrangler kv:namespace create "TARGET_REGISTRY" --preview
```

### 4. Update wrangler.toml

Update the `id` and `preview_id` fields in `wrangler.toml` with the IDs from step 3:

```toml
[[kv_namespaces]]
binding = "JOB_STATE"
id = "your-namespace-id-here"
preview_id = "your-preview-id-here"
```

### 5. Deploy to Cloudflare

```bash
wrangler publish
```

Your API will be available at:
```
https://blt-netguardian.your-subdomain.workers.dev
```

### 6. Test the API

```bash
curl https://blt-netguardian.your-subdomain.workers.dev/
```

Should return:
```json
{
  "name": "BLT-NetGuardian API",
  "version": "1.0.0",
  "status": "operational",
  "message": "Backend API for BLT-NetGuardian security pipeline",
  "frontend": "https://owasp-blt.github.io/BLT-NetGuardian/"
}
```

## Local Development

### Frontend (Local Server)

Use any static file server:

```bash
# Using Python
python -m http.server 8000

# Using Node.js
npx serve .

# Using PHP
php -S localhost:8000
```

Then visit `http://localhost:8000`

### Backend (Wrangler Dev)

```bash
wrangler dev
```

This starts a local development server at `http://localhost:8787`

Update `assets/js/config.js` to use the local endpoint:

```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:8787',
    // ...
};
```

## Custom Domain (Optional)

### Frontend Custom Domain

1. Add a CNAME file to the repository root with your domain
2. Configure DNS to point to GitHub Pages
3. Enable HTTPS in repository settings

### Backend Custom Domain

1. Go to Cloudflare Workers dashboard
2. Select your worker
3. Click "Triggers" > "Custom Domains"
4. Add your custom domain
5. Update `assets/js/config.js` with the new API URL

## Environment Variables

Configure in `wrangler.toml`:

```toml
[vars]
ENVIRONMENT = "production"
MAX_WORKERS = "10"
TASK_TIMEOUT = "300"
```

## Monitoring & Logs

### Cloudflare Dashboard

- View worker logs in real-time
- Monitor requests, errors, and performance
- Set up alerts for errors

### Command Line

```bash
# Stream live logs
wrangler tail

# View metrics
wrangler dev --inspect
```

## Security Considerations

1. **CORS**: The worker allows all origins by default. Restrict this in production:
   ```python
   cors_headers = {
       'Access-Control-Allow-Origin': 'https://owasp-blt.github.io',
       # ...
   }
   ```

2. **Rate Limiting**: Implement rate limiting for production
3. **Authentication**: Add API key or JWT authentication
4. **Input Validation**: Ensure all inputs are validated
5. **HTTPS**: Always use HTTPS for the API endpoint

## Troubleshooting

### CORS Errors

- Ensure CORS headers are properly set in the worker
- Check browser console for specific CORS errors
- Verify the API_BASE_URL in config.js is correct

### Worker Not Responding

- Check wrangler logs: `wrangler tail`
- Verify KV namespaces are properly configured
- Ensure worker is deployed: `wrangler publish`

### Frontend Not Loading

- Clear browser cache
- Check GitHub Pages is enabled in repository settings
- Verify all files are committed and pushed
- Check browser console for errors

## CI/CD (Optional)

### GitHub Actions for Frontend

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./
```

### GitHub Actions for Backend

Create `.github/workflows/deploy-worker.yml`:

```yaml
name: Deploy Cloudflare Worker

on:
  push:
    branches: [ main ]
    paths:
      - 'src/**'
      - 'wrangler.toml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Cloudflare Workers
        uses: cloudflare/wrangler-action@2.0.0
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
```

## Support

For issues and questions:
- Open an issue on GitHub
- Check the API documentation in API.md
- Review Cloudflare Workers documentation

---

Happy Deploying! 🚀
