# BLT-Lettuce Cloudflare Worker

A Cloudflare Python Worker that serves as the complete backend for the BLT-Lettuce Slack bot. This worker handles Slack webhooks, sends welcome messages to new users, tracks statistics, and serves the homepage.

## Features

- **Homepage**: Serves the BLT-Lettuce dashboard at the root URL
- **Webhook Endpoint**: Receives Slack events via webhook
- **Welcome Messages**: Automatically sends welcome messages to new team members
- **Message Handler**: Detects keywords like "contribute" and provides helpful responses
- **Direct Message Support**: Responds to direct messages from users
- **Stats Tracking**: Tracks number of joins and commands run
- **Stats API**: Provides a JSON endpoint for stats consumption
- **Multi-Org Support**: Can be installed in any Slack organization

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Homepage with dashboard |
| `/webhook` | POST | Slack webhook endpoint for receiving events |
| `/stats` | GET | Returns current statistics as JSON |
| `/health` | GET | Health check endpoint |

## Setup

### Prerequisites

- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- Cloudflare account
- Slack Bot Token and Signing Secret

### Installation

1. Install Wrangler:
   ```bash
   npm install -g wrangler
   ```

2. Login to Cloudflare:
   ```bash
   wrangler login
   ```

3. Create the KV namespace for stats:
   ```bash
   wrangler kv:namespace create "STATS_KV"
   ```

4. Update `wrangler.toml` with the KV namespace ID from the previous command.

5. Set up required secrets:
   ```bash
   wrangler secret put SLACK_TOKEN       # Your Bot User OAuth Token
   wrangler secret put SIGNING_SECRET    # Your Signing Secret
   ```

6. (Optional) Set up custom channel IDs:
   ```bash
   wrangler secret put JOINS_CHANNEL_ID  # Channel for join notifications
   wrangler secret put CONTRIBUTE_ID     # Channel for contribution guidelines
   ```

7. Deploy the worker:
   ```bash
   wrangler deploy
   ```

## Configuration

### Slack App Setup

1. Go to [Slack API](https://api.slack.com/apps) and create a new app or use the `manifest.yaml`
2. If creating manually:
   - Enable Event Subscriptions and add the webhook URL: `https://your-worker.workers.dev/webhook`
   - Subscribe to these bot events: `team_join`, `message.channels`, `message.im`, `app_mention`
   - Enable Interactivity and set Request URL to: `https://your-worker.workers.dev/webhook`
3. Install the app to your workspace
4. Copy the Bot User OAuth Token and use it for `SLACK_TOKEN`
5. Copy the Signing Secret and use it for `SIGNING_SECRET`

### Required Bot Permissions

- `chat:write` - Send messages
- `im:write` - Open DM conversations  
- `im:read` - Read direct messages
- `im:history` - Read DM history
- `channels:history` - Read channel messages
- `channels:read` - View basic channel information
- `users:read` - Read user information
- `team:read` - Read workspace information

### Multi-Organization Deployment

This bot is configured to support org-wide deployment, allowing it to be installed in any Slack organization:

1. In your Slack app settings, navigate to **Manage Distribution**
2. Enable **Org-Wide App Installation**
3. Complete the app directory listing (if you want to distribute publicly)
4. Share your app's installation URL

Each organization that installs the bot will have its own isolated stats in KV storage.

## Stats

Stats are stored in Cloudflare KV and include:
- `joins`: Number of new team members who have joined
- `commands`: Number of commands run
- `last_updated`: Timestamp of last update

Stats are workspace-specific and use optimistic locking to handle concurrent updates.

## Development

Run locally:
```bash
wrangler dev
```

View logs:
```bash
wrangler tail
```

Test the webhook endpoint:
```bash
curl -X POST https://your-worker.workers.dev/webhook \
  -H "Content-Type: application/json" \
  -d '{"type": "url_verification", "challenge": "test123"}'
```

## Homepage

The worker serves a responsive HTML dashboard at the root URL that displays:
- Live statistics from the KV store
- Information about the bot's features
- Links to join OWASP Slack and contribute on GitHub

## Environment Variables

### Required
- `SLACK_TOKEN` - Bot User OAuth Token (xoxb-...)
- `SIGNING_SECRET` - Slack App Signing Secret

### Optional (with defaults)
- `JOINS_CHANNEL_ID` - Channel ID for join notifications (default: C06RMMRMGHE)
- `CONTRIBUTE_ID` - Channel ID for contribution guidelines (default: C04DH8HEPTR)
- `DEPLOYS_CHANNEL` - Channel name for deployment notifications (default: #project-blt-lettuce-deploys)

## Security

- All Slack requests are verified using HMAC signature validation
- Replay attacks are prevented with timestamp checking (5-minute window)
- The bot ignores its own messages to prevent loops
- Error messages are sanitized to avoid exposing internal details

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Cloudflare Worker                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Homepage   │  │   Webhook    │  │    Stats     │  │
│  │   (HTML)     │  │   Handler    │  │     API      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Slack API   │ │      KV      │ │   Browser    │
│   (Events)   │ │   Storage    │ │   (Users)    │
└──────────────┘ └──────────────┘ └──────────────┘
```
