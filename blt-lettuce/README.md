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

> **Note:** This Slack bot functionality has been incorporated into the main [BLT repository](https://github.com/OWASP-BLT/BLT) and is being transferred back to tgis repo for better organization.

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

The bot is powered by a **Python Cloudflare Worker** that:

- Handles Slack webhook events
- Sends personalized welcome messages
- Tracks statistics in KV storage
- Provides a stats API for the dashboard
- Caches project metadata (expires every 24-48 hours)

See [cloudflare-worker/README.md](cloudflare-worker/README.md) for setup instructions.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | Slack webhook for events |
| `/stats` | GET | Returns statistics JSON |
| `/health` | GET | Health check endpoint |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) for Cloudflare Workers
- Slack Bot Token and Signing Secret

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/OWASP-BLT/BLT-Lettuce.git
   cd BLT-Lettuce
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.sample .env
   # Edit .env with your Slack credentials
   ```

4. **Run locally**
   ```bash
   poetry run python app.py
   ```

### Deploy Cloudflare Worker

```bash
cd cloudflare-worker
wrangler login
wrangler kv:namespace create "STATS_KV"
# Update wrangler.toml with the namespace ID
wrangler secret put SLACK_TOKEN
wrangler secret put SIGNING_SECRET
wrangler deploy
```

---

## 📁 Project Structure

```
BLT-Lettuce/
├── app.py                  # Main Flask application
├── cloudflare-worker/      # Cloudflare Worker code
│   ├── worker.py           # Python worker implementation
│   ├── wrangler.toml       # Worker configuration
│   └── README.md           # Worker documentation
├── data/
│   ├── projects.json       # OWASP project metadata cache
│   └── repos.json          # Repository categorization
├── docs/
│   └── index.html          # GitHub Pages dashboard
├── src/lettuce/            # Bot plugins and modules
├── tests/                  # Test suite
├── pyproject.toml          # Poetry configuration
└── README.md               # This file
```

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
