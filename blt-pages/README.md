# OWASP BLT — Bug Reporting Platform

[![OWASP](https://img.shields.io/badge/OWASP-Project-blue?logo=owasp)](https://owasp.org/www-project-bug-logging-tool/)
[![License: AGPLv3](https://img.shields.io/badge/License-AGPL_v3-red.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![GitHub Pages](https://img.shields.io/badge/Deployed-GitHub_Pages-222?logo=github)](https://owasp-blt.github.io/BLT-Pages/)

Community-powered bug-reporting platform built on GitHub Pages, part of the
[OWASP Bug Logging Tool (BLT)](https://owasp.org/www-project-bug-logging-tool/) project.

---

## Features

| Feature | Description |
|---|---|
| 🐛 **Public bug reports** | 404/500 errors, functional, performance, typos, design, IP violations |
| 🕶️ **Anonymous reporting** | Submit via [BLT-API](https://blt.owasp.org/api) — no GitHub account required |
| 🔒 **Security vulnerabilities** | Zero-log, zero-tracking via [BLT-Zero](https://zero.owaspblt.org) |
| 🏆 **Leaderboard** | Auto-updated every 6 h by GitHub Actions |

---

## Tech Stack

- **Pure HTML + Tailwind CSS** (CDN) — no build step
- **Font Awesome** (CDN)
- **GitHub Actions** for leaderboard generation
- **BLT-API** for anonymous report submission

---

## Local Development

No build step required — open the HTML files directly in a browser, or use any
static file server:

```bash
# Python
python -m http.server 8080

# Node
npx serve .
```

---

## GitHub Actions

| Workflow | Trigger | Purpose |
|---|---|---|
| `update-leaderboard.yml` | Schedule (6 h) · issue events · manual | Regenerates `data/leaderboard.json` from all `bug`-labelled issues |

---

## Issue Template

Bug reports use the structured YAML template at
[`.github/ISSUE_TEMPLATE/bug_report.yml`](.github/ISSUE_TEMPLATE/bug_report.yml).
Fields include `title`, `link`, `LOGO_URL`, and `ORG_NAME` so the template is
generic and reusable across forks.

---

## License

[GNU Affero General Public License v3.0](LICENSE) — OWASP Foundation &amp; BLT Contributors.
