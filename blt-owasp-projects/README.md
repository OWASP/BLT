# OWASP Projects Dashboard 🛡️

A comprehensive dashboard for tracking and visualizing OWASP (Open Web Application Security Project) repositories and their statistics.

## 📊 Overview

This project provides an automated system for monitoring OWASP project repositories, collecting their statistics, and presenting them through interactive web dashboards. It tracks over 1000+ OWASP projects, automatically fetching repository data, commit information, and project metadata.

## ✨ Features

- **Automated Repository Discovery**: Automatically discovers and tracks all OWASP `www-project-*` repositories
- **Daily Updates**: GitHub Actions workflows run daily to keep repository data fresh
- **Interactive Dashboards**: Two web-based dashboards for exploring project data:
  - `index.html` - Comprehensive project matrix with detailed statistics
  - `projects.html` - Simplified view with core metrics and color-coded activity
- **Rich Metadata**: Tracks project information including:
  - Repository statistics (stars, forks, issues, PRs)
  - Commit activity and release information
  - Project metadata (level, type, region, pitch)
  - License and language information
  - Build status and GitHub status
- **Slack Notifications**: Get notified when new OWASP projects are detected

## 🌐 Live Dashboards

- **Full Project Matrix**: [index.html](https://owasp-blt.github.io/BLT-OWASP-Projects/index.html)
- **Simplified Projects View**: [projects.html](https://owasp-blt.github.io/BLT-OWASP-Projects/projects.html)

## 📁 Project Structure

```
.
├── index.html                    # Main dashboard with comprehensive project data
├── projects.html                 # Simplified dashboard with color-coded activity
├── repo_status.json              # Detailed repository status data
├── www_project_repos.json        # Basic repository information
├── project_repos_links.json      # Project to repository mappings
└── .github/
    ├── workflows/
    │   ├── parse_repos.yml       # Fetches OWASP project repositories
    │   ├── fetch_repo_status.yml # Updates detailed repository status
    │   ├── sweep_repos.yml       # Sweeps repositories for additional data
    │   └── scrape_github_links.yml# Scrapes GitHub links from project pages
    └── scripts/
        ├── main.py               # Main repository parsing script
        ├── fetch_repo_status.py  # Fetches detailed repository information
        ├── sweep.py              # Repository sweeping logic
        └── scrape_github_links.py# GitHub link extraction script
```

## 🚀 Getting Started

### Prerequisites

- Python 3.x
- GitHub Personal Access Token (for API access)
- Slack Webhook URL (optional, for notifications)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/OWASP-BLT/BLT-OWASP-Projects.git
   cd BLT-OWASP-Projects
   ```

2. **Install dependencies**
   ```bash
   pip install requests
   ```

3. **Configure environment variables**
   
   For GitHub Actions, set these secrets in your repository:
   - `GITHUB_TOKEN` - GitHub Personal Access Token
   - `ACCESS_TOKEN` - Additional access token for API calls
   - `SLACK_WEBHOOK_URL` - Slack webhook for notifications (optional)

### Local Development

To run the scripts locally:

```bash
# Fetch OWASP project repositories
export GITHUB_TOKEN="your_token_here"
export SLACK_WEBHOOK_URL="your_webhook_url"
python .github/scripts/main.py

# Fetch detailed repository status
export ACCESS_TOKEN="your_token_here"
python .github/scripts/fetch_repo_status.py
```

### Viewing the Dashboards

Simply open the HTML files in a web browser:

```bash
# Open the main dashboard
open index.html

# Or open the simplified view
open projects.html
```

For GitHub Pages deployment, the dashboards are automatically available at your GitHub Pages URL.

## 🔄 Automated Workflows

This project uses GitHub Actions to automatically update data:

### 1. Parse OWASP Repositories (`parse_repos.yml`)
- **Trigger**: Daily at midnight (UTC) or manual dispatch
- **Purpose**: Fetches all OWASP `www-project-*` repositories
- **Output**: Updates `www_project_repos.json`
- **Notifications**: Sends Slack alerts for new repositories

### 2. Fetch Repository Status (`fetch_repo_status.yml`)
- **Trigger**: Daily at midnight (UTC), on push, or manual dispatch
- **Purpose**: Fetches detailed statistics for all tracked projects
- **Output**: Updates `repo_status.json`

### 3. Sweep Repositories (`sweep_repos.yml`)
- **Trigger**: Scheduled or manual dispatch
- **Purpose**: Additional repository data collection
- **Output**: Updates project metadata

### 4. Scrape GitHub Links (`scrape_github_links.yml`)
- **Trigger**: Scheduled or manual dispatch
- **Purpose**: Extracts GitHub repository links from OWASP project pages
- **Output**: Updates `project_repos_links.json`

## 📊 Data Files

### `www_project_repos.json`
Contains basic repository information fetched from GitHub API:
- Repository name and URL
- Creation, update, and push timestamps
- Stars, forks, and issues count

### `repo_status.json`
Contains detailed project and repository statistics:
- Project metadata (name, title, level, type)
- Repository statistics (stars, forks, PRs, issues)
- Commit and release information
- License and language data
- Build and GitHub status

### `project_repos_links.json`
Maps OWASP project names to their associated GitHub repositories.

## 🎨 Dashboard Features

### Main Dashboard (index.html)
- Sortable and searchable DataTable
- 24+ columns of project information
- Pagination (100 items per page)
- Direct links to project pages and repositories

### Simplified Dashboard (projects.html)
- Color-coded activity indicators (blue = old, red = recent)
- Mobile-responsive design
- Focus on core metrics (stars, forks, issues)
- Sortable by activity timestamps

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Commit your changes**
   ```bash
   git commit -m 'Add some amazing feature'
   ```
5. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Areas for Contribution

- Improve dashboard UI/UX
- Add new data visualizations
- Enhance data collection scripts
- Add documentation
- Fix bugs and issues
- Add new metrics or filters

## 📝 License

This project is part of the OWASP BLT (Bug Logging Tool) initiative. Please refer to the OWASP Foundation's licensing terms for more information.

## 🔗 Related Projects

- [OWASP BLT](https://github.com/OWASP-BLT/BLT) - Main OWASP Bug Logging Tool
- [OWASP Foundation](https://owasp.org/) - Official OWASP website
- [OWASP Projects](https://owasp.org/projects/) - OWASP projects directory

## 📞 Support

For questions, issues, or suggestions:

- Open an issue on [GitHub Issues](https://github.com/OWASP-BLT/BLT-OWASP-Projects/issues)
- Visit [OWASP BLT](https://github.com/OWASP-BLT/BLT)
- Check [OWASP Community](https://owasp.org/community/)

## 🙏 Acknowledgments

- OWASP Foundation and community
- All contributors to OWASP projects
- GitHub API for providing repository data
- DataTables library for interactive tables

---

**Made with ❤️ by the OWASP BLT community**