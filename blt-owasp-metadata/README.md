# OWASP Metadata

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-brightgreen?logo=github)](https://owasp-blt.github.io/OWASP-metadata/)
[![Scraper Workflow](https://github.com/OWASP-BLT/OWASP-metadata/actions/workflows/scraper.yml/badge.svg)](https://github.com/OWASP-BLT/OWASP-metadata/actions/workflows/scraper.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![OWASP](https://img.shields.io/badge/OWASP-Project-orange?logo=owasp)](https://owasp.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-yellow?logo=javascript&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS)
[![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![Mermaid](https://img.shields.io/badge/Mermaid-FF3670?logo=mermaid&logoColor=white)](https://mermaid.js.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/OWASP-BLT/OWASP-metadata/pulls)
[![GitHub Issues](https://img.shields.io/github/issues/OWASP-BLT/OWASP-metadata)](https://github.com/OWASP-BLT/OWASP-metadata/issues)
[![GitHub Stars](https://img.shields.io/github/stars/OWASP-BLT/OWASP-metadata?style=social)](https://github.com/OWASP-BLT/OWASP-metadata/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/OWASP-BLT/OWASP-metadata?style=social)](https://github.com/OWASP-BLT/OWASP-metadata/network/members)

A unified metadata aggregation system for OWASP projects and chapters. This project aims to unify and standardize data across the OWASP repository ecosystem without requiring major changes to existing repositories, by leveraging the existing Jekyll front matter in `index.md` files.

## 🌐 Live Demo

**[View the Live Dashboard →](https://owasp-blt.github.io/OWASP-metadata/)**

Explore the interactive web interface with:
- 📊 **[Metadata Explorer](https://owasp-blt.github.io/OWASP-metadata/)** - Browse and search all OWASP repositories
- 📈 **[Analytics Dashboard](https://owasp-blt.github.io/OWASP-metadata/charts.html)** - Visualize metadata coverage and trends
- 🗺️ **[Project Wayfinder](https://owasp-blt.github.io/OWASP-metadata/diagram.html)** - Visual overview by type and maturity
- 🔄 **[SDLC Integration Chart](https://owasp-blt.github.io/OWASP-metadata/mermaid-diagram.html)** - OWASP projects mapped to Software Development Lifecycle phases

## Purpose

The primary goal of this project is to:

1. **Aggregate Metadata**: Collect and standardize metadata from OWASP repositories that use Jekyll-based `index.md` files with YAML front matter
2. **Enable Discovery**: Power the OWASP Slack bot to guide new users toward projects they would be interested in based on their skills, interests, and location
3. **Provide Insights**: Offer analytics and visualizations on metadata coverage across the OWASP ecosystem

## How It Works

OWASP repositories typically include an `index.md` file with Jekyll front matter containing metadata such as:

```yaml
---
title: Project Name
layout: col-sidebar
tags: security, web, tools
level: 3
type: tool
region: Global
pitch: A brief description of the project
---
```

This project:

1. **Scrapes** all OWASP organization repositories via the GitHub API
2. **Extracts** YAML front matter from each repository's `index.md` file
3. **Normalizes** the data into consistent formats (CSV, JSON)
4. **Visualizes** the data through a web-based explorer and analytics dashboard

## Data Outputs

The scraper generates several data files in the `data/` directory:

| File | Description |
|------|-------------|
| `metadata.json` | Complete metadata for all repositories in JSON format |
| `metadata.csv` | Full metadata in CSV format |
| `metadata_matrix.json` | Matrix showing which fields are present per repository |
| `metadata_matrix.csv` | Matrix in CSV format |
| `metadata_summary.md` | Summary of field usage across all repositories |
| `metadata_checklist.csv` | Checklist format for tracking metadata completeness |

## Web Interface

The project includes multiple interactive web interfaces:

| Interface | Description | Link |
|-----------|-------------|------|
| **Metadata Explorer** | Interactive table for browsing, filtering, and searching repository metadata | [View →](https://owasp-blt.github.io/OWASP-metadata/) |
| **Analytics Dashboard** | Visual analytics showing field usage, completeness rates, and trends | [View →](https://owasp-blt.github.io/OWASP-metadata/charts.html) |
| **Project Wayfinder** | Visual diagram showing projects grouped by type and maturity level | [View →](https://owasp-blt.github.io/OWASP-metadata/diagram.html) |
| **SDLC Integration Chart** | Mermaid-based diagram mapping OWASP projects to SDLC phases | [View →](https://owasp-blt.github.io/OWASP-metadata/mermaid-diagram.html) |

### Features

- 🌓 **Dark/Light Theme Toggle** - Switch between themes for comfortable viewing
- 🔍 **Advanced Filtering** - Filter by project type, maturity level, and metadata fields
- 📥 **Export Functionality** - Download data as CSV or diagrams as SVG
- 📱 **Responsive Design** - Works on desktop and mobile devices
- ⚡ **Real-time Updates** - Data refreshes weekly via GitHub Actions

## OWASP Slack Bot Integration

The standardized metadata from this project will be consumed by the OWASP Slack bot to:

- Help new contributors find projects matching their skills and interests
- Recommend relevant chapters based on user location
- Provide quick access to project information and resources
- Guide users to projects based on tags, type, and activity level

## Project Structure

```
├── scripts/
│   └── scrape_metadata.py    # Main scraper script
├── data/                     # Generated metadata files
├── index.html                # Metadata explorer UI
├── charts.html               # Analytics dashboard
├── diagram.html              # Project Wayfinder diagram
├── mermaid-diagram.html      # SDLC integration diagram
├── app.js                    # Explorer application logic
├── charts.js                 # Analytics charts logic
├── diagram.js                # Project Wayfinder logic
├── mermaid-diagram.js        # SDLC diagram logic
├── mermaid.min.js            # Mermaid library for diagrams
├── styles.css                # Shared styles
└── charts.css                # Analytics-specific styles
```

## Usage

### Running the Scraper

```bash
# Set up environment
pip install -r requirements.txt

# Set GitHub token (optional, but recommended for higher rate limits)
export GITHUB_TOKEN=your_token_here

# Run the scraper
python scripts/scrape_metadata.py
```

### Viewing the Data

Visit the **[Live Dashboard](https://owasp-blt.github.io/OWASP-metadata/)** to explore the metadata interactively, or run locally by opening `index.html` in a browser.

For analytics and visualizations, visit the **[Analytics Dashboard](https://owasp-blt.github.io/OWASP-metadata/charts.html)**.

To see how OWASP projects map to the Software Development Lifecycle, check out the **[SDLC Integration Chart](https://owasp-blt.github.io/OWASP-metadata/mermaid-diagram.html)**.

## Contributing

Contributions are welcome! This project helps improve metadata consistency across OWASP repositories. If you notice missing or inconsistent metadata in OWASP projects, consider contributing to those repositories by adding or updating their `index.md` front matter.

### How to Contribute

1. **Fork** this repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

## License

This project is part of the OWASP Foundation's open source initiatives and is licensed under the [Apache License 2.0](https://opensource.org/licenses/Apache-2.0).

---

<p align="center">
  Made with ❤️ by the <a href="https://owasp.org/www-project-bug-logging-tool/">OWASP BLT Project</a>
</p>
