# BLT-OWASP-Projects

**Comprehensive dashboard for tracking and visualizing OWASP repositories and their statistics**

- **Repository**: [OWASP-BLT/BLT-OWASP-Projects](https://github.com/OWASP-BLT/BLT-OWASP-Projects)
- **Live Dashboards**:
    - [Full Project Matrix](https://owasp-blt.github.io/BLT-OWASP-Projects/index.html)
    - [Simplified Projects View](https://owasp-blt.github.io/BLT-OWASP-Projects/projects.html)
- **Language**: Python, HTML, JavaScript

---

## Overview

BLT-OWASP-Projects provides an automated system for monitoring OWASP project repositories, collecting their statistics, and presenting them through interactive web dashboards. It tracks 1000+ OWASP projects, automatically fetching repository data, commit information, and project metadata.

## Key Features

- **Automated Repository Discovery** — Automatically discovers and tracks all OWASP `www-project-*` repositories
- **Daily Updates** — GitHub Actions workflows run daily to keep data fresh
- **Interactive Dashboards** — Two web-based dashboards for exploring project data
- **Rich Metadata Tracking** — Stars, forks, issues, PRs, commit activity, releases, license, language, build status
- **Slack Notifications** — Get notified when new OWASP projects are detected

---

## Live Dashboards

| Dashboard | Description |
|-----------|-------------|
| **[Full Project Matrix](https://owasp-blt.github.io/BLT-OWASP-Projects/index.html)** | Comprehensive project data with 24+ sortable columns and search |
| **[Simplified Projects View](https://owasp-blt.github.io/BLT-OWASP-Projects/projects.html)** | Color-coded activity indicators, mobile-responsive, focused on core metrics |

---

## How It Works

### Automated Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `parse_repos.yml` | Daily at midnight UTC | Fetches all OWASP `www-project-*` repositories, sends Slack alerts for new ones |
| `fetch_repo_status.yml` | Daily at midnight UTC, on push | Fetches detailed statistics for all tracked projects |
| `sweep_repos.yml` | Scheduled or manual | Additional repository data collection |
| `scrape_github_links.yml` | Scheduled or manual | Extracts GitHub repository links from OWASP project pages |

### Data Files

| File | Description |
|------|-------------|
| `www_project_repos.json` | Basic repository information (name, URL, stars, forks, issues, timestamps) |
| `repo_status.json` | Detailed project and repository statistics (metadata, commit info, license, language) |
| `project_repos_links.json` | Maps OWASP project names to their associated GitHub repositories |

---

## Getting Started

### Prerequisites

- Python 3.x
- GitHub Personal Access Token (for API access)
- Slack Webhook URL (optional, for notifications)

### Setup

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT-OWASP-Projects.git
cd BLT-OWASP-Projects

# Install dependencies
pip install requests

# Configure environment variables (for GitHub Actions, set these as secrets)
# GITHUB_TOKEN - GitHub Personal Access Token
# ACCESS_TOKEN - Additional access token for API calls
# SLACK_WEBHOOK_URL - Slack webhook for notifications (optional)
```

### Local Development

```bash
# Fetch OWASP project repositories
export GITHUB_TOKEN="your_token_here"
python .github/scripts/main.py

# Fetch detailed repository status
export ACCESS_TOKEN="your_token_here"
python .github/scripts/fetch_repo_status.py
```

### Viewing the Dashboards

```bash
# Open the main dashboard
open index.html

# Or open the simplified view
open projects.html
```

---

## Dashboard Features

### Full Project Matrix (index.html)

- Sortable and searchable DataTable
- 24+ columns of project information
- Pagination (100 items per page)
- Direct links to project pages and repositories

### Simplified Dashboard (projects.html)

- Color-coded activity indicators (blue = old, red = recent)
- Mobile-responsive design
- Focus on core metrics (stars, forks, issues)
- Sortable by activity timestamps

---

## Project Structure

```
.
├── index.html                         # Main dashboard
├── projects.html                      # Simplified dashboard
├── repo_status.json                   # Detailed repository status data
├── www_project_repos.json             # Basic repository information
├── project_repos_links.json           # Project to repository mappings
└── .github/
    ├── workflows/
    │   ├── parse_repos.yml
    │   ├── fetch_repo_status.yml
    │   ├── sweep_repos.yml
    │   └── scrape_github_links.yml
    └── scripts/
        ├── main.py
        ├── fetch_repo_status.py
        ├── sweep.py
        └── scrape_github_links.py
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Commit and push
5. Open a Pull Request

**Areas for contribution:**

- Improve dashboard UI/UX
- Add new data visualizations
- Enhance data collection scripts
- Add documentation
- Add new metrics or filters
