# BLT-OWASP-metadata

**Unified metadata aggregation system for OWASP projects and chapters**

- **Repository**: [OWASP-BLT/BLT-OWASP-metadata](https://github.com/OWASP-BLT/BLT-OWASP-metadata)
- **Live Dashboard**: [owasp-blt.github.io/OWASP-metadata](https://owasp-blt.github.io/OWASP-metadata/)
- **Language**: Python, JavaScript
- **License**: Apache 2.0

---

## Overview

BLT-OWASP-metadata is a unified metadata aggregation system for OWASP projects and chapters. It standardizes data across the OWASP repository ecosystem without requiring major changes to existing repositories, by leveraging the existing Jekyll front matter in `index.md` files.

## Key Features

- 📊 **Metadata Explorer** — Browse and search all OWASP repositories
- 📈 **Analytics Dashboard** — Visualize metadata coverage and trends
- 🗺️ **Project Wayfinder** — Visual overview by type and maturity
- 🔄 **SDLC Integration Chart** — OWASP projects mapped to Software Development Lifecycle phases
- 🌓 **Dark/Light Theme Toggle** — Comfortable viewing in any environment
- 🔍 **Advanced Filtering** — Filter by project type, maturity level, and metadata fields
- 📥 **Export Functionality** — Download data as CSV or diagrams as SVG
- ⚡ **Weekly Auto-updates** — Data refreshes weekly via GitHub Actions

---

## Purpose

1. **Aggregate Metadata** — Collect and standardize metadata from OWASP repositories that use Jekyll-based `index.md` files with YAML front matter
2. **Enable Discovery** — Power the OWASP Slack bot to guide new users toward projects they would be interested in based on their skills, interests, and location
3. **Provide Insights** — Offer analytics and visualizations on metadata coverage across the OWASP ecosystem

---

## How It Works

OWASP repositories typically include an `index.md` file with Jekyll front matter:

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

The system:

1. **Scrapes** all OWASP organization repositories via the GitHub API
2. **Extracts** YAML front matter from each repository's `index.md` file
3. **Normalizes** the data into consistent formats (CSV, JSON)
4. **Visualizes** the data through a web-based explorer and analytics dashboard

---

## Web Interface

| Interface | Description | Link |
|-----------|-------------|------|
| **Metadata Explorer** | Interactive table for browsing, filtering, and searching repository metadata | [View →](https://owasp-blt.github.io/OWASP-metadata/) |
| **Analytics Dashboard** | Visual analytics showing field usage, completeness rates, and trends | [View →](https://owasp-blt.github.io/OWASP-metadata/charts.html) |
| **Project Wayfinder** | Visual diagram showing projects grouped by type and maturity level | [View →](https://owasp-blt.github.io/OWASP-metadata/diagram.html) |
| **SDLC Integration Chart** | Mermaid-based diagram mapping OWASP projects to SDLC phases | [View →](https://owasp-blt.github.io/OWASP-metadata/mermaid-diagram.html) |

---

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

---

## OWASP Slack Bot Integration

The standardized metadata from this project is consumed by the OWASP Slack bot to:

- Help new contributors find projects matching their skills and interests
- Recommend relevant chapters based on user location
- Provide quick access to project information and resources
- Guide users to projects based on tags, type, and activity level

---

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

---

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
├── styles.css                # Shared styles
└── charts.css                # Analytics-specific styles
```

---

## Contributing

Contributions are welcome! This project helps improve metadata consistency across OWASP repositories. If you notice missing or inconsistent metadata in OWASP projects, consider contributing to those repositories by adding or updating their `index.md` front matter.

1. Fork this repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request
