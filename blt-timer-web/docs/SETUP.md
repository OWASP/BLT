# Setup Guide

Complete guide to setting up Fresh Time Tracker for development and production.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Cloudflare Setup](#cloudflare-setup)
4. [GitHub Integration](#github-integration)
5. [Local LLM Setup](#local-llm-setup)
6. [Client Setup](#client-setup)
7. [Production Deployment](#production-deployment)

## Prerequisites

### Required Software
- Node.js 18+ ([Download](https://nodejs.org/))
- npm 9+ (comes with Node.js)
- Git ([Download](https://git-scm.com/))
- Cloudflare account ([Sign up](https://dash.cloudflare.com/sign-up))

### Optional Software
- Ollama (for local LLM) ([Install](https://ollama.ai/))
- Docker (for LocalAI) ([Install](https://www.docker.com/))

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/OWASP-BLT/Fresh.git
cd Fresh
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Create Environment File

Create `.dev.vars` in the project root:

```env
# Optional: GitHub Integration
GITHUB_CLIENT_ID=your-github-app-client-id
GITHUB_CLIENT_SECRET=your-github-app-secret

# Optional: Encryption
ENCRYPTION_KEY=your-secure-random-key-here

# Optional: Local LLM
LOCAL_LLM_ENDPOINT=http://localhost:11434
```

### 4. Start Development Server

```bash
npm run dev
```

The server will start at `http://localhost:8787`

### 5. Test the API

```bash
# Health check
curl http://localhost:8787/health

# Get API info
curl http://localhost:8787/
```

## Cloudflare Setup

### 1. Install Wrangler CLI

```bash
npm install -g wrangler
```

### 2. Login to Cloudflare

```bash
wrangler login
```

### 3. Create KV Namespaces

```bash
# Time tracking data
wrangler kv:namespace create TIME_TRACKING_DATA

# Activity data  
wrangler kv:namespace create ACTIVITY_DATA

# Preview namespaces (for development)
wrangler kv:namespace create TIME_TRACKING_DATA --preview
wrangler kv:namespace create ACTIVITY_DATA --preview
```

### 4. Update wrangler.toml

Copy the namespace IDs from the output and update `wrangler.toml`:

```toml
[[kv_namespaces]]
binding = "TIME_TRACKING_DATA"
id = "your-kv-namespace-id-here"
preview_id = "your-preview-namespace-id-here"

[[kv_namespaces]]
binding = "ACTIVITY_DATA"
id = "your-kv-namespace-id-here"
preview_id = "your-preview-namespace-id-here"
```

### 5. Set Environment Variables

```bash
# Set production secrets
wrangler secret put ENCRYPTION_KEY
wrangler secret put GITHUB_CLIENT_SECRET
```

## GitHub Integration

### 1. Create GitHub OAuth App

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Fill in details:
   - Application name: Fresh Time Tracker
   - Homepage URL: https://your-app.com
   - Authorization callback URL: https://your-app.com/auth/callback
4. Save Client ID and Client Secret

### 2. Create GitHub Webhook

1. Go to your repository settings
2. Navigate to Webhooks → Add webhook
3. Payload URL: `https://your-worker.workers.dev/api/webhooks/github`
4. Content type: `application/json`
5. Select events:
   - Push
   - Pull requests
   - Issues
   - Issue comments
6. Add secret token (store securely)

### 3. Configure Application

Add to `.dev.vars`:

```env
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
GITHUB_WEBHOOK_SECRET=your-webhook-secret
```

## Local LLM Setup

### Option 1: Ollama (Recommended)

#### Install Ollama

**macOS:**
```bash
curl https://ollama.ai/install.sh | sh
```

**Linux:**
```bash
curl https://ollama.ai/install.sh | sh
```

**Windows:**
Download from [ollama.ai](https://ollama.ai/)

#### Pull Vision Model

```bash
# LLaVA - Good for screenshot analysis
ollama pull llava

# Alternative: BakLLaVA
ollama pull bakllava
```

#### Start Ollama

```bash
ollama serve
```

Default endpoint: `http://localhost:11434`

#### Test Ollama

```bash
curl http://localhost:11434/api/version
```

### Option 2: LocalAI (Docker)

```bash
# Pull image
docker pull quay.io/go-skynet/local-ai:latest

# Run with vision model
docker run -p 8080:8080 \
  -v /path/to/models:/models \
  quay.io/go-skynet/local-ai:latest

# Test
curl http://localhost:8080/v1/models
```

### Option 3: Transformers.js (Browser)

For browser-based local analysis, no setup required. Models download automatically.

## Client Setup

### Browser Client

```html
<!DOCTYPE html>
<html>
<head>
  <title>Fresh Time Tracker</title>
</head>
<body>
  <script type="module">
    import TimeTrackerClient from './client/tracker-client.ts';
    
    const tracker = new TimeTrackerClient({
      apiUrl: 'https://your-worker.workers.dev',
      userId: 'user-123',
      projectId: 'project-456',
      enableKeyboard: true,
      enableMouse: true,
      enableScreenshots: false,
    });
    
    // Start tracking
    window.startTracking = () => tracker.startSession();
    window.stopTracking = () => tracker.endSession();
  </script>
  
  <button onclick="startTracking()">Start Tracking</button>
  <button onclick="stopTracking()">Stop Tracking</button>
</body>
</html>
```

### CLI Client

```bash
# Make executable
chmod +x examples/cli-tracker.ts

# Run with ts-node
npx ts-node examples/cli-tracker.ts

# Or compile and run
tsc examples/cli-tracker.ts
node examples/cli-tracker.js
```

### Node.js Client

```javascript
const TimeTrackerClient = require('./client/tracker-client');

const tracker = new TimeTrackerClient({
  apiUrl: process.env.API_URL || 'http://localhost:8787',
  userId: process.env.USER_ID,
  projectId: process.env.PROJECT_ID,
});

async function main() {
  await tracker.startSession();
  
  // Your code here
  
  await tracker.endSession();
}

main();
```

## Production Deployment

### 1. Build and Deploy

```bash
# Type check
npm run type-check

# Deploy to Cloudflare
npm run deploy
```

### 2. Configure Custom Domain

```bash
# Add route to wrangler.toml
routes = [
  { pattern = "tracker.yourdomain.com/*", zone_name = "yourdomain.com" }
]

# Deploy again
npm run deploy
```

### 3. Set Up Monitoring

Add to `wrangler.toml`:

```toml
[observability]
enabled = true
```

View logs:
```bash
wrangler tail
```

### 4. Configure Rate Limiting

Add rate limiting in your worker:

```typescript
// Add to src/index.ts
import { RateLimiter } from './utils/rate-limiter';

const limiter = new RateLimiter({
  limit: 100,
  window: 60000, // 1 minute
});

app.use('*', async (c, next) => {
  const userId = c.req.header('X-User-ID');
  if (!limiter.check(userId)) {
    return c.json({ error: 'Rate limit exceeded' }, 429);
  }
  await next();
});
```

### 5. Enable Analytics

In Cloudflare Dashboard:
1. Go to Workers → Your Worker
2. Enable Analytics
3. Set up alerts for errors/latency

## Verification

### Test Deployment

```bash
# Health check
curl https://your-worker.workers.dev/health

# Start session
curl -X POST https://your-worker.workers.dev/api/sessions/start \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test-user" \
  -d '{"projectId": "test-project"}'

# Get sessions
curl https://your-worker.workers.dev/api/sessions \
  -H "X-User-ID: test-user"
```

### Monitor Performance

```bash
# View real-time logs
wrangler tail

# Check metrics
wrangler metrics
```

## Troubleshooting

### Common Issues

**Issue**: `wrangler: command not found`
```bash
npm install -g wrangler
```

**Issue**: KV namespace errors
```bash
# Verify namespaces exist
wrangler kv:namespace list

# Create if missing
wrangler kv:namespace create TIME_TRACKING_DATA
```

**Issue**: Local LLM connection refused
```bash
# Check if Ollama is running
ps aux | grep ollama

# Start if not running
ollama serve
```

**Issue**: CORS errors
- Ensure CORS is enabled in `src/index.ts`
- Check origin is allowed
- Verify headers are correct

### Debug Mode

```bash
# Run with debug logging
wrangler dev --log-level debug

# Enable verbose output
wrangler deploy --verbose
```

### Get Help

- GitHub Issues: [Report a bug](https://github.com/OWASP-BLT/Fresh/issues)
- Discussions: [Ask a question](https://github.com/OWASP-BLT/Fresh/discussions)
- Cloudflare Docs: [Workers documentation](https://developers.cloudflare.com/workers/)

## Next Steps

- Read the [API Documentation](README.md#api-endpoints)
- Check out [Examples](../examples/)
- Review [Privacy Policy](PRIVACY.md)
- Join the community discussions
