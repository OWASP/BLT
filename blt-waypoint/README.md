# OWASP BLT Organization Dashboard

**Live Site:** [https://waypoint.owaspblt.org/](https://waypoint.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/tree/main/blt-waypoint](https://git.owaspblt.org/BLT/tree/main/blt-waypoint)

A live interactive dashboard of the OWASP BLT projects. Every project is a folder of the
[git.owaspblt.org/BLT](https://git.owaspblt.org/BLT) monorepo; the dashboard shows each folder's
commits, issues, pull requests and live site, plus the archived GitHub record.

**Live Demo:** [waypoint.owaspblt.org](https://waypoint.owaspblt.org/)

---

## About OWASP BLT

**OWASP BLT (Bug Logging Tool)** is a community-driven OWASP Foundation project that develops open-source tools for structured vulnerability reporting, bug tracking, security automation, and contributor engagement. 

The BLT ecosystem includes:
- Core platform for bug discovery and reporting
- REST API for integration
- Mobile app (Flutter)
- Browser extension for Chrome
- Slack bot for team collaboration
- Various security and automation tools

All projects are developed transparently under OWASP governance with AGPL-3.0 licensing.

---

## ✨ Features

- **Dashboard:** every project folder with its live site, last commit and 26-week activity,
  commits in the last 30 days and year, open issues and pull requests. Search, sort and filter
  by status (active, quiet, dormant), live site, open issues or pull requests; table or cards.
- **Issues:** every open issue on the forge, by project, with labels, author, age and comments.
  Search, filter by project or label, and group by project.
- **Screenshots:** a daily capture of each live site.
- Light and dark, works on phones, and the filters are in the address bar so views can be shared.

---

## 🏗️ Architecture

```
git.owaspblt.org (history?path=<folder>, issue and pull ledgers)   Cloudflare (Workers custom domains)
        |  scripts/generate_forge_data.py + scripts/live_sites.py, daily 06:29 UTC (build-site)
        v
Workers KV  forge_data.json  ------------------------------->  /forge_data.json (also /gitlab_data.json)
            screenshots/<folder>.jpg, screenshots/index.json -->  /screenshots/*   (worker/index.js)
        ^
        |  scripts/capture_screenshots.py (Cloudflare Browser Rendering), daily 07:00 UTC (screenshots)
public/ (index.html, issues.html, screenshots.html, script.js, styles.css)  <- static assets
```

### How It Works
1. **Project data:** `scripts/generate_forge_data.py` reads, for each folder in
   `scripts/routing/projects.tsv`, the folder history (`history?path=<folder>`, paged back to 365
   days or `FORGE_HISTORY_PAGES` pages), the issue and pull request ledgers (attributed by label
   `<folder>` / `project:<folder>`, else title prefix `[<folder>]` / `<folder>:`) and
   `<folder>/.forkmesh/info.json` where present. It writes `public/forge_data.json`: commit counts
   for 30/90/365 days (bots excluded), last commit, distinct authors, 26 weekly counts, open issues
   and pull requests, README size and the live site (`live_url`). `FORGE_BUDGET_SECONDS` (default
   300) bounds a run; when it runs out nothing is written.
2. **Live sites:** `scripts/live_sites.py` maps each folder's Worker (the `name` in its
   `wrangler.toml`) to its custom domain using Cloudflare's Workers domain list, falling back to
   `custom_domain` routes in the `wrangler.toml`.
3. **Daily refresh, no commits:** `.forkmesh/blt-waypoint--build-site.yml` (06:29 UTC, and on
   changes to the generator) writes `forge_data.json` to the Worker's KV namespace with
   `scripts/worker-data/kv-put.sh`. `.forkmesh/blt-waypoint--screenshots.yml` (07:00 UTC) reads
   that data, captures each live site at 1280x800 with Cloudflare Browser Rendering
   (`scripts/capture_screenshots.py`, about 15 s per site) and writes the JPEGs and
   `screenshots/index.json` to KV. A site that fails keeps the previous day's image.
   `worker/index.js` serves both from KV; `/forge_data.json` falls back to the committed copy.
4. **Archive:** `data/github_archive.json` is the archived GitHub record. It is not served; the
   generator only uses it for descriptions a folder's `info.json` does not give.

## 🚀 Quick Start

### Clone & Run Locally

```bash
git clone https://git.owaspblt.org/BLT.git
cd blt-waypoint

# Start a local server
python -m http.server 8000 -d public
# Open http://localhost:8000
```

### Data and tests

```bash
python3 scripts/generate_forge_data.py   # live, read-only: about 200 anonymous requests
python3 scripts/capture_screenshots.py   # needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID
../scripts/ci/test.sh blt-waypoint       # from the repo root: scripts/ci/test.sh blt-waypoint
```

Deploy with `scripts/deploy.sh blt-waypoint` from the repo root. The KV namespace
(`blt-waypoint-data`, binding `DATA`) is created by `scripts/worker-data/create-kv.sh`.

---

## 🤝 Contributing

We welcome contributions! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Commit (`git commit -m "feat: add feature"`)
5. Push and create a Pull Request

---

## 💬 Community

- 🌐 **Website:** [owaspblt.org](https://owaspblt.org)
- 💬 **Slack:** [Join OWASP Slack](https://owasp.org/slack/invite)
- 📧 **Issues:** [git.owaspblt.org issues](https://git.owaspblt.org/BLT/issues?label=blt-waypoint)

---

## 📄 License

AGPL-3.0 - See [LICENSE](LICENSE) for details

<p align="center">Made with ❤️ by the OWASP BLT Community</p>
