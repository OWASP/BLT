### File Naming Convention

Welcome message files in the `data/` directory use the following naming pattern:

`message-<team_id>-<channel_id>-ephemeral.md`

- `<team_id>`: The Slack team (workspace) ID (e.g., `T070JPE5BQQ`)
- `<channel_id>`: The Slack channel ID (e.g., `C06V9S85YR1`)

**Examples:**
- `message-T070JPE5BQQ-C06V9S85YR1-ephemeral.md` — Ephemeral join message for team `T070JPE5BQQ` in channel `C06V9S85YR1`
- `message-T070JPE5BQQ-C06V9S85YR1.md` — Persistent/channel template fallback for the same team/channel

Backward compatibility:
- `ephemeral-T070JPE5BQQ-C06V9S85YR1.md` is still recognized by the worker.

This convention makes it easy to distinguish between ephemeral and persistent messages and to target specific workspaces and channels.
<div align="center">

# 🥬 BLT-Lettuce

**Live Site:** [https://lettuce.owaspblt.org/](https://lettuce.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-Lettuce](https://git.owaspblt.org/BLT/BLT-Lettuce)

**An intelligent Slack bot for the OWASP community**

[![License](https://img.shields.io/github/license/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=blue)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=yellow)](https://git.owaspblt.org/BLT/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=green)](https://git.owaspblt.org/BLT/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=red)](https://git.owaspblt.org/BLT/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=purple)](https://git.owaspblt.org/BLT/pulls)

[![Contributors](https://img.shields.io/github/contributors/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=orange)](https://git.owaspblt.org/BLT/graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=cyan)](https://git.owaspblt.org/BLT/BLT-Lettuce/commits/main)
[![Commit Activity](https://img.shields.io/github/commit-activity/m/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=pink)](https://git.owaspblt.org/BLT/pulse)
[![Repo Size](https://img.shields.io/github/repo-size/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=gray)](https://git.owaspblt.org/BLT/BLT-Lettuce)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare_Workers-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://workers.cloudflare.com/)
[![Slack](https://img.shields.io/badge/Slack_API-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://api.slack.com/)

[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=flat-square&logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square)](https://github.com/astral-sh/ruff)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg?style=flat-square)](https://conventionalcommits.org)

[💬 **Join OWASP Slack**](https://owasp.org/slack/invite) · [🐛 **Report Bug**](https://git.owaspblt.org/BLT/issues/new?template=bug_report.md) · [✨ **Request Feature**](https://git.owaspblt.org/BLT/issues/new?template=feature_request.md)

</div>

---

## 📖 About

BLT-Lettuce is an intelligent Slack bot designed for the OWASP Slack workspace. It welcomes new members, helps them discover projects, and connects the global security community.

> **Note:** This Slack bot functionality has been incorporated into the main [BLT repository](https://git.owaspblt.org/BLT/BLT-Core) and is being transferred back to this repo for better organization.

### 🎯 Core Features



## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        OWASP Slack Workspace                     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloudflare Worker (Python)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Webhook    │  │    Stats     │  │   Project Discovery  │  │
│  │   Handler    │  │   Tracking   │  │      Flowchart       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
          ▼                       ▼                       ▼
│   Cloudflare    │    │    GitHub API   │    │   GitHub Pages  │
│   KV Storage    │    │  (Org scanning) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🔄 Project Discovery Flow

The bot uses a conversational flowchart to help users find OWASP projects:

```
┌─────────────────────────────────────┐
│        User Initiates Chat          │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  "What type of project interests    │
│   you?" (Multiple Choice)           │
│  • Documentation/Standards          │
│  • Security Tools                   │
│  • Deliberately Insecure Apps       │
│  • Research/Education               │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  "What technology stack?"           │
│  • Python  • Java  • JavaScript     │
│  • Go      • .NET  • Any            │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  Query cached project metadata      │
│  from configured GitHub orgs        │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  Return matching project links      │
│  with descriptions and stats        │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  No matches? Offer to:              │
│  • Start over with different params │
│  • Learn how to start a new project │
└─────────────────────────────────────┘
```

---

## 📊 Live Stats

View real-time statistics at our **[Stats Page](https://lettuce.owaspblt.org/)**:

- 👋 Members welcomed
- ⚡ Commands executed
- 🐙 GitHub project health metrics
- 🌍 Global availability status

---

## ☁️ Cloudflare Worker

BLT-Lettuce is now **fully powered by a Cloudflare Python Worker** (`src/worker.py`) that serves as the complete backend:

- **Homepage**: Serves the stats at the root URL
- **Slack Events**: Handles all webhook events (team joins, messages, mentions)
- **Welcome Messages**: Sends personalized welcome messages to new members
- **Message Handling**: Detects keywords like "contribute" and provides helpful responses
- **Direct Messages**: Responds to user DMs
- **Stats Tracking**: Tracks statistics in KV storage with atomic updates
- **Stats API**: Provides a JSON endpoint for live statistics
- **Multi-Org Support**: Can be installed in any Slack organization

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Homepage |
| `/webhook` | POST | Slack webhook for events |
| `/stats` | GET | Returns statistics JSON |
| `/health` | GET | Health check endpoint |
| `/health/welcome` | GET | OWASP welcome health (503 when failing; see below) |
| `/welcome-logo?tid=` | GET | Tracked footer logo of a welcome DM (records the first open) |
| `/admin/welcomes` | GET | Welcome delivery report (HTTP Basic; `?format=json`) |
| `/api/community-stats` | GET | OWASP joins per day (30 days) and channels with the most members |

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

### Environment Variables

**Required**
- `SLACK_TOKEN` - Bot User OAuth Token (xoxb-...)
- `SIGNING_SECRET` - Slack App Signing Secret

**Optional Channel Configuration**

For multi-organization deployments, you can configure custom channel IDs:
- `JOINS_CHANNEL_ID` - Channel ID where join notifications are posted (optional)
- `CONTRIBUTE_ID` - Channel ID for contribution guidelines link (optional)
- `DEPLOYS_CHANNEL` - Channel name for deployment notifications (optional)

> **Note**: If these are not set, the bot will skip channel-specific features (like posting join notifications to a monitoring channel) but all core functionality (welcome DMs, keyword detection) will still work.

To find a channel ID in Slack:
1. Right-click on the channel name → "Copy link"
2. The ID is the last part: `https://workspace.slack.com/archives/C06RMMRMGHE`

### Stats

Stats are stored in Cloudflare KV and include:
- `joins`: Number of new team members who have joined
- `commands`: Number of commands run
- `last_updated`: Timestamp of last update

Stats are workspace-specific and use optimistic locking to handle concurrent updates.

### Security

- All Slack requests are verified using HMAC signature validation
- Replay attacks are prevented with timestamp checking (5-minute window)
- The bot ignores its own messages to prevent loops
- Error messages are sanitized to avoid exposing internal details

## OWASP welcome bot

Lettuce welcomes new members of the OWASP Slack workspace (`T04T40NHX`). The code is
`src/lettuce/welcome_bot.py`; the text is `src/lettuce/messages/T04T40NHX-team_join.txt`
(a `.txt` inside `src/`, because Wrangler bundles text modules from `src/` but not `.md`
files or anything outside `src/`). blt-sammich sent this welcome before; BLT-project
workspaces and commands stay with sammich.

**How a join is handled.** `/webhook` checks the Slack signature, then a `team_join` from a
workspace in `WELCOME_TEAM_IDS` goes to `welcome_bot.accept_team_join`:

1. One `team_joins` row is inserted. Its partial unique index on `event_id` is the event
   claim: a Slack retry inserts nothing and is answered `duplicate`.
2. Slack gets its 200 at once; the DM is sent after the response (`ctx.waitUntil`).
3. `conversations.open`, then `chat.postMessage` with the BLT logo beside the text and a
   tracked logo (`/welcome-logo?tid=<96 random bits>`) in the footer. Each call is retried
   once on a rate limit, 5xx or network error.
4. The row gets `sent` (with `delivered_at` when Slack returns a message ts) or `failed`
   with the Slack error code. The first load of the footer logo sets `opened_at`.

Bots, deleted users and anyone welcomed in the last 30 days are recorded as `skipped`.
Logs are one JSON line (`[welcome] {...}`) with ids and Slack error codes, never tokens.

**Settings.**

| Name | Kind | Default | Meaning |
|------|------|---------|---------|
| `WELCOME_ENABLED` | secret | off | `true` sends welcome DMs. Off: joins are recorded (`disabled`), nobody is DMed. |
| `WELCOME_TEAM_IDS` | var | `T04T40NHX` | Workspaces handled by the welcome bot (comma-separated). |
| `WELCOME_SLACK_TOKEN` | secret | none | Only needed when lettuce isn't installed through `/workspace/add`; the install's token in `workspaces` comes first. |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | secrets | none | HTTP Basic for `/admin/welcomes`. Unset: the report always answers 401. |

`WELCOME_ENABLED` is a secret, not a `[vars]` entry, so a later deploy can't switch the
welcome back off. Set it with `npx wrangler secret put WELCOME_ENABLED`.

**Health.** `/health/welcome` reports the last join, the last delivered welcome, the last
24 hours (joins, eligible, delivered, failed, rate) and the last `auth.test`. With the
welcome on it answers **503** (`"status": "welcome-unhealthy"` and a `problems` list) when:
joins older than 10 minutes arrived in 24 h and none was delivered; 5 or more eligible joins
and under 50 % delivered; `auth.test` failed or the token is for another workspace; no
`auth.test` in 3 hours (the cron stopped); or the message file didn't load. Otherwise 200
with `welcome-healthy`. With the welcome off it answers 200 `welcome-disabled` and still
lists the problems. blt-monitor's `lettuce_owasp_welcome` check looks for `welcome-healthy`.

**Cron** (blt-cron calls `/__scheduled` hourly): `auth.test` with the OWASP token, stored in
`welcome_state`; once a day, `conversations.list` (public, not archived) for the channels with
the most members, kept as one `welcome_state` row and shown at the end of the welcome
("Most Active Channels", the 5 biggest) and in `/api/community-stats`. Lettuce's per-channel
scan, `users.list` member count, missing-GitHub-org alert and inactivity alert skip welcome
workspaces, and their events don't write `Webhook_Received` rows.

**D1 cost.** A welcomed join is one INSERT (about 5 row writes with indexes) and one UPDATE;
an open is one more UPDATE. The cron adds about 25 writes a day. Migration
`007_owasp_welcome.sql` only creates new tables.

### Cut-over from sammich

1. Apply the migration (`npx wrangler d1 migrations apply blt-lettuce --remote`) and deploy
   lettuce, blt-sammich and blt-monitor. Nothing changes yet: lettuce's welcome is off and
   sammich's is on.
2. Install lettuce in the OWASP workspace (owner checklist below). Lettuce now records OWASP
   joins as `disabled`; check `/admin/welcomes` shows them, and within an hour
   `/health/welcome` shows `"slack_auth": {"ok": true, ...}`.
3. In the same minute:
   `cd blt-lettuce && echo true | npx wrangler secret put WELCOME_ENABLED` and
   `cd blt-sammich && echo false | npx wrangler secret put WELCOME_ENABLED`.
4. Watch the next joins in `/admin/welcomes` (status `sent`, delivered) and
   `/health/welcome` (`welcome-healthy`). Then set `"enabled": true` on
   `lettuce_owasp_welcome` in `blt-monitor/public/monitors.json` and deploy blt-monitor.

Only the bot with `WELCOME_ENABLED` on sends, even while both apps receive `team_join`.
A join that arrives between the two `secret put` commands can be welcomed by both or by
neither; with about 40-60 joins a day that is unlikely, and a missed one shows in
`/admin/welcomes`.

**Rollback:** `echo false | npx wrangler secret put WELCOME_ENABLED` in blt-lettuce and
`echo true | npx wrangler secret put WELCOME_ENABLED` in blt-sammich (or delete both secrets:
the defaults are lettuce off, sammich on), and set the monitor back to `"enabled": false`.

### Owner checklist (Slack)

- **Lettuce app** (api.slack.com/apps, app `A076K2SA7PG`):
  - Event Subscriptions: Request URL `https://lettuce.owaspblt.org/webhook` shows Verified,
    and `team_join` is under bot events.
  - OAuth & Permissions: the redirect URL `https://lettuce.owaspblt.org/callback` is listed.
  - Manage Distribution: public distribution is on. The app is installed only in the BLT
    workspace today; unless OWASP is its home workspace, it can't be installed there without
    distribution.
- **Install in OWASP:** an OWASP workspace admin opens `https://lettuce.owaspblt.org/workspace/add`
  while signed in to the OWASP workspace and approves. The bot scopes requested are
  `channels:read, chat:write, users:read, team:read, im:write, im:read, im:history`, plus
  the user scopes `identity.basic, identity.email, identity.team`. If OWASP requires app
  approval, approve Lettuce in the workspace admin settings first. The install stores the
  OWASP bot token in lettuce's D1 `workspaces` table; there is no token to copy by hand.
- **Lettuce secrets** (already set: `SIGNING_SECRET`, `SLACK_TOKEN`, `SLACK_CLIENT_ID`,
  `SLACK_CLIENT_SECRET`, `CRON_SECRET`, `BASE_URL`): add `ADMIN_USERNAME` and
  `ADMIN_PASSWORD` for the report. `WELCOME_ENABLED` is set at the cut-over.
- **blt-monitor:** it has no `SLACK_WEBHOOK_URL` secret, so its failures currently alert
  nobody. Create an incoming webhook for the alert channel and set it with
  `npx wrangler secret put SLACK_WEBHOOK_URL` in blt-monitor.

---

## 🚀 Quick Start

### Prerequisites

- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) for Cloudflare Workers
- Cloudflare account
- Slack Bot Token and Signing Secret

### Deploy to Cloudflare Workers

1. **Clone the repository**
   ```bash
   git clone https://git.owaspblt.org/BLT.git
   cd BLT-Lettuce
   ```

2. **Install Wrangler and login**
   ```bash
   npm install -g wrangler
   wrangler login
   ```

3. **Set up secrets**
   ```bash
   wrangler secret put SLACK_TOKEN       # Your Bot User OAuth Token
   wrangler secret put SIGNING_SECRET    # Your Signing Secret
   ```

   **Or use the automated setup script** (recommended for production):
   
   ```bash
   # Copy the example env file
   cp .env.production.example .env.production
   
   # Edit with your production credentials
   nano .env.production
   
   # Run the setup script
   python scripts/setup-env.py
   ```
   
   See [Environment Setup Guide](#environment-setup) for detailed instructions.

4. **Deploy the worker**
   ```bash
   wrangler deploy
   ```

5. **Configure Slack App**
   - Use the `manifest.yaml` to create or update your Slack app
   - Or manually configure Event Subscriptions URL: `https://your-worker.workers.dev/webhook`
   - Subscribe to events: `team_join`, `message.channels`, `message.im`, `app_mention`

### Adding to Any Slack Organization

This bot supports org-wide deployment and can be installed in any Slack workspace:

1. Create your Slack app using the provided `manifest.yaml`
2. Deploy the Cloudflare Worker to your account
3. Enable **Org-Wide App Installation** in your Slack app settings
4. Share the installation URL with other organizations

Each organization will have its own isolated statistics and configuration.

---

## 📁 Project Structure

```
BLT-Lettuce/
├── src/
│   ├── worker.py           # Complete Python worker with all bot logic
│   └── lettuce/            # Bot plugins and modules (for reference)
├── wrangler.toml           # Worker configuration
├── manifest.yaml           # Slack App manifest for easy setup
├── docs/
│   └── index.html          # GitHub Pages stats (reference)
├── app.py                  # Legacy Flask application (kept for reference)
├── data/
│   ├── projects.json       # OWASP project metadata cache
│   └── repos.json          # Repository categorization
├── tests/                  # Test suite
├── pyproject.toml          # Python dependencies
└── README.md               # This file
```

**Note**: The primary application is now the Cloudflare Worker in `src/worker.py`. The Flask app (`app.py`) and related plugins are kept for historical reference and may be removed in a future release. All new development should focus on the Cloudflare Worker implementation.

---

## 🤝 How to Contribute

We welcome contributions from everyone! Here's how to get started:

1. **Fork the Repository** - Click "Fork" at the top right of this page
2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR-USERNAME/BLT-Lettuce.git
   ```
3. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make Changes** - Follow our coding standards (enforced by pre-commit hooks)
5. **Test Your Changes**
   ```bash
   poetry run pytest
   ```
6. **Commit with Conventional Commits**
   ```bash
   git commit -m "feat: add new feature"
   ```
7. **Push and Open a PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### 📺 Contributing Video Tutorial

Watch our [contribution walkthrough video](https://www.loom.com/share/4b0f414ed3974f44a14659532b855e79?sid=e5d85c12-8782-4341-900b-3f978f9a9fd2) for a step-by-step guide.

---

## 🧑‍💻 Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run ruff check --fix .
poetry run ruff format .
```

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

---

## 🚀 Deployment Guide

This section contains the complete deployment guide previously kept in DEPLOYMENT.md.

### Prerequisites

Before you begin, make sure you have:

- A Cloudflare account (free tier works)
- A Slack workspace where you have admin permissions
- Node.js and npm installed (for Wrangler CLI)

### Step 1: Set Up Cloudflare

#### 1.1 Install Wrangler CLI

```bash
npm install -g wrangler
```

#### 1.2 Login to Cloudflare

```bash
wrangler login
```

This will open a browser window for you to authenticate.

#### 1.3 Update wrangler.toml

Edit wrangler.toml and replace the placeholder database_id with your actual D1 database ID.

### Step 2: Set Up Slack App

#### Option A: Using manifest.yaml (Recommended)

1. Go to https://api.slack.com/apps
2. Click Create New App -> From an app manifest
3. Select your workspace
4. Copy the contents of manifest.yaml from this repo
5. Paste it and click Create
6. Update the Request URLs in the manifest with your actual worker URL:
   - Change https://your-worker.workers.dev/webhook to your actual URL
   - You will get this URL after deploying in Step 3

#### Option B: Manual Configuration

1. Go to https://api.slack.com/apps
2. Click Create New App -> From scratch
3. Name it "BLT-Lettuce" and select your workspace
4. Configure OAuth and Permissions:
   - Add these Bot Token Scopes:
     - chat:write
     - im:write
     - im:read
     - im:history
     - channels:history
     - channels:read
     - users:read
     - team:read
5. Enable Event Subscriptions:
   - Set Request URL to https://your-worker.workers.dev/webhook
   - Subscribe to bot events:
     - team_join
     - message.channels
     - message.im
     - message.mpim
     - app_mention
6. Enable Interactivity:
   - Set Request URL to https://your-worker.workers.dev/webhook

#### 2.1 Get Your Credentials

1. Go to OAuth and Permissions
2. Install the app to your workspace
3. Copy the Bot User OAuth Token (starts with xoxb-)
4. Go to Basic Information
5. Copy the Signing Secret

### Step 3: Deploy to Cloudflare

#### 3.1 Set Up Secrets

```bash
# Set your Slack Bot Token
wrangler secret put SLACK_TOKEN

# Set your Signing Secret
wrangler secret put SIGNING_SECRET
```

#### 3.2 Optional Channel IDs

```bash
# Channel where join notifications are posted
wrangler secret put JOINS_CHANNEL_ID

# Channel ID for contribution guidelines
wrangler secret put CONTRIBUTE_ID
```

To find a channel ID in Slack:
1. Right-click on the channel name
2. Select Copy link
3. The ID is the last part of the URL, for example:
   https://workspace.slack.com/archives/C06RMMRMGHE

#### 3.3 Deploy the Worker

```bash
wrangler deploy
```

You will get a URL like:
https://blt-lettuce-worker.your-subdomain.workers.dev

### Step 4: Update Slack App URLs

If you created your app before deploying:

1. Go back to your Slack app settings
2. Update these URLs with your actual worker URL:
   - Event Subscriptions -> Request URL: https://your-actual-worker-url.workers.dev/webhook
   - Interactivity and Shortcuts -> Request URL: https://your-actual-worker-url.workers.dev/webhook
3. Click Save Changes

Slack will verify the URL and you should see a green checkmark when configured correctly.

### Step 5: Test Your Bot

1. In your Slack workspace, invite a test user or create a new account
2. The bot should automatically send them a welcome DM
3. Try sending a message with the word "contribute" and the bot should respond
4. Visit your worker URL in a browser to see the homepage

### Deploying to Multiple Organizations

To allow other Slack workspaces to install your bot:

1. In your Slack app settings, go to Manage Distribution
2. Remove hard-coded information, if any
3. Enable Org-Wide App Installation
4. Share your app install link

Each organization will have its own isolated data in the Cloudflare D1 database.

### Troubleshooting

#### URL Verification Failed

- Make sure the worker is deployed: wrangler deploy
- Check that the URL in Slack matches exactly: https://your-worker.workers.dev/webhook
- Look at worker logs: wrangler tail

#### Bot Not Responding

- Check that secrets are set: wrangler secret list
- Verify the bot has the right permissions in Slack
- Check logs: wrangler tail
- Make sure the bot is installed in your workspace

#### Cannot Open DM with User

- Make sure the bot has im:write permission
- Verify the bot is installed in the workspace
- Some users may have DMs disabled in their settings

### Monitoring

#### View Logs

```bash
wrangler tail
```

#### View Homepage

Visit https://your-worker-url.workers.dev/ to see the full homepage with:
- Live statistics
- Bot features
- GitHub project information

### Updating the Worker

To update your worker after making changes:

```bash
wrangler deploy
```

The update is instant with no downtime required.

### Cost

Cloudflare Workers free tier includes:
- 100,000 requests per day
- 10ms CPU time per request

For a typical Slack workspace, this is usually sufficient.

### Support

If you encounter issues:
1. Check the GitHub issues in this repository
2. Review the Cloudflare Workers documentation
3. Check the Slack API documentation

### Security Notes

- Never commit your secrets (SLACK_TOKEN, SIGNING_SECRET) to version control
- The worker verifies all requests from Slack using HMAC signature validation
- Replay attacks are prevented with timestamp validation
- All secrets are stored securely in Cloudflare encrypted storage

---

## 📜 License

This project is licensed under the **AGPL-3.0 License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [OWASP Foundation](https://owasp.org/) for supporting open-source security
- All our amazing [contributors](https://git.owaspblt.org/BLT/graphs/contributors)
- The OWASP Slack community for feedback and ideas

---

<div align="center">

**Made with 💚 by the [OWASP BLT Team](https://owasp.org/www-project-bug-logging-tool/)**

[![Join OWASP Slack](https://img.shields.io/badge/Join-OWASP_Slack-4A154B?style=for-the-badge&logo=slack)](https://owasp.org/slack/invite)
[![Star this repo](https://img.shields.io/badge/Star_this_Repo-⭐-yellow?style=for-the-badge)](https://git.owaspblt.org/BLT/BLT-Lettuce)

</div>
