# BLT-Lettuce Cloudflare Worker

A Cloudflare Python Worker that handles Slack webhooks, sends welcome messages to new users, and tracks statistics.

## Features

- **Webhook Endpoint**: Receives Slack events via webhook
- **Welcome Messages**: Automatically sends welcome messages to new team members
- **Stats Tracking**: Tracks number of joins and commands run
- **Stats API**: Provides a JSON endpoint for stats consumption

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
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

5. Set up secrets:
   ```bash
   wrangler secret put SLACK_TOKEN
   wrangler secret put SIGNING_SECRET
   ```

6. Deploy the worker:
   ```bash
   wrangler deploy
   ```

## Configuration

### Slack App Setup

1. Go to [Slack API](https://api.slack.com/apps) and create a new app
2. Enable Event Subscriptions and add the webhook URL: `https://your-worker.workers.dev/webhook`
3. Subscribe to the `team_join` event
4. Install the app to your workspace
5. Copy the Bot User OAuth Token and use it for `SLACK_TOKEN`
6. Copy the Signing Secret and use it for `SIGNING_SECRET`

### Required Bot Permissions

- `chat:write` - Send messages
- `im:write` - Open DM conversations
- `users:read` - Read user information

## Stats

Stats are stored in Cloudflare KV and include:
- `joins`: Number of new team members who have joined
- `commands`: Number of commands run
- `last_updated`: Timestamp of last update

## Development

Run locally:
```bash
wrangler dev
```

View logs:
```bash
wrangler tail
```

## Stats Dashboard

View the stats dashboard at the GitHub Pages site for this repository.
