# OWASP-BLT Projects

Welcome to the OWASP-BLT ecosystem! Our organization maintains a comprehensive suite of open-source projects designed to democratize bug bounties and enhance application security. Below you'll find all of our projects organized by category.

---

## 🏆 Core Platform

### BLT - Bug Logging Tool
The flagship platform that powers the OWASP-BLT ecosystem. A community-driven platform for discovering, reporting, and tracking security vulnerabilities.

- **Repository**: [OWASP-BLT/BLT](https://github.com/OWASP-BLT/BLT)
- **Website**: [owaspblt.org](https://owaspblt.org)
- **Language**: HTML, Python, Django
- **License**: AGPL-3.0
- **Stars**: 224+ | **Forks**: 279+

**Key Features**:

- 🔍 Bug discovery and reporting system
- 🏆 Rewards and recognition for researchers
- 👥 Community-driven collaboration
- 🎮 Gamification with leaderboards
- 💰 Innovative blockchain-based rewards
- 📊 Comprehensive analytics dashboard

---

## 📱 Mobile & Desktop Apps

### BLT-Flutter
The official OWASP BLT mobile application built with Flutter for iOS and Android.

- **Repository**: [OWASP-BLT/BLT-Flutter](https://github.com/OWASP-BLT/BLT-Flutter)
- **Website**: [OWASP Project Page](https://owasp.org/www-project-bug-logging-tool/)
- **Language**: Dart, Flutter
- **License**: BSD-3-Clause
- **Stars**: 24+ | **Forks**: 37+

**Key Features**:

- Native mobile experience for bug hunters
- Cross-platform iOS and Android support
- On-the-go vulnerability reporting

---

## 🌐 Web Extensions & Tools

### BLT-Extension
Chrome extension that allows you to take screenshots of websites and report vulnerabilities directly from your browser.

- **Repository**: [OWASP-BLT/BLT-Extension](https://github.com/OWASP-BLT/BLT-Extension)
- **Language**: JavaScript
- **License**: BSD-3-Clause

**Key Features**:

- Screenshot capture functionality
- Direct bug reporting from browser
- Seamless integration with BLT platform

### BLT-on-Cloudflare
Modern implementation of BLT running on Cloudflare's edge infrastructure for improved performance and scalability.

- **Repository**: [OWASP-BLT/BLT-on-Cloudflare](https://github.com/OWASP-BLT/BLT-on-Cloudflare)
- **Demo**: [blt-on-cloudflare.pages.dev](https://blt-on-cloudflare.pages.dev/)
- **Language**: JavaScript
- **License**: AGPL-3.0

**Key Features**:

- Serverless architecture on Cloudflare Workers
- Global edge deployment
- Enhanced performance and scalability

### OWASP-BLT-Lyte
A lightweight, streamlined version of the BLT platform optimized for performance.

- **Repository**: [OWASP-BLT/OWASP-BLT-Lyte](https://github.com/OWASP-BLT/OWASP-BLT-Lyte)
- **Language**: TypeScript
- **License**: AGPL-3.0

**Key Features**:

- Lightweight implementation
- Optimized for speed and efficiency
- Modern TypeScript codebase

---

## 🤖 Bots & Automation

### BLT-Action
GitHub Action that enables automatic issue assignment and management with the `/assign` command.

- **Repository**: [OWASP-BLT/BLT-Action](https://github.com/OWASP-BLT/BLT-Action)
- **Language**: JavaScript
- **License**: BSD-3-Clause
- **Stars**: 6+ | **Forks**: 16+

**Key Features**:

- `/assign` command for self-assignment
- Automatic issue de-assignment after 24 hours
- Improves contributor workflow
- CI/CD and security scanning integration

### BLT-Lettuce
Advanced Slack bot for the BLT community with AI-powered features and automation.

- **Repository**: [OWASP-BLT/BLT-Lettuce](https://github.com/OWASP-BLT/BLT-Lettuce)
- **Language**: Python
- **License**: GPL-3.0

**Key Features**:

- Slack workspace integration
- Automated community management
- Security alerts and notifications

### BLT-Sammich
Dedicated Slack bot for BLT community interactions and support.

- **Repository**: [OWASP-BLT/BLT-Sammich](https://github.com/OWASP-BLT/BLT-Sammich)
- **Language**: Python

**Key Features**:

- Community engagement tools
- Bug bounty notifications
- Team collaboration features

### Github_Sportscaster
GitHub activity monitoring bot that provides real-time updates on repository events.

- **Repository**: [OWASP-BLT/Github_Sportscaster](https://github.com/OWASP-BLT/Github_Sportscaster)
- **Topics**: API, Bot, GitHub, Sportscaster, Tool

**Key Features**:

- Real-time GitHub activity tracking
- Automated event notifications
- Repository statistics and insights

---

## 🔧 Development Tools & Utilities

### BLT-API
Full-featured REST API for OWASP BLT running on Cloudflare Workers with edge deployment.

- **Repository**: [OWASP-BLT/BLT-API](https://github.com/OWASP-BLT/BLT-API)
- **Language**: Python
- **License**: AGPL-3.0

**Key Features**:

- Edge-deployed on Cloudflare's global network for low latency
- Full API coverage: bugs, users, domains, organizations, projects, hunts, leaderboard, and more
- Cloudflare D1 (SQLite) database for data persistence
- Authentication support with JWT tokens
- Automated D1 migrations on every deployment

### Fresh
Privacy-focused time tracking system for developers with GitHub integration and local LLM analysis.

- **Repository**: [OWASP-BLT/Fresh](https://github.com/OWASP-BLT/Fresh)
- **Language**: TypeScript
- **License**: MIT

**Key Features**:

- Privacy-first design
- GitHub integration for activity tracking
- Local LLM analysis capabilities
- Developer-focused time management

### SelfErase
Open-source, hybrid local+edge privacy toolkit for managing and deleting personal data online.

- **Repository**: [OWASP-BLT/SelfErase](https://github.com/OWASP-BLT/SelfErase)
- **Language**: Dart
- **License**: AGPL-3.0

**Key Features**:

- Personal data management
- Privacy-focused data deletion
- Hybrid local and edge processing
- Self-destruct capabilities

### OWASP-Wich (BLT-OWASP-Wich)
OWASP Project compliance checker that evaluates repositories against 100 compliance points across 10 categories.

- **Repository**: [OWASP-BLT/BLT-OWASP-Wich](https://github.com/OWASP-BLT/BLT-OWASP-Wich)
- **Live App**: [owasp-blt.github.io/OWASP-Wich](https://owasp-blt.github.io/OWASP-Wich/)
- **Language**: Python, JavaScript
- **License**: Apache 2.0

**Key Features**:

- 100-point compliance checklist across 10 categories
- Browser-based web app (no installation required)
- Python CLI tool for CI/CD automation
- Checks OWASP Top 10, ASVS, and security best practices
- Percentage-based scoring with category breakdown

### OWASP-Bumper (BLT-OWASP-Bumper)
Automated OWASP repository dashboard generator with smart insights and metrics.

- **Repository**: [OWASP-BLT/BLT-OWASP-Bumper](https://github.com/OWASP-BLT/BLT-OWASP-Bumper)
- **Live Demo**: [owasp-blt.github.io/OWASP-Bumper](https://owasp-blt.github.io/OWASP-Bumper/)
- **Language**: Python, HTML, JavaScript
- **License**: MIT

**Key Features**:

- 52-week activity sparklines for all repositories
- Real-time search and filtering by name, description, tags
- Category filters (Projects, Chapters, All)
- Activity filters (active, inactive 1yr+, inactive 3yr+)
- Daily automated updates via GitHub Actions
- Zero external dependencies (pure Python standard library)

---

## 🔐 Blockchain & Rewards

### BLT-Bacon
Bitcoin-based token system (BACON) designed to incentivize engagement and contributions within the OWASP BLT ecosystem using the Runes protocol.

- **Repository**: [OWASP-BLT/BLT-Bacon](https://github.com/OWASP-BLT/BLT-Bacon)
- **Language**: Shell
- **License**: LGPL-2.1
- **Stars**: 4+ | **Forks**: 2+

**Key Features**:

- Bitcoin Core integration
- Runes protocol implementation
- Transparent reward system
- Gamified contributor incentives
- Blockchain-based security

### BLT-OWASP-metadata
Unified metadata aggregation system for OWASP projects and chapters with interactive visualizations.

- **Repository**: [OWASP-BLT/BLT-OWASP-metadata](https://github.com/OWASP-BLT/BLT-OWASP-metadata)
- **Live Dashboard**: [owasp-blt.github.io/OWASP-metadata](https://owasp-blt.github.io/OWASP-metadata/)
- **Language**: Python, JavaScript
- **License**: Apache 2.0

**Key Features**:

- Scrapes YAML front matter from OWASP repository `index.md` files
- Metadata Explorer, Analytics Dashboard, Project Wayfinder, and SDLC Integration Chart
- Powers the OWASP Slack bot to help contributors find matching projects
- Weekly automated updates via GitHub Actions
- Export to CSV and SVG

---

## 📊 Monitoring & Analytics

### BLT-OWASP-Projects
Comprehensive dashboard for tracking and visualizing OWASP repositories and their statistics.

- **Repository**: [OWASP-BLT/BLT-OWASP-Projects](https://github.com/OWASP-BLT/BLT-OWASP-Projects)
- **Live Dashboards**: [Full Matrix](https://owasp-blt.github.io/BLT-OWASP-Projects/index.html) | [Simplified View](https://owasp-blt.github.io/BLT-OWASP-Projects/projects.html)
- **Language**: Python, HTML, JavaScript

**Key Features**:

- Tracks 1000+ OWASP `www-project-*` repositories automatically
- Daily automated data collection via GitHub Actions
- Two interactive dashboards (full matrix and simplified view)
- Tracks stars, forks, issues, PRs, commit activity, license, and language
- Slack notifications for newly detected OWASP projects


### OWASP-BLT-Website-Monitor
Automated website monitoring system using GitHub Actions to track uptime and performance.

- **Repository**: [OWASP-BLT/OWASP-BLT-Website-Monitor](https://github.com/OWASP-BLT/OWASP-BLT-Website-Monitor)
- **Website**: [Monitor Dashboard](https://owasp-blt.github.io/OWASP-BLT-Website-Monitor/)
- **Language**: HTML
- **License**: AGPL-3.0

**Key Features**:

- GitHub Actions-based monitoring
- Uptime tracking and alerts
- Performance metrics
- Historical data visualization

### BLT-Tomato
High-level OWASP project management scripts and utilities.

- **Repository**: [OWASP-BLT/BLT-Tomato](https://github.com/OWASP-BLT/BLT-Tomato)
- **Website**: [Project Page](https://owasp-blt.github.io/BLT-Tomato/)
- **Language**: HTML

**Key Features**:

- OWASP project management tools
- Automation scripts
- Project compliance utilities

---

## 🎓 Community & Education

### BLT-Jobs
Community-driven job board for the OWASP BLT ecosystem with an issue-based workflow.

- **Repository**: [OWASP-BLT/BLT-Jobs](https://github.com/OWASP-BLT/BLT-Jobs)
- **Live Site**: [jobs.owaspblt.org](https://jobs.owaspblt.org)
- **Language**: HTML, JavaScript, Python

**Key Features**:

- Issue-based job posting workflow (no fork or PR required)
- Supports Greenhouse, Lever, Workable, LinkedIn, Indeed, and any URL via Jina Reader
- Job seeker profile publishing via issue
- Full-text search across listings and profiles
- Automated data pipeline via GitHub Actions + GitHub Pages
- Zero backend — static HTML + vanilla JS


### BLT-Hackathon
Self-hosted GitHub project to conduct hackathons with charts, leaderboards, and prize management.

- **Repository**: [OWASP-BLT/BLT-Hackathon](https://github.com/OWASP-BLT/BLT-Hackathon)
- **Website**: [Hackathon Dashboard](https://owasp-blt.github.io/BLT-Hackathon/)
- **Language**: JavaScript
- **License**: MIT

**Key Features**:

- Self-hosted hackathon management
- Real-time leaderboards
- Prize tracking and distribution
- Community engagement tools
- GitHub integration

### MY-GSOC-TOOL
Dashboard tool for Google Summer of Code students to track their contributions, feedback, and documentation.

- **Repository**: [OWASP-BLT/MY-GSOC-TOOL](https://github.com/OWASP-BLT/MY-GSOC-TOOL)
- **Website**: [Student Dashboard](https://owasp-blt.github.io/MY-GSOC-TOOL/)
- **Language**: JavaScript
- **License**: AGPL-3.0

**Key Features**:

- GSoC contribution tracking
- Feedback management
- Documentation organization
- Progress visualization
- Mentor communication tools

---

## 🎨 Demo & Showcase Projects

### Sizzle
Demonstration project showcasing BLT platform capabilities and integrations.

- **Repository**: [OWASP-BLT/Sizzle](https://github.com/OWASP-BLT/Sizzle)
- **Topics**: Demo, JavaScript, Tool
- **License**: AGPL-3.0

**Key Features**:

- Platform demonstration
- Integration examples
- Feature showcase

### Toasty
Web-based demonstration tool for testing and showcasing features.

- **Repository**: [OWASP-BLT/Toasty](https://github.com/OWASP-BLT/Toasty)
- **Topics**: Demo, Tool, Web

**Key Features**:

- Interactive demonstrations
- Feature testing environment
- Web-based interface

---

## 📚 Documentation & Meta

### BLT-docs
This repository! Comprehensive documentation for all OWASP-BLT projects using MkDocs Material theme.

- **Repository**: [OWASP-BLT/BLT-docs](https://github.com/OWASP-BLT/BLT-docs)
- **Website**: [owasp-blt.github.io/BLT-docs](https://owasp-blt.github.io/BLT-docs/)
- **Topics**: Docs, Documentation, Guides, OWASP

**Key Features**:

- Centralized documentation hub
- MkDocs Material theme
- User and developer guides
- API documentation
- Contributing guidelines

### .github
Organization-wide GitHub configuration, templates, and community health files.

- **Repository**: [OWASP-BLT/.github](https://github.com/OWASP-BLT/.github)
- **Topics**: Community, GitHub, Org-config, Templates

**Key Features**:

- Issue templates
- Pull request templates
- Community guidelines
- Organization profile

---

## 🚀 Getting Started

Interested in contributing or using our projects? Here are some quick links:

- **Main Website**: [owaspblt.org](https://owaspblt.org)
- **Documentation**: [owasp-blt.github.io/documentation](https://owasp-blt.github.io/documentation/)
- **GitHub Organization**: [github.com/OWASP-BLT](https://github.com/OWASP-BLT)
- **OWASP Project Page**: [owasp.org/www-project-bug-logging-tool](https://owasp.org/www-project-bug-logging-tool/)

### Contributing

All our projects welcome contributions! Here's how to get started:

1. **Choose a project** that interests you from the list above
2. **Read the contributing guidelines** in the project's repository
3. **Join our community** on [OWASP Slack](https://owasp.org/slack/invite)
4. **Start contributing** by picking up issues labeled `good first issue`

### Support

Need help or have questions?

- 💬 **Slack**: Join the BLT channel on [OWASP Slack](https://owasp.org/slack/invite)
- 🐛 **Issues**: Open an issue in the relevant project repository
- 📧 **Email**: Contact us through GitHub discussions
- 💰 **Sponsor**: Support the project on [GitHub Sponsors](https://github.com/sponsors/OWASP-BLT)

---

## 📊 Project Statistics

- **Total Projects**: 27+
- **Total Stars**: 300+
- **Total Forks**: 450+
- **Active Contributors**: 100+
- **Programming Languages**: Python, JavaScript, TypeScript, Dart, HTML, Shell
- **Primary License**: AGPL-3.0, BSD-3-Clause, MIT, GPL-3.0, LGPL-2.1, Apache 2.0

---

<p align="center">
  <strong>⭐ Star our projects if you find them helpful!</strong><br>
  Made with ❤️ by the OWASP BLT Community
</p>
