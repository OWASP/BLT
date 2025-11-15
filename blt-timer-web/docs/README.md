# Fresh Time Tracker Documentation

## Overview

Fresh Time Tracker is a privacy-focused time tracking system designed for developers. It monitors your work activity across multiple sources while keeping your data secure and private.

## Key Features

### 1. **Multi-Source Activity Tracking**
- **GitHub Integration**: Automatic tracking of commits, pull requests, issues, and reviews
- **Keyboard & Mouse Activity**: Monitor active work time vs idle time
- **Agent Prompt Tracking**: Track interactions with AI assistants (GitHub Copilot, ChatGPT, etc.)
- **Screenshot Analysis**: Optional local screenshot analysis for productivity insights

### 2. **Privacy & Security First**
- ✅ **Local LLM Processing**: All screenshot analysis happens locally on your machine
- ✅ **No 3rd Party Upload**: Screenshots and sensitive data NEVER leave your device
- ✅ **Encrypted Storage**: All data stored in Cloudflare KV with encryption
- ✅ **User Control**: Full control over what data is collected and when

### 3. **Cloudflare Worker Architecture**
- Global edge deployment for low latency
- Durable Objects for real-time session management
- WebSocket support for live activity tracking
- KV storage for persistent data

## Architecture

```
┌─────────────────┐
│  Client-Side    │
│  Tracker        │
│  (Browser/CLI)  │
└────────┬────────┘
         │
         │ HTTPS/WebSocket
         │
┌────────▼────────┐
│  Cloudflare     │
│  Worker         │
│  (Edge)         │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────────┐
│  KV   │ │  Durable    │
│ Store │ │  Objects    │
└───────┘ └─────────────┘

┌─────────────────┐
│  Local LLM      │
│  (User Device)  │
│  - Screenshot   │
│    Analysis     │
└─────────────────┘
```

## Getting Started

### Prerequisites

- Node.js 18+
- Cloudflare account (for deployment)
- Wrangler CLI

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

This starts the Cloudflare Worker in development mode.

### Deployment

```bash
npm run deploy
```

## API Endpoints

### Session Management

#### Start Session
```
POST /api/sessions/start
Headers: X-User-ID: <user-id>
Body: { "projectId": "project-123" }
```

#### End Session
```
POST /api/sessions/:sessionId/end
Headers: X-User-ID: <user-id>
```

#### Pause Session
```
POST /api/sessions/:sessionId/pause
Headers: X-User-ID: <user-id>
```

#### Resume Session
```
POST /api/sessions/:sessionId/resume
Headers: X-User-ID: <user-id>
```

#### Get Session
```
GET /api/sessions/:sessionId
Headers: X-User-ID: <user-id>
```

#### List Sessions
```
GET /api/sessions?limit=50
Headers: X-User-ID: <user-id>
```

### Activity Tracking

#### Track Activity
```
POST /api/activity
Headers: X-User-ID: <user-id>
Body: {
  "sessionId": "session-123",
  "type": "keyboard|mouse|github|agent-prompt|screenshot",
  "data": { ... }
}
```

#### Get Session Activities
```
GET /api/sessions/:sessionId/activities
Headers: X-User-ID: <user-id>
```

#### Get Session Summary
```
GET /api/sessions/:sessionId/summary
Headers: X-User-ID: <user-id>
```

### Webhooks

#### GitHub Webhook
```
POST /api/webhooks/github
Headers: 
  X-User-ID: <user-id>
  X-Session-ID: <session-id>
Body: <GitHub webhook payload>
```

## Client Usage

### Browser

```typescript
import TimeTrackerClient from './client/tracker-client';

const tracker = new TimeTrackerClient({
  apiUrl: 'https://your-worker.workers.dev',
  userId: 'user-123',
  projectId: 'project-456',
  enableKeyboard: true,
  enableMouse: true,
  enableScreenshots: false, // Requires explicit consent
  screenshotInterval: 15, // minutes
});

// Start tracking
await tracker.startSession();

// Track agent usage
await tracker.trackAgentPrompt('GitHub Copilot', 150, 500);

// End tracking
await tracker.endSession();
```

