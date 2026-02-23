# BLT-OWASP-Bumper

**Automated OWASP Repository Dashboard Generator**

- **Repository**: [OWASP-BLT/BLT-OWASP-Bumper](https://github.com/OWASP-BLT/BLT-OWASP-Bumper)
- **Live Demo**: [owasp-blt.github.io/OWASP-Bumper](https://owasp-blt.github.io/OWASP-Bumper/)
- **Language**: Python, HTML, JavaScript
- **License**: MIT

---

## Overview

OWASP-Bumper is an **intelligent GitHub Action-powered tool** that automatically generates a comprehensive, interactive HTML dashboard displaying all repositories in the OWASP GitHub organization. It provides deep insights into repository activity, health, and metadata — all updated daily without any manual intervention.

## Key Features

- 📈 **52-week activity sparklines** — Visualize commit patterns for every repository
- 🔍 **Real-time search** — Filter by name, description, title, pitch, or tags
- 🏷️ **Category filters** — Projects, Chapters, or All repositories
- ⏰ **Activity filters** — Active, inactive 1yr+, inactive 3yr+
- 🔔 **Bump Button** — One-click reminder issue creation for inactive repos
- 📱 **Responsive design** — Works on desktop, tablet, and mobile
- ⏰ **Daily auto-updates** — Automatically runs at 00:00 UTC via GitHub Actions
- 🛡️ **XSS Protection** — All user content properly escaped
- 🌐 **Zero external dependencies** — No libraries required

---

## How It Works

```
GitHub Actions Trigger (Daily at 00:00 UTC or Manual)
        │
        ▼
Python Script (generate_repo_list.py)
  1. Fetch all repos via GitHub API (paginated)
  2. Enrich with metadata (parallel requests):
     ├─> Fetch index.md YAML frontmatter
     ├─> Fetch open PR counts
     └─> Fetch 52-week commit stats
  3. Generate static HTML with embedded JSON data
        │
        ▼
Commit & Push to Main (index.html updated automatically)
        │
        ▼
Deploy to GitHub Pages
```

---

## Technical Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Python 3.11+ | Repository data fetching and HTML generation |
| **CI/CD** | GitHub Actions | Automated daily runs and deployment |
| **Hosting** | GitHub Pages | Free, fast, reliable static hosting |
| **Frontend** | Vanilla JS/HTML/CSS | Zero-dependency interactive dashboard |
| **API** | GitHub REST API v3 | Repository data and statistics |

### Zero External Dependencies

- ✅ **Python**: Uses only the standard library (`urllib`, `json`, `base64`, etc.)
- ✅ **JavaScript**: Pure vanilla JS — no jQuery, React, or Vue needed
- ✅ **CSS**: Handcrafted responsive styles without Bootstrap or Tailwind
- ✅ **Deployment**: Native GitHub Actions — no third-party services

---

## Usage

### For the OWASP Organization (Default)

The workflow is **already configured** and runs automatically:

1. Wait for the daily run at 00:00 UTC, or
2. Trigger manually:
   - Go to **Actions** tab
   - Select **"Generate OWASP Repository List"**
   - Click **"Run workflow"**
3. View the results at: [https://owasp-blt.github.io/OWASP-Bumper/](https://owasp-blt.github.io/OWASP-Bumper/)

### For Your Own Organization

1. **Fork this repository**
2. **Enable GitHub Pages** (Settings → Pages → Source: GitHub Actions)
3. **Configure the organization** — Edit `.github/workflows/generate-repo-list.yml` and change `GITHUB_ORG: owasp` to your organization name
4. **Run the workflow** and enjoy your dashboard!

### Local Development

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT-OWASP-Bumper.git
cd BLT-OWASP-Bumper

# Run with default settings (OWASP organization)
python3 generate_repo_list.py

# Open the generated page
open index.html
```

### With Authentication (Recommended)

```bash
export GITHUB_TOKEN=ghp_your_token_here
python3 generate_repo_list.py
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_ORG` | `owasp` | Target GitHub organization |
| `GITHUB_TOKEN` | _(none)_ | GitHub Personal Access Token |
| `OUTPUT_FILE` | `index.html` | Output HTML filename |
| `FETCH_SPARKLINES` | `true` | Enable 52-week activity charts |
| `FETCH_METADATA` | `true` | Enable index.md parsing & PR counts |

---

## Project Structure

```
OWASP-Bumper/
├── generate_repo_list.py    # Main Python script (generates HTML)
├── index.html               # Generated output (auto-generated, do not edit)
├── .github/
│   └── workflows/
│       └── generate-repo-list.yml   # GitHub Actions workflow
├── README.md
└── SETUP.md                 # Detailed setup instructions
```

---

## Dashboard Features

- **Repository Metrics**: Name, description, stars, forks, issues, PRs
- **Technology Stack**: Primary programming language detection
- **Temporal Data**: Created & last updated timestamps
- **Archive Status**: Clear indication of archived repositories
- **Project Metadata**: OWASP maturity level, tags, categories, regional info
- **Multi-dimensional Sorting**: By date, name, stars, forks, issues, PRs, activity score, or OWASP level

---

## Performance

Typical execution times for the OWASP organization (~400 repositories):

| Operation | Time | API Calls |
|-----------|------|-----------|
| Fetch repository list | ~5s | ~4 requests |
| Fetch sparklines | ~60s | ~400 requests |
| Fetch metadata | ~60s | ~800 requests |
| Generate HTML | ~1s | 0 requests |
| **Total** | **~2 minutes** | **~1,204 requests** |

With optimizations (sparklines & metadata disabled): **~6 seconds total**

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Open a Pull Request
