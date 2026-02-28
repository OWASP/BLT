# BLT-GitHub-App

A GitHub App that integrates [OWASP BLT](https://owaspblt.org) services into GitHub repositories.

## Features

- **`/assign` command** — Comment `/assign` on any issue to be automatically assigned to it. Assignments expire after 24 hours if no linked PR is submitted.
- **`/unassign` command** — Comment `/unassign` to release an issue assignment so others can pick it up.
- **BLT bug reporting** — When an issue is labeled as `bug`, `vulnerability`, or `security`, it is automatically reported to the [BLT API](https://github.com/OWASP-BLT/BLT-API).
- **Welcome messages** — New issues and pull requests receive helpful onboarding messages with contribution tips.
- **Merge congratulations** — Merged PRs receive an acknowledgement message celebrating the contributor's work.

## Setup

### Prerequisites

- Node.js 18 or higher
- A GitHub App (see [Probot docs](https://probot.github.io/docs/development/))

### Installation

```bash
git clone https://github.com/OWASP-BLT/BLT-GitHub-App.git
cd BLT-GitHub-App
npm install
```

### Configuration

Copy `.env.example` to `.env` and fill in your GitHub App credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `APP_ID` | Your GitHub App's ID |
| `PRIVATE_KEY` | Your GitHub App's private key (PEM format) |
| `WEBHOOK_SECRET` | Your GitHub App's webhook secret |
| `GITHUB_CLIENT_ID` | OAuth client ID (optional) |
| `GITHUB_CLIENT_SECRET` | OAuth client secret (optional) |
| `BLT_API_URL` | BLT API base URL (default: `https://blt-api.owasp-blt.workers.dev`) |

### Running

```bash
npm start
```

### Testing

```bash
npm test
```

## GitHub App Permissions

The app requires the following repository permissions:

| Permission | Access |
|---|---|
| Issues | Read & Write |
| Pull Requests | Read & Write |
| Metadata | Read |

And listens for these webhook events: `issue_comment`, `issues`, `pull_request`.

## Usage

### Issue Assignment

In any issue, comment:

```
/assign
```

You will be assigned to the issue with a 24-hour deadline to submit a pull request.

To release an issue:

```
/unassign
```

### Bug Reporting

When an issue is labeled with `bug`, `vulnerability`, or `security`, the app automatically creates a corresponding entry in the BLT platform and posts the Bug ID as a comment.

## Cloudflare Worker (Python)

A Python port of the app is available in the `cloudflare-worker/` directory.
It runs as a [Cloudflare Workers](https://workers.cloudflare.com/) Python Worker
and includes a **landing homepage** where users can view the app status and
install it on their own GitHub organization.

### Quick start

```bash
cd cloudflare-worker
cp .dev.vars.example .dev.vars   # fill in your credentials
npx wrangler dev                 # local dev server
npx wrangler deploy              # deploy to Cloudflare
```

### Cloudflare environment variables

| Variable | Description |
|---|---|
| `APP_ID` | GitHub App numeric ID |
| `PRIVATE_KEY` | GitHub App private key (PEM, PKCS#1 or PKCS#8) |
| `WEBHOOK_SECRET` | GitHub App webhook secret |
| `GITHUB_APP_SLUG` | GitHub App URL slug (e.g. `blt-github-app`) |
| `BLT_API_URL` | BLT API base URL (default: `https://blt-api.owasp-blt.workers.dev`) |
| `GITHUB_CLIENT_ID` | OAuth client ID (optional) |
| `GITHUB_CLIENT_SECRET` | OAuth client secret (optional) |

Set secrets securely:
```bash
npx wrangler secret put APP_ID
npx wrangler secret put PRIVATE_KEY
npx wrangler secret put WEBHOOK_SECRET
```

### Landing page

The worker serves a landing page at `/` showing:
- Live operational status
- Feature overview
- A one-click **"Add to GitHub Organization"** button

### Python tests

```bash
pip install pytest
pytest cloudflare-worker/test_worker.py -v
```

### Cloudflare Worker endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/health` | JSON health check |
| `POST` | `/api/github/webhooks` | GitHub webhook receiver |
| `GET` | `/callback` | Post-installation success page |

## Project Structure

```
├── index.js                      # Main Probot app entry point
├── src/
│   ├── blt-api.js                # BLT API client
│   └── handlers/
│       ├── issue-assign.js       # /assign and /unassign command handlers
│       ├── issue-opened.js       # New issue and label handlers
│       └── pull-request.js      # PR opened/closed handlers
├── test/                         # Jest test suite
├── cloudflare-worker/
│   ├── worker.py                 # Python Cloudflare Worker (all handlers + landing page)
│   ├── wrangler.toml             # Cloudflare Worker configuration
│   ├── .dev.vars.example         # Local dev environment variables template
│   └── test_worker.py            # pytest unit tests for pure-Python utilities
├── app.yml                       # GitHub App manifest
├── .env.example                  # Environment variable template (Node.js)
└── package.json
```

## Related Projects

- [OWASP BLT](https://github.com/OWASP-BLT/BLT) — Main bug logging platform
- [BLT-Action](https://github.com/OWASP-BLT/BLT-Action) — GitHub Action for issue assignment
- [BLT-API](https://github.com/OWASP-BLT/BLT-API) — REST API for BLT

## License

[AGPL-3.0](LICENSE)