### Node.js CLI

See `examples/cli-tracker.ts` for a complete CLI implementation.

## Privacy Guarantees

### What We Track
- ✅ Activity patterns (keyboard/mouse activity counts)
- ✅ GitHub events (commits, PRs, issues)
- ✅ Agent prompt metadata (lengths, agent names)
- ✅ High-level activity classification (coding, debugging, etc.)

### What We DON'T Track
- ❌ Actual keystrokes or text content
- ❌ Screenshot images (only local analysis results)
- ❌ Specific code content
- ❌ Personal identifiable information in prompts

### Screenshot Analysis

When enabled (with explicit user consent):

1. **Screenshot is captured** on user's device
2. **Analyzed locally** using a local LLM (e.g., Ollama, LLaMA)
3. **Screenshot is immediately deleted** after analysis
4. **Only generic classification** is sent to server:
   - Activity type: coding, debugging, research, communication
   - Confidence score
   - No image data, no text content

### Data Storage

- All data encrypted at rest in Cloudflare KV
- User IDs are hashed
- GitHub tokens stored encrypted, never exposed in responses
- Retention policies can be configured per user

## Configuration

### Environment Variables

Create a `.dev.vars` file for local development:

```env
# GitHub Integration (optional)
GITHUB_CLIENT_ID=your-github-app-client-id
GITHUB_CLIENT_SECRET=your-github-app-secret

# Encryption key for sensitive data
ENCRYPTION_KEY=your-secure-encryption-key

# Local LLM endpoint (for screenshot analysis)
LOCAL_LLM_ENDPOINT=http://localhost:11434 # Ollama default
```

### User Preferences

Users can configure their tracking preferences:

```typescript
{
  enableScreenshots: false,
  screenshotInterval: 15, // minutes
  enableKeyboardTracking: true,
  enableMouseTracking: true,
  enableGitHubIntegration: true,
  enableAgentPromptTracking: true,
  privacyMode: 'full' // 'full' or 'minimal'
}
```

## GitHub Integration

### Setup GitHub Webhooks

1. Go to your repository settings
2. Add webhook URL: `https://your-worker.workers.dev/api/webhooks/github`
3. Select events: push, pull_request, issues, issue_comment
4. Add secret token for security

### OAuth Integration

For private repositories, users need to authorize the app:

1. Create a GitHub OAuth App
2. Add client ID and secret to environment
3. Implement OAuth flow in your client application

## Local LLM Setup

For screenshot analysis, you need a local LLM:

### Option 1: Ollama

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a vision model
ollama pull llava

# Run locally
ollama serve
```

### Option 2: LocalAI

```bash
# Using Docker
docker run -p 8080:8080 quay.io/go-skynet/local-ai:latest
```

### Option 3: Transformers.js

For browser-based analysis, use transformers.js with a vision model.

## Security Considerations

1. **API Authentication**: Implement proper authentication (JWT, OAuth)
2. **Rate Limiting**: Add rate limiting to prevent abuse
3. **Data Encryption**: Use strong encryption for sensitive data
4. **Access Control**: Implement role-based access control
5. **Audit Logging**: Log all data access for security audits

## Performance

- Worker response time: < 50ms (global edge)
- WebSocket latency: < 100ms
- Activity sync interval: 60 seconds (configurable)
- KV read/write: < 10ms

## Scaling

The system scales automatically with Cloudflare Workers:

- No servers to manage
- Automatic global distribution
- Pay-per-request pricing
- Handles millions of requests

## Roadmap

- [ ] Mobile app support (iOS/Android)
- [ ] VS Code extension
- [ ] Browser extension
- [ ] Jira/Linear integration
- [ ] Team dashboards
- [ ] Advanced analytics
- [ ] Export to CSV/JSON
- [ ] Custom reporting

## Contributing

See CONTRIBUTING.md for guidelines.

## License

MIT License - see LICENSE file.

## Support

For issues or questions:
- GitHub Issues: https://github.com/OWASP-BLT/Fresh/issues
- Email: support@example.com
- Docs: https://docs.example.com
