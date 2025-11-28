# OWASP Metadata

A unified metadata aggregation system for OWASP projects and chapters. This project aims to unify and standardize data across the OWASP repository ecosystem without requiring major changes to existing repositories, by leveraging the existing Jekyll front matter in `index.md` files.

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

The project includes two web interfaces:

- **Metadata Explorer** (`index.html`): Interactive table for browsing, filtering, and searching repository metadata
- **Analytics Dashboard** (`charts.html`): Visual analytics showing field usage, completeness rates, and trends

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
├── app.js                    # Explorer application logic
├── charts.js                 # Analytics charts logic
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

Open `index.html` in a browser to explore the metadata interactively, or view `charts.html` for analytics and visualizations.

## Contributing

Contributions are welcome! This project helps improve metadata consistency across OWASP repositories. If you notice missing or inconsistent metadata in OWASP projects, consider contributing to those repositories by adding or updating their `index.md` front matter.

## License

This project is part of the OWASP Foundation's open source initiatives.
