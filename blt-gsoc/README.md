# BLT-GSOC

This repository contains all Google Summer of Code (GSoC) related pages and functionality extracted from the main OWASP BLT application.

## 🌐 GitHub Pages

**Live Site**: https://owasp-blt.github.io/BLT-GSOC/

The GSoC pages are now hosted as static GitHub Pages in the `docs/` directory:
- **Home Page**: [index.html](https://owasp-blt.github.io/BLT-GSOC/) - Main GSoC landing page
- **PR Analytics**: [pr-report.html](https://owasp-blt.github.io/BLT-GSOC/pr-report.html) - Information about PR analytics dashboard

### GitHub Pages Structure

```
docs/
├── index.html          # Main GSoC page (converted from Django template)
├── pr-report.html      # PR analytics info page
├── .nojekyll          # Bypass Jekyll processing
├── css/
│   └── main.css       # Custom styles
├── images/
│   └── gsoc.png       # GSoC logo
└── js/
    └── gsoc_pr_report.js  # Analytics scripts (for reference)
```

The pages have been converted from Django templates to static HTML and use:
- **Tailwind CSS** (CDN) for styling
- **Font Awesome** (CDN) for icons
- Responsive design with dark mode support

## Contents

This repository includes all GSoC-related components from the BLT application:

### Templates (`templates/`)
- **`gsoc.html`** - Main GSoC landing page showcasing:
  - GSoC program overview
  - OWASP participation information  
  - Project statistics and metrics
  - List of available GSoC projects
  - Mentor information
  - Application guidelines

- **`templates/projects/gsoc_pr_report.html`** - GSoC PR Analysis dashboard:
  - Yearly PR statistics
  - Top repositories by contributions
  - Contributor metrics
  - Interactive charts and visualizations
  - Filterable reports by year

### Views (`views/`)
- **`issue.py`** - Contains:
  - `GsocView` class - Handles the main GSoC page display
  - `refresh_gsoc_project` function - Allows staff to refresh PR data for projects
  
- **`project.py`** - Contains:
  - `gsoc_pr_report` function - Generates comprehensive PR analytics for GSoC projects
  
- **`constants.py`** - Contains:
  - `GSOC25_PROJECTS` dictionary - Defines all GSoC 2025 projects and their associated repositories

### Management Commands (`management/commands/`)
- **`fetch_gsoc_prs.py`** - Django management command to:
  - Fetch pull request data from GitHub for GSoC repositories
  - Update PR statistics and metrics
  - Support for selective repository updates
  
- **`fetch_gsoc_orgs.py`** - Django management command to:
  - Fetch organization data from GSoC API
  - Update participating organization information

### Static Assets (`static/`)
- **`js/gsoc_pr_report.js`** - JavaScript for:
  - Interactive charts using ApexCharts
  - Dynamic data visualization
  - Year filtering functionality
  - Responsive chart rendering

- **`images/gsoc.png`** - Google Summer of Code logo (225x225 PNG)

### URL Configuration
- **`urls.py`** - URL patterns for GSoC pages (extracted from main BLT app):
  - `/gsoc/` - Main GSoC landing page
  - `/gsoc/refresh/` - Project refresh endpoint (staff only)
  - `/gsoc/pr-report/` - PR analytics dashboard

## GSoC 2025 Projects

The repository tracks contributions across the following OWASP projects:

- **BLT** - Bug Logging Tool (5 repositories)
- **NEST** - OWASP Nest
- **NETTACKER** - Automated Penetration Testing Framework
- **JUICE-SHOP** - Intentionally Insecure Web Application
- **DSOMM** - DevSecOps Maturity Model
- **PYGOAT** - Intentionally Vulnerable Python Application
- **OpenCRE** - Open Common Requirement Enumeration

## Integration

These files were originally part of the main OWASP BLT repository and have been extracted into this dedicated repository for better organization and maintenance of GSoC-related functionality.

### Original Sources
All files in this repository were moved from:
- **Repository**: [OWASP-BLT/BLT](https://github.com/OWASP-BLT/BLT)
- **Date**: 2026-02-17
- **Original Paths**:
  - `website/templates/gsoc.html`
  - `website/templates/projects/gsoc_pr_report.html`
  - `website/views/issue.py` (GsocView, refresh_gsoc_project)
  - `website/views/project.py` (gsoc_pr_report)
  - `website/views/constants.py` (GSOC25_PROJECTS)
  - `website/management/commands/fetch_gsoc_prs.py`
  - `website/management/commands/fetch_gsoc_orgs.py`
  - `website/static/js/gsoc_pr_report.js`
  - `website/static/images/gsoc.png`
  - `blt/urls.py` (GSoC URL patterns)

## Dependencies

These GSoC components have dependencies on the main BLT application:

### Django Models
- `User` - Django user model for authentication
- `Repo` - Repository information and metadata
- `Contributor` - GitHub contributor data
- `GitHubIssue` - Pull request and issue tracking
- `DailyStats` - Statistics and rate limiting

### Templates
- `base.html` - Base template layout
- `includes/sidenav.html` - Navigation sidebar component
- Django template tags: `static`, `custom_tags`

### Python Packages
- Django framework
- django-allauth - Social authentication
- requests - HTTP library
- markdown - Markdown processing
- bleach - HTML sanitization
- better-profanity - Content filtering

### External Services
- GitHub API - For fetching PR and repository data
- ApexCharts CDN - For data visualization

## Integration Notes

To use these components in the main BLT application:

1. **Templates**: Place in `website/templates/` directory
2. **Views**: Import from `website/views/`
3. **Static Assets**: Place in `website/static/`
4. **Management Commands**: Place in `website/management/commands/`
5. **URL Patterns**: Include in main `urls.py`

Example URL configuration:
```python
from website.views.issue import GsocView, refresh_gsoc_project
from website.views.project import gsoc_pr_report

urlpatterns = [
    path("gsoc/", GsocView.as_view(), name="gsoc"),
    path("gsoc/refresh/", refresh_gsoc_project, name="refresh_gsoc_project"),
    path("gsoc/pr-report/", gsoc_pr_report, name="gsoc_pr_report"),
]
```

## File Structure

```
BLT-GSOC/
├── README.md                              # This file
├── CHANGELOG.md                           # Version history
├── .gitignore                             # Git ignore patterns
├── urls.py                                # URL routing configuration
├── templates/                             # Django HTML templates
│   ├── gsoc.html                         # Main GSoC page
│   └── projects/
│       └── gsoc_pr_report.html           # PR analytics dashboard
├── views/                                 # Django views
│   ├── __init__.py                       # Package initialization
│   ├── issue.py                          # GsocView and refresh function
│   ├── project.py                        # PR report generation
│   └── constants.py                      # Project constants
├── management/                            # Django management commands
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       ├── fetch_gsoc_prs.py            # Fetch PR data
│       └── fetch_gsoc_orgs.py           # Fetch org data
└── static/                                # Static assets
    ├── js/
    │   └── gsoc_pr_report.js            # Interactive charts
    └── images/
        └── gsoc.png                      # GSoC logo
```

## License

This project inherits the license from the main OWASP BLT project.

## Deployment

### Enabling GitHub Pages

To enable GitHub Pages for this repository:

1. Go to repository **Settings** > **Pages**
2. Under "Source", select **Deploy from a branch**
3. Select branch: `copilot/move-gsoc-pages-to-repo` (or `main`)
4. Select folder: `/docs`
5. Click **Save**

The site will be published at: `https://owasp-blt.github.io/BLT-GSOC/`

### Local Development

To test the static pages locally:

```bash
# Using Python's built-in HTTP server
cd docs
python3 -m http.server 8000

# Then open http://localhost:8000 in your browser
```

Or use any other static file server like `npx serve docs` or VS Code Live Server.

### Converting Templates

The `convert_to_static.py` script was used to convert Django templates to static HTML:

```bash
python3 convert_to_static.py
```

This script:
- Removes Django template tags (`{% %}` and `{{ }}`)
- Replaces `{% static %}` tags with relative paths
- Adds complete HTML structure with CDN dependencies
- Adds navigation and footer
