# Changelog

All notable changes to the BLT-GSOC repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added - 2026-02-17

#### Initial Migration from OWASP-BLT/BLT Repository

All GSoC-related pages and functionality have been extracted from the main BLT application into this dedicated repository.

**Templates (2 files)**
- `templates/gsoc.html` - Main Google Summer of Code landing page with:
  - Program overview and information
  - Project listings and statistics
  - Mentor profiles
  - Application guidelines
  
- `templates/projects/gsoc_pr_report.html` - Pull Request analytics dashboard with:
  - Yearly PR statistics
  - Top repositories visualization
  - Contributor metrics
  - Interactive charts and filters

**Views (3 files)**
- `views/issue.py` - Contains:
  - `GsocView` class for rendering the main GSoC page
  - `refresh_gsoc_project()` function for updating project data
  
- `views/project.py` - Contains:
  - `gsoc_pr_report()` function for generating PR analytics
  
- `views/constants.py` - Contains:
  - `GSOC25_PROJECTS` dictionary defining all GSoC 2025 projects

**Management Commands (2 files)**
- `management/commands/fetch_gsoc_prs.py` - Fetches PR data from GitHub
- `management/commands/fetch_gsoc_orgs.py` - Fetches GSoC organization data

**Static Assets (2 files)**
- `static/js/gsoc_pr_report.js` - Interactive charts and data visualization (938 lines)
- `static/images/gsoc.png` - Google Summer of Code logo (225x225 PNG)

**Configuration**
- `urls.py` - URL routing patterns for GSoC pages

**Documentation**
- `README.md` - Comprehensive documentation of all components
- `CHANGELOG.md` - This file

**Development Files**
- `.gitignore` - Python/Django project ignore patterns
- `__init__.py` files for proper Python package structure

### Projects Tracked

The repository currently tracks contributions across these OWASP projects:
- **BLT** (5 repositories) - Bug Logging Tool
- **NEST** - OWASP Nest
- **NETTACKER** - Automated Penetration Testing Framework
- **JUICE-SHOP** (2 repositories) - Intentionally Insecure Web Application
- **DSOMM** - DevSecOps Maturity Model
- **PYGOAT** - Intentionally Vulnerable Python Application
- **OpenCRE** - Open Common Requirement Enumeration

### Technical Details

**Source Repository**: OWASP-BLT/BLT  
**Migration Date**: February 17, 2026  
**Total Files Moved**: 11 core files + 4 metadata files  
**Lines of Code**: ~10,600+ lines

### Dependencies

These components depend on the main BLT application for:
- Base templates (`base.html`, `includes/sidenav.html`)
- Django models (User, Repo, Contributor, GitHubIssue, DailyStats)
- Django framework and utilities
- Authentication and permissions
- Database access

## Future Enhancements

Potential improvements for future versions:
- [ ] Add unit tests for views and management commands
- [ ] Create standalone deployment documentation
- [ ] Add API endpoints for programmatic access
- [ ] Implement caching for PR reports
- [ ] Add export functionality (CSV, JSON, PDF)
- [ ] Create admin interface for project management
- [ ] Add automated update scheduling
- [ ] Implement webhook integration for real-time updates
