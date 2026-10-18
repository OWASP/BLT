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

- **Real-Time Search** - Search repositories by name and description
- **Advanced Sorting** - Sort by stars, forks, issues, activity, and more
- **Smart Filtering** - Filter by programming language and topics
- **Dual Views** - Switch between table and card layouts
- **Dark Mode** - Full dark mode support
- **Responsive Design** - Works on all devices
- **Smart Preferences** - Remembers your settings

---

## 🏗️ Architecture

```
git.owaspblt.org (history?path=<folder>, issue and pull ledgers)
        |  scripts/generate_forge_data.py, daily in .forkmesh/blt-waypoint--build-site.yml
        v
Workers KV (forge_data.json)  --->  worker/index.js  --->  /forge_data.json (also /gitlab_data.json)
                                         |
public/ (index.html, issues.html, script.js, github_data.json, main_data.*)  <- static assets
```

### Tech Stack
- **Frontend:** HTML5, CSS3, JavaScript
- **Styling:** Tailwind CSS
- **Data:** JSON-based repository metadata
- **Hosting:** Cloudflare Worker with static assets; refreshed data in Workers KV

### How It Works
1. **Forge tab and issues page:** `scripts/generate_forge_data.py` reads, for each folder in
   `scripts/routing/projects.tsv`, the folder history (`history?path=<folder>`, paged back to 365
   days or `FORGE_HISTORY_PAGES` pages), the issue and pull request ledgers (attributed by label
   `<folder>` / `project:<folder>`, else title prefix `[<folder>]` / `<folder>:`) and
   `<folder>/.forkmesh/info.json` where present. It writes `public/forge_data.json`: commit counts
   for 30/90/365 days (bots excluded), last commit, distinct authors, 26 weekly counts, open issues
   and pull requests, README size and `wrangler.toml` presence. Stars, forks, languages, releases,
   tags, branches and sizes do not exist per folder; they are `null` and their columns are hidden
   on the Forge tab. `FORGE_BUDGET_SECONDS` (default 300) bounds a run; when it runs out nothing
   is written.
2. **Daily refresh, no commits:** `.forkmesh/blt-waypoint--build-site.yml` (06:29 UTC, and on
   changes to the generator) runs the generator in the runner checkout and writes
   `forge_data.json` to the Worker's KV namespace with `scripts/worker-data/kv-put.sh`.
   `worker/index.js` serves `/forge_data.json` (and the old `/gitlab_data.json` URL) from KV,
   falling back to the committed `public/forge_data.json`; everything else is a static asset.
3. **GitHub tab:** `public/github_data.json` is the archived GitHub record (URLs point at the
   forge folders; `python scripts/forge_urls.py public/github_data.json` rewrites any
   gitlab.com/owasp-blt URL).
4. **Main tab:** `main_data.csv`/`.js`/`.json` derive from `github_data.json` with
   `python scripts/generate_main_data.py`; commit them together (the tests check they are current).

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
python3 scripts/generate_main_data.py    # after editing public/github_data.json
../scripts/ci/test.sh blt-waypoint       # from the repo root: scripts/ci/test.sh blt-waypoint
```

Deploy with `scripts/deploy.sh blt-waypoint` from the repo root. The KV namespace
(`blt-waypoint-data`, binding `DATA`) is created by `scripts/worker-data/create-kv.sh`.

### Usage
- **Search:** Type in the search bar to find repositories
- **Sort:** Choose sorting option from dropdown
- **Filter:** Click language tags or use sidebar filters
- **Toggle View:** Switch between table and card layouts
- **Dark Mode:** Click the moon icon in header

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
