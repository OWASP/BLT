# BLT-GSOC

**Live Site:** [https://gsoc.owaspblt.org/](https://gsoc.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-GSOC](https://git.owaspblt.org/BLT/BLT-GSOC)

<p align="center"><img src="logo.png" alt="blt-gsoc logo" width="160" height="160"></p>

This repository contains the Google Summer of Code (GSoC) pages for the OWASP BLT project, hosted as a static GitHub Pages site.

## 🌐 Live Site

**URL**: https://gsoc.owaspblt.org/

## 📄 Pages

- **Home Page** (`index.html`) - Main GSoC landing page with:
  - Program overview and benefits
  - Statistics and project showcase
  - Application guidelines and timeline
  - Mentor information and FAQ

- **PR Analytics** (`pr-report.html`) - Information about the PR analytics dashboard

## 📁 Repository Structure

```
BLT-GSOC/
├── index.html          # Main GSoC page
├── pr-report.html      # PR analytics info page
├── .nojekyll          # Bypass Jekyll processing
├── css/
│   └── main.css       # Custom styles
├── images/
│   └── gsoc.png       # GSoC logo
├── js/
│   └── gsoc_pr_report.js  # Analytics scripts
├── worker/            # Worker: serves the site, refreshes data into KV
├── README.md          # This file
├── CHANGELOG.md       # Version history
└── SUMMARY.md         # Project summary
```

## 🎨 Technology Stack

- **HTML5** - Semantic markup
- **Tailwind CSS** (CDN) - Utility-first styling framework
- **Font Awesome** (CDN) - Icon library
- **Custom CSS** - Additional styles and animations

### Features
- ✅ Fully responsive design (mobile, tablet, desktop)
- ✅ Dark mode support (automatic)
- ✅ Fast loading with CDN resources
- ✅ SEO optimized
- ✅ Accessible markup

## 📜 History

This repository includes all GSoC-related components from the BLT application:

## 📜 History

This repository originally contained Django templates, views, and management commands for GSoC functionality within the main OWASP BLT application. These have been converted to static HTML pages for hosting on GitHub Pages.

### Evolution
1. **Initial Migration** - GSoC pages extracted from main BLT repository
2. **Static Conversion** - Django templates converted to standalone HTML
3. **Root Migration** - Moved from `docs/` folder to root for simpler structure

All Django backend functionality has been removed in favor of a pure static site that can be easily hosted on GitHub Pages.

## 🚀 GitHub Pages Deployment

The site is configured to serve from the repository root. To enable GitHub Pages:

1. Go to repository **Settings** → **Pages**
2. Under "Source", select: **Deploy from a branch**
3. Branch: Select your branch (e.g., `main` or `copilot/move-gsoc-pages-to-repo`)
4. Folder: Select **/ (root)**
5. Click **Save**

The site will be published at: `https://gsoc.owaspblt.org/`

## 📊 Data refresh (Worker and KV)

The site is the `blt-gsoc` Cloudflare Worker: `scripts/deploy.sh blt-gsoc` copies the pages into
`public/` and deploys `worker/index.js`, which serves them. Two data files are kept in Workers KV
(binding `DATA`, namespace `blt-gsoc-data`) instead of being committed, and are served at their old
paths, so the pages did not change. Until KV has a copy, the committed file is served.

| Path | Task | When (UTC, called by [blt-cron](../blt-cron)) | Source |
| --- | --- | --- | --- |
| `/js/gsoc2026_stats.generated.js` | `gsoc2026-stats` (`worker/gsoc2026-stats.js`) | once a minute 02:17-02:31 until done | GitHub search and commits API |
| `/data/progress.json` | `progress` (`worker/progress.js`) | once a minute 23:07-23:11 until done | GitLab commits, Slack search (both workspaces) |

A full refresh needs more requests than one free-plan invocation may make (50), and GitHub allows 30
searches a minute, so each task works through its list a few items per call and keeps its cursor in
KV (`state:<task>`). A GitHub count that fails keeps the previous value. `data/contributors.json`
still lives in git and lists who the progress tracker follows.

Worker secrets: `CRON_SECRET` (same as blt-cron), `GH_API_TOKEN`, `GITLAB_TOKEN` (optional),
`SLACK_TOKEN_OWASP`, `SLACK_TOKEN_BLT` (user tokens with `search:read`). To run a task by hand, or
to backfill a day of progress, call the Worker (repeat until the answer says `"done": true`):

```bash
curl -X POST https://gsoc.owaspblt.org/__scheduled -H "X-BLT-Cron-Secret: $CRON_SECRET" \
  -d '{"task": "progress", "day": "2026-06-11", "reset": true}'
```

Tests: `npm test` (stubbed fetch and KV).

## 🔧 Local Development

To test the pages locally:

```bash
# Using Python's built-in HTTP server
python3 -m http.server 8000

# Then open http://localhost:8000 in your browser
```

Locally the data files come from `js/` and `data/` as committed, not from KV.

Or use any static file server like:
- `npx serve`
- VS Code Live Server extension
- `php -S localhost:8000`

## 📝 Content

### Main Page Features
- Hero section with GSoC logo and program overview
- Statistics cards (100+ countries, 7 years, 20+ projects)
- Student and mentor benefits
- Application timeline and process
- 7 OWASP project showcases:
  - BLT (Bug Logging Tool)
  - NEST
  - NETTACKER
  - JUICE-SHOP
  - DSOMM
  - PYGOAT
  - OpenCRE
- Mentor profiles
- Comprehensive FAQ section

### PR Analytics Page
- Feature overview
- Information about live dashboard (requires BLT backend)
- Links to main BLT application

## 🤝 Contributing

This is a static documentation site. To update content:
1. Edit the HTML files directly
2. Update CSS in `css/main.css` for styling changes
3. Test locally before committing
4. Submit a pull request

## 📄 License

This project is part of the OWASP BLT project and inherits its license.

## 🔗 Related Links

- **Main BLT Repository**: [OWASP-BLT/BLT](https://git.owaspblt.org/BLT/BLT-Core)
- **OWASP GSoC Info**: [owasp.org/www-community/initiatives/gsoc/](https://owasp.org/www-community/initiatives/gsoc/)
- **Google Summer of Code**: [summerofcode.withgoogle.com](https://summerofcode.withgoogle.com/)
