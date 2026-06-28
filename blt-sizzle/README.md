# 🔥 BLT Sizzle — Async Daily Check-in App

<div align="center">

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://gitlab.com/owasp-blt/blt-sizzle)
[![License](https://img.shields.io/badge/license-OWASP%20BLT-blue.svg)](#-license)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-orange.svg)](https://workers.cloudflare.com/)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)

**A lightweight, secure, async-first daily check-in app built on Cloudflare Workers.**  
Track progress, surface blockers, and keep your team aligned — without another meeting.

</div>

---

## Table of Contents

- [Features](#-features)
- [Quick Deploy](#-quick-deploy)
- [Setup](#️-setup)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Endpoints](#-api-endpoints)
- [Architecture](#️-architecture)
- [Database Schema](#-database-schema)
- [Security](#-security)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [Roadmap](#️-roadmap)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📝 **Daily Check-ins** | Document previous work, today's plan, and blockers |
| 😊 **Mood Tracking** | Express how you're feeling with emoji selections |
| 🔁 **Auto Pre-fill** | Yesterday's plans automatically populate as today's accomplished work |
| 💬 **Slack Integration** | Daily reminders via Slack with a direct link to your check-in form |
| 📧 **Email Reminders** | Optional email notifications (SendGrid, Mailgun, AWS SES, Postmark) |
| 🔒 **Encrypted Storage** | Sensitive data encrypted before storage in Cloudflare D1 |
| ⏰ **Customizable Notifications** | Set preferred reminder time and timezone |

> **⚠️ Security Note:** The current implementation uses base64 encoding as a placeholder for encryption.
> For production use with sensitive data, implement proper AES-GCM encryption via the Web Crypto API.

---

## 🚀 Quick Deploy

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://gitlab.com/owasp-blt/blt-sizzle)

---

## 🛠️ Setup

### Prerequisites

- [Cloudflare Account](https://dash.cloudflare.com/sign-up) (free tier works)
- [Node.js](https://nodejs.org/) 16.13 or later
- Git

### Steps

```bash
# 1. Install Wrangler
npm install

# 2. Authenticate
npx wrangler login

# 3. Create D1 database
npm run db:create
# Copy the database ID into wrangler.toml under [[d1_databases]]

# 4. Initialize schema
npm run db:init

# 5. Set encryption key (production)
openssl rand -base64 32
npx wrangler secret put ENCRYPTION_KEY

# Or for development, add to wrangler.toml:
# [vars]
# ENCRYPTION_KEY = "your-generated-key"

# 6. (Optional) Create KV namespace for session storage
npx wrangler kv:namespace create "KV"
# Copy the ID into wrangler.toml under [[kv_namespaces]]

# 7. Deploy
npm run deploy
```

App will be live at `https://blt-sizzle-checkin.your-subdomain.workers.dev`.

### Local Development

```bash
npm run dev   # http://localhost:8787
npm run tail  # stream live logs
npm run db:query "SELECT * FROM users LIMIT 5"
```

### Multiple Environments

Create `wrangler.dev.toml` / `wrangler.staging.toml` with environment-specific values, then:

```bash
npx wrangler deploy --config wrangler.dev.toml
npx wrangler deploy --config wrangler.staging.toml
npx wrangler deploy  # production
```

### CI/CD (GitHub Actions)

```yaml
- name: Deploy to Cloudflare Workers
  run: npx wrangler deploy
  env:
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

---

## 🔧 Configuration

### Environment Variables

| Variable | How to set | Description |
|---|---|---|
| `ENCRYPTION_KEY` | `wrangler secret put` | Required. Encrypts stored data |
| `EMAIL_API_KEY` | `wrangler secret put` | Email service API key |
| `EMAIL_FROM` | `wrangler.toml [vars]` | Sender email address |
| `EMAIL_PROVIDER` | `wrangler.toml [vars]` | `sendgrid` or `mailgun` |
| `WORKER_HOST` | `wrangler.toml [vars]` | Deployed worker URL |

Always use `wrangler secret put` for sensitive values in production — never commit them to `wrangler.toml`.

### Scheduled Notifications

Add a cron trigger to `wrangler.toml`:

```toml
[triggers]
crons = ["0 9 * * *"]  # 9 AM UTC daily; worker checks per-user timezones
```

### Custom Domain

```toml
routes = [
  { pattern = "checkin.yourdomain.com", custom_domain = true }
]
```

### Slack Integration

1. Create an [Incoming Webhook](https://api.slack.com/messaging/webhooks) in your Slack workspace
2. In the app, go to **Settings**, paste the URL, set notification time/timezone, then click **Test**

---

## 📱 Usage

1. Visit your deployed app URL
2. Fill out the daily form:
   - **Previous Work** — auto-filled from last check-in
   - **Today's Plan** — required
   - **Blockers** — optional
   - **Mood** — emoji picker
3. Submit — done! ✅

---

## 🛣️ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Main check-in form |
| `GET` | `/settings` | Notification settings page |
| `POST` | `/api/checkin` | Submit a check-in |
| `GET` | `/api/checkin/latest` | Get latest check-in (for pre-fill) |
| `GET` | `/api/settings` | Get user settings |
| `POST` | `/api/settings` | Save user settings |
| `POST` | `/api/notification/test` | Send a test notification |

---

## 🏗️ Architecture

```
User Browser (HTML/CSS/JS)
        │
        ▼
Cloudflare Worker (Python — workers/main.py)
        │
        ├──────────────────────┐
        ▼                      ▼
D1 Database (SQLite)    External APIs
  ├─ users               ├─ Slack Webhooks
  └─ checkins            ├─ SendGrid
                         └─ Mailgun
```

**Stack:**
- **Frontend**: Semantic HTML5, CSS3 (gradients, flexbox), Vanilla ES6+ JS, localStorage, Fetch API
- **Backend**: Python on Cloudflare Workers, async/await, D1 (SQLite), Cron Triggers
- **Infrastructure**: Cloudflare Workers (serverless), D1 Database, optional KV Namespace

---

## 📊 Database Schema

### Users

| Column | Description |
|---|---|
| `user_id` | Unique identifier (generated client-side) |
| `email` | Optional email for notifications |
| `slack_webhook_url` | Encrypted Slack webhook URL |
| `notification_time` | Preferred reminder time (HH:MM) |
| `timezone` | User's timezone |
| `email_notifications` | 0 or 1 |

### Check-ins

| Column | Description |
|---|---|
| `user_id` | FK → users |
| `encrypted_previous_work` | Encrypted previous accomplishments |
| `encrypted_today_plan` | Encrypted today's plans |
| `encrypted_blockers` | Encrypted blockers/challenges |
| `mood` | Emoji |
| `checkin_date` | Date of check-in |

---

## 🔒 Security

### What's implemented
- Encryption key required at startup — no fallback
- All check-in content encrypted at rest
- Parameterized queries (SQL injection protection)
- HTTPS enforced by Cloudflare
- Rate limiting by Cloudflare
- Slack webhook URLs stored encrypted, never exposed in responses

### Known limitations (production hardening needed)
- **Encryption**: Current implementation uses base64 + IV, not true AES-GCM. For production, use the Web Crypto API:
  ```python
  from js import crypto
  iv = crypto.getRandomValues(bytearray(12))
  encrypted = await crypto.subtle.encrypt({"name": "AES-GCM", "iv": iv}, crypto_key, data)
  ```
- **Authentication**: User IDs are stored in `localStorage` — no password/SSO. Clearing browser data creates a new user (by design).
- **No CSRF protection** — no session-based auth currently.

### Recommended production hardening
- Implement AES-GCM via Web Crypto API
- Add OAuth (Cloudflare Access, Google, GitHub) or JWT
- Add per-user rate limiting and audit logging
- Add GDPR endpoints: `GET /api/user/export`, `DELETE /api/user/delete`
- Implement data retention policies

### Routine maintenance
- **Weekly**: Review Worker logs for anomalies
- **Monthly**: Update dependencies (`npm update`, `wrangler update`), rotate encryption keys
- **Quarterly**: Full security audit, penetration testing

### Vulnerability reporting
Email **security@owasp.org** with description, reproduction steps, impact, and suggested fix. Do not publish publicly.

---

## 🧪 Testing

### Manual testing

```bash
npm run dev  # start local server at http://localhost:8787

# Submit a check-in
curl -X POST http://localhost:8787/api/checkin \
  -H "Content-Type: application/json" \
  -d '{"userId":"test_user","previousWork":"x","todayPlan":"y","blockers":"","mood":"😊"}'

# Retrieve latest
curl "http://localhost:8787/api/checkin/latest?userId=test_user"

# Save settings
curl -X POST http://localhost:8787/api/settings \
  -H "Content-Type: application/json" \
  -d '{"userId":"test_user","email":"test@example.com","notificationTime":"09:00","timezone":"UTC","slackWebhookUrl":"","emailNotifications":0}'
```

### Automated tests

```bash
pip install requests
# Start server first, then:
python tests/test_api.py
```

### Database inspection

```bash
npx wrangler d1 execute checkin-db --command "SELECT * FROM checkins ORDER BY created_at DESC LIMIT 10"
npx wrangler d1 execute checkin-db --command "SELECT name FROM sqlite_master WHERE type='table'"
```

---

## 🤝 Contributing

Contributions are welcome! Please follow the OWASP Code of Conduct.

### Workflow

1. Fork the repo and clone your fork
2. Add upstream: `git remote add upstream https://gitlab.com/owasp-blt/blt-sizzle.git`
3. Create a branch: `git checkout -b feature/your-feature` or `fix/bug-description`
4. Make changes, test thoroughly, then open a merge request

### Code style

- **Python**: PEP 8, async/await, snake_case
- **JavaScript**: ES6+, `const`/`let`, async/await, no frameworks
- **HTML/CSS**: Semantic HTML5, BEM class naming, CSS variables, responsive design

### PR checklist

- [ ] Code follows style guidelines
- [ ] Tests pass (`python tests/test_api.py`)
- [ ] Documentation updated
- [ ] Clear commit messages

### Bug reports & feature requests

Open a GitHub issue with: a clear title, description, reproduction steps (bugs) or use case and proposed solution (features).

---

## 🗺️ Roadmap

Contributions welcome!

- [ ] 🔄 **Async Check-ins** — Post updates whenever it suits you; no synchronised schedules
- [ ] 🤖 **AI Summaries** — Auto-summarise updates daily/weekly, highlight wins and blockers
- [ ] 👥 **Per-group Summaries** — Team/role-specific insights (engineering vs design, etc.)
- [ ] 🏠 **Persistent Rooms** — Always-open rooms for async updates with browsable history
- [ ] 🖼️ **Rich Media** — Images, GIFs, short videos alongside text
- [ ] 🎨 **Custom Prompts** — Admin-defined check-in questions with colour/emoji coding
- [ ] 💬 **Comments & Reactions** — Async reactions and threaded comments on updates
- [ ] 📦 **Bulk Export** — CSV, JSON, or PDF export for reporting
- [ ] 🎥 **Video/Voice Updates** — Optional short audio/video clips
- [ ] 🔗 **Project Tool Integrations** — GitHub, Jira, Trello task linking
- [ ] 🌟 **Mood Tracking & Kudos** — Peer recognition and icebreakers
- [ ] 🌍 **Timezone-aware Scheduling** — Respect each member's local time
- [ ] 🏃 **Agile Templates** — Scrum, Kanban, retrospective support
- [ ] 🔐 **Private Check-ins** — Team-visible vs manager-only updates
- [ ] 📈 **Participation Analytics** — Engagement tracking and follow-up stats
- [ ] 🆓 **Free-tier Limits** — Configurable caps for open-source/free plans

---

## 🐛 Troubleshooting

<details>
<summary><strong>Database not initializing</strong></summary>

Ensure the D1 database is created and the ID is correct in `wrangler.toml`, then re-run:
```bash
npm run db:init
```
</details>

<details>
<summary><strong>Slack notifications not working</strong></summary>

Test the webhook directly:
```bash
curl -X POST -H 'Content-Type: application/json' -d '{"text":"Test"}' YOUR_WEBHOOK_URL
```
Then check Worker logs: `npm run tail`
</details>

<details>
<summary><strong>Data not persisting</strong></summary>

Check the D1 binding in `wrangler.toml` and verify schema was applied:
```bash
npm run db:query "SELECT name FROM sqlite_master WHERE type='table'"
```
</details>

---

##  License

This project is part of [OWASP BLT](https://gitlab.com/owasp-blt) and follows the same license terms.

---

<div align="center">Made with ❤️ by <a href="https://gitlab.com/owasp-blt">OWASP BLT</a></div>
