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
├── app.yml                       # GitHub App manifest
├── .env.example                  # Environment variable template
└── package.json
```

## Related Projects

- [OWASP BLT](https://github.com/OWASP-BLT/BLT) — Main bug logging platform
- [BLT-Action](https://github.com/OWASP-BLT/BLT-Action) — GitHub Action for issue assignment
- [BLT-API](https://github.com/OWASP-BLT/BLT-API) — REST API for BLT

## License

[AGPL-3.0](LICENSE)

