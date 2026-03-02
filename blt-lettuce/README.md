<div align="center">

# 🥬 BLT-Lettuce

**An intelligent Slack bot for the OWASP community**

[![License](https://img.shields.io/github/license/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=blue)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=yellow)](https://github.com/OWASP-BLT/BLT-Lettuce/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=green)](https://github.com/OWASP-BLT/BLT-Lettuce/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=red)](https://github.com/OWASP-BLT/BLT-Lettuce/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=purple)](https://github.com/OWASP-BLT/BLT-Lettuce/pulls)

[![Contributors](https://img.shields.io/github/contributors/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=orange)](https://github.com/OWASP-BLT/BLT-Lettuce/graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=cyan)](https://github.com/OWASP-BLT/BLT-Lettuce/commits/main)
[![Commit Activity](https://img.shields.io/github/commit-activity/m/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=pink)](https://github.com/OWASP-BLT/BLT-Lettuce/pulse)
[![Repo Size](https://img.shields.io/github/repo-size/OWASP-BLT/BLT-Lettuce?style=for-the-badge&color=gray)](https://github.com/OWASP-BLT/BLT-Lettuce)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare_Workers-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://workers.cloudflare.com/)
[![Slack](https://img.shields.io/badge/Slack_API-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://api.slack.com/)

[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=flat-square&logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square)](https://github.com/astral-sh/ruff)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg?style=flat-square)](https://conventionalcommits.org)

[📊 **Live Dashboard**](https://owasp-blt.github.io/BLT-Lettuce/) · [💬 **Join OWASP Slack**](https://owasp.org/slack/invite) · [🐛 **Report Bug**](https://github.com/OWASP-BLT/BLT-Lettuce/issues/new?template=bug_report.md) · [✨ **Request Feature**](https://github.com/OWASP-BLT/BLT-Lettuce/issues/new?template=feature_request.md)

</div>

---

## 📖 About

BLT-Lettuce is an intelligent Slack bot designed for the OWASP Slack workspace. It welcomes new members, helps them discover projects, and connects the global security community.

> **Note:** This Slack bot functionality has been incorporated into the main [BLT repository](https://github.com/OWASP-BLT/BLT) and is being transferred back to this repo for better organization.

### 🎯 Core Features

- **👋 Welcome New Members** - Automatically sends personalized welcome messages to newcomers
- **🔍 Project Discovery** - Interactive conversations help users find relevant OWASP projects
- **📊 GitHub Integration** - Scans configured organizations and caches project metadata
- **🤖 Conversational Flow** - Asks multiple-choice questions to understand user needs
- **⚡ Edge-Powered** - Runs on Cloudflare Workers for global, low-latency performance

---

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
└─────────────────────────────────┬───────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cloudflare    │    │    GitHub API   │    │   GitHub Pages  │
│   KV Storage    │    │  (Org scanning) │    │  (Dashboard)    │
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

## 📊 Live Dashboard

View real-time statistics at our **[Stats Dashboard](https://owasp-blt.github.io/BLT-Lettuce/)**:

- 👋 Members welcomed
- ⚡ Commands executed
- 🐙 GitHub project health metrics
- 🌍 Global availability status

---

## ☁️ Cloudflare Worker

BLT-Lettuce is now **fully powered by a Cloudflare Python Worker** (`src/worker.py`) that serves as the complete backend:

- **Homepage**: Serves the dashboard at the root URL
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
| `/` | GET | Homepage dashboard |
| `/webhook` | POST | Slack webhook for events |
| `/stats` | GET | Returns statistics JSON |
| `/health` | GET | Health check endpoint |

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

---

## 🚀 Quick Start

### Prerequisites

- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) for Cloudflare Workers
- Cloudflare account
- Slack Bot Token and Signing Secret

### Deploy to Cloudflare Workers

1. **Clone the repository**
   ```bash
   git clone https://github.com/OWASP-BLT/BLT-Lettuce.git
   cd BLT-Lettuce
   ```

2. **Install Wrangler and login**
   ```bash
   npm install -g wrangler
   wrangler login
   ```

3. **Create KV namespace**
   ```bash
   wrangler kv:namespace create "STATS_KV"
   # Copy the namespace ID and update it in wrangler.toml
   ```

4. **Set up secrets**
   ```bash
   wrangler secret put SLACK_TOKEN       # Your Bot User OAuth Token
   wrangler secret put SIGNING_SECRET    # Your Signing Secret
   ```

5. **Deploy the worker**
   ```bash
   wrangler deploy
   ```

6. **Configure Slack App**
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
│   └── index.html          # GitHub Pages dashboard (reference)
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

## 📜 License

This project is licensed under the **AGPL-3.0 License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [OWASP Foundation](https://owasp.org/) for supporting open-source security
- All our amazing [contributors](https://github.com/OWASP-BLT/BLT-Lettuce/graphs/contributors)
- The OWASP Slack community for feedback and ideas

---

<div align="center">

**Made with 💚 by the [OWASP BLT Team](https://owasp.org/www-project-bug-logging-tool/)**

[![Join OWASP Slack](https://img.shields.io/badge/Join-OWASP_Slack-4A154B?style=for-the-badge&logo=slack)](https://owasp.org/slack/invite)
[![Star this repo](https://img.shields.io/badge/Star_this_Repo-⭐-yellow?style=for-the-badge)](https://github.com/OWASP-BLT/BLT-Lettuce)

</div>
