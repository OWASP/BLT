# BLT-Lettuce Deployment Guide

This guide will walk you through deploying BLT-Lettuce to Cloudflare Workers and configuring it for your Slack workspace.

## Prerequisites

Before you begin, make sure you have:

- A Cloudflare account (free tier works)
- A Slack workspace where you have admin permissions
- Node.js and npm installed (for Wrangler CLI)

## Step 1: Set Up Cloudflare

### 1.1 Install Wrangler CLI

```bash
npm install -g wrangler
```

### 1.2 Login to Cloudflare

```bash
wrangler login
```

This will open a browser window for you to authenticate.

### 1.3 Create KV Namespace

```bash
cd cloudflare-worker
wrangler kv:namespace create "STATS_KV"
```

Copy the namespace ID from the output. It will look like:
```
{ binding = "STATS_KV", id = "abc123def456" }
```

### 1.4 Update wrangler.toml

Edit `wrangler.toml` and replace `REPLACE_WITH_YOUR_KV_NAMESPACE_ID` with your actual namespace ID.

## Step 2: Set Up Slack App

### Option A: Using manifest.yaml (Recommended)

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From an app manifest**
3. Select your workspace
4. Copy the contents of `manifest.yaml` from this repo
5. Paste it and click **Create**
6. **Important**: Update the Request URLs in the manifest with your actual worker URL:
   - Change `https://your-worker.workers.dev/webhook` to your actual URL
   - You'll get this URL after deploying in Step 3

### Option B: Manual Configuration

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From scratch**
3. Name it "BLT-Lettuce" and select your workspace
4. Configure OAuth & Permissions:
   - Add these Bot Token Scopes:
     - `chat:write`
     - `im:write`
     - `im:read`
     - `im:history`
     - `channels:history`
     - `channels:read`
     - `users:read`
     - `team:read`
5. Enable Event Subscriptions:
   - Set Request URL to `https://your-worker.workers.dev/webhook`
   - Subscribe to bot events:
     - `team_join`
     - `message.channels`
     - `message.im`
     - `message.mpim`
     - `app_mention`
6. Enable Interactivity:
   - Set Request URL to `https://your-worker.workers.dev/webhook`

### 2.1 Get Your Credentials

1. Go to **OAuth & Permissions**
2. Install the app to your workspace
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
4. Go to **Basic Information**
5. Copy the **Signing Secret**

## Step 3: Deploy to Cloudflare

### 3.1 Set Up Secrets

```bash
cd cloudflare-worker

# Set your Slack Bot Token
wrangler secret put SLACK_TOKEN
# Paste your xoxb- token when prompted

# Set your Signing Secret
wrangler secret put SIGNING_SECRET
# Paste your signing secret when prompted
```

### 3.2 (Optional) Configure Custom Channel IDs

If you want to customize the channels for notifications:

```bash
# Channel where join notifications are posted
wrangler secret put JOINS_CHANNEL_ID
# Enter your channel ID (e.g., C06RMMRMGHE)

# Channel ID for contribution guidelines
wrangler secret put CONTRIBUTE_ID
# Enter your channel ID (e.g., C04DH8HEPTR)
```

To find a channel ID in Slack:
1. Right-click on the channel name
2. Select "Copy link"
3. The ID is the last part of the URL: `https://workspace.slack.com/archives/C06RMMRMGHE`

### 3.3 Deploy the Worker

```bash
wrangler deploy
```

You'll get a URL like: `https://blt-lettuce-worker.your-subdomain.workers.dev`

## Step 4: Update Slack App URLs

If you created your app before deploying:

1. Go back to your Slack app settings
2. Update these URLs with your actual worker URL:
   - **Event Subscriptions** → Request URL: `https://your-actual-worker-url.workers.dev/webhook`
   - **Interactivity & Shortcuts** → Request URL: `https://your-actual-worker-url.workers.dev/webhook`
3. Click **Save Changes**

Slack will verify the URL - you should see a green checkmark if everything is configured correctly.

## Step 5: Test Your Bot

1. In your Slack workspace, invite a test user or create a new account
2. The bot should automatically send them a welcome DM
3. Try sending a message with the word "contribute" - the bot should respond
4. Visit your worker URL in a browser to see the dashboard
5. Visit `https://your-worker-url.workers.dev/stats` to see the stats API

## Deploying to Multiple Organizations

To allow other Slack workspaces to install your bot:

1. In your Slack app settings, go to **Manage Distribution**
2. Remove hard-coded information (if any)
3. Enable **Org-Wide App Installation**
4. You can now share your app's install link

Each organization will have its own isolated statistics in the Cloudflare KV store.

## Troubleshooting

### URL Verification Failed

- Make sure the worker is deployed: `wrangler deploy`
- Check that the URL in Slack matches exactly: `https://your-worker.workers.dev/webhook`
- Look at worker logs: `wrangler tail`

### Bot Not Responding

- Check that secrets are set: `wrangler secret list`
- Verify the bot has the right permissions in Slack
- Check logs: `wrangler tail`
- Make sure the bot is installed in your workspace

### Stats Not Updating

- Verify KV namespace is correctly configured in `wrangler.toml`
- Check that you replaced the placeholder namespace ID
- Look for errors in logs: `wrangler tail`

### Cannot Open DM with User

- Make sure the bot has `im:write` permission
- Verify the bot is installed in the workspace
- Some users may have DMs disabled in their settings

## Monitoring

### View Logs

```bash
wrangler tail
```

This shows real-time logs from your worker.

### Check Stats

Visit `https://your-worker-url.workers.dev/stats` to see:
- Number of members welcomed
- Number of commands processed
- Last update timestamp

### View Dashboard

Visit `https://your-worker-url.workers.dev/` to see the full dashboard with:
- Live statistics
- Bot features
- GitHub project information

## Updating the Worker

To update your worker after making changes:

```bash
cd cloudflare-worker
wrangler deploy
```

The update is instant - no downtime required.

## Cost

Cloudflare Workers free tier includes:
- 100,000 requests per day
- 10ms CPU time per request

For a typical Slack workspace, this is more than enough and completely free!

## Support

If you encounter issues:
1. Check the [GitHub Issues](https://github.com/OWASP-BLT/BLT-Lettuce/issues)
2. Review the [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
3. Check the [Slack API Documentation](https://api.slack.com/)

## Security Notes

- Never commit your secrets (SLACK_TOKEN, SIGNING_SECRET) to version control
- The worker verifies all requests from Slack using HMAC signatures
- Replay attacks are prevented with timestamp validation
- All secrets are stored securely in Cloudflare's encrypted storage

---

**Congratulations!** 🎉 Your BLT-Lettuce bot is now running on Cloudflare Workers and ready to welcome new members to your Slack workspace!
