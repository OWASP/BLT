# OWASP BLT — Bug Reporting Platform

[![OWASP](https://img.shields.io/badge/OWASP-Project-blue?logo=owasp)](https://owasp.org/www-project-bug-logging-tool/)
[![License: AGPLv3](https://img.shields.io/badge/License-AGPL_v3-red.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Cloudflare](https://img.shields.io/badge/Deployed-Cloudflare-F38020?logo=cloudflare)](https://pages.owaspblt.org/)

Community-powered bug-reporting platform hosted from `public/` on Cloudflare, part of the
[OWASP Bug Logging Tool (BLT)](https://owasp.org/www-project-bug-logging-tool/) project.

---

## Features

| Feature | Description |
|---|---|
| 🐛 **Public bug reports** | 404/500 errors, functional, performance, typos, design, IP violations |
| 🕶️ **Anonymous reporting** | Submit via [BLT-API](https://blt.owasp.org/api) — no GitLab account required |
| 🔒 **Security vulnerabilities** | Zero-log, zero-tracking via [BLT-Zero](https://zero.owaspblt.org) |
| 🏆 **Leaderboard** | Generated from GitLab issues |

---

## Tech Stack

- **Pure HTML + Tailwind CSS** (CDN) — no build step
- **Font Awesome** (CDN)
- **GitLab CI** for tests and leaderboard generation
- **Cloudflare Workers Static Assets** serving `public/`
- **BLT-API** for anonymous report submission

---

## Local Development

No build step required — open the HTML files directly in a browser, or use any
static file server:

```bash
# Python
python -m http.server 8080 --directory public

# Node
npx serve public
```

---

## GitLab CI

| Workflow | Trigger | Purpose |
|---|---|---|
| `.gitlab-ci.yml` | Push · schedule · manual | Runs tests and regenerates `public/data/leaderboard.json` from all `bug`-labelled GitLab issues |

---

## Issue Template

Bug reports use the GitLab issue template at
[`.gitlab/issue_templates/Bug.md`](.gitlab/issue_templates/Bug.md).

---

## License

[GNU Affero General Public License v3.0](LICENSE) — OWASP Foundation &amp; BLT Contributors.
