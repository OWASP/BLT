# OWASP BLT Organization Dashboard

A live interactive dashboard for exploring OWASP-BLT GitHub and GitLab repositories, migration progress, and repository statistics.

**Live Demo:** [github.owaspblt.org](http://github.owaspblt.org/)

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
┌──────────────────────────────────────────────────────┐
│                GitHub API / GitLab API               │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│      github_data.json / gitlab_data.json             │
└────────────────────────┬─────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐   ┌──────────┐   ┌────────────┐
    │index.html   │script.js │   │styles.css  │
    └─────────┘   └──────────┘   └────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
         ┌──────────────────────────────┐
         │   Interactive Dashboard      │
         │  (Table/Card Views, Search,  │
         │   Sort, Filter, Dark Mode)   │
         └──────────────────────────────┘
```

### Tech Stack
- **Frontend:** HTML5, CSS3, JavaScript
- **Styling:** Tailwind CSS
- **Data:** JSON-based repository metadata
- **Hosting:** Cloudflare Pages

### How It Works
1. Data is generated from the GitHub and GitLab APIs in GitLab CI
2. Repository statistics are compiled into `github_data.json` and `gitlab_data.json`
3. JavaScript dynamically renders the dashboard
4. GitLab CI refreshes the committed `public/` data files and deploys `public/` to Cloudflare Pages
5. Users can search, sort, and filter in real-time

---

## 🚀 Quick Start

### Clone & Run Locally

```bash
git clone https://gitlab.com/owasp-blt/blt-waypoint.git
cd blt-waypoint

# Start a local server
python -m http.server 8000 -d public
# Open http://localhost:8000
```

### GitLab Build, Cloudflare Hosting

GitLab builds the static site with:

```bash
sh scripts/build_static.sh
```

The committed Pages output directory is `public/`. The GitLab pipeline refreshes the data files there, keeps that folder as a short-lived build artifact, then deploys it to Cloudflare Pages with:

```bash
npx --yes wrangler pages deploy public --project-name "$CLOUDFLARE_PROJECT_NAME" --branch "$CI_COMMIT_BRANCH"
```

Set `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in GitLab CI/CD variables, and configure a GitLab pipeline schedule for the daily refresh.

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
- 📧 **Issues:** [GitLab Issues](https://gitlab.com/owasp-blt/blt-waypoint/-/issues)

---

## 📄 License

AGPL-3.0 - See [LICENSE](LICENSE) for details

<p align="center">Made with ❤️ by the OWASP BLT Community</p>
