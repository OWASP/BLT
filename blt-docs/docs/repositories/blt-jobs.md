# BLT-Jobs

**Community-driven job board for the OWASP BLT ecosystem**

- **Repository**: [OWASP-BLT/BLT-Jobs](https://github.com/OWASP-BLT/BLT-Jobs)
- **Live Site**: [jobs.owaspblt.org](https://jobs.owaspblt.org)
- **Language**: HTML, JavaScript, Python
- **License**: See upstream OWASP BLT repository

---

## Overview

BLT-Jobs is a community-driven job board for the OWASP BLT ecosystem, deployed on GitHub Pages. It uses an **issue-based workflow** — contributors open an issue with a job URL or form, the system adds the listing and closes the issue; no fork or PR required.

## Key Features

- **Add job via issue** — Paste a job URL or fill a form; a bot scrapes or parses it, adds the listing, and closes the issue
- **Add seeker profile via issue** — Fill a template; your profile is published and the issue is closed automatically
- **Dark Mode** — Persistent dark/light toggle, respects system preference
- **Full-text Search** — Client-side search across all job listings and seeker profiles
- **Automated Data Pipeline** — GitHub Actions rebuild JSON data on every merge; GitHub Pages redeploys instantly
- **Zero Backend** — Static HTML + vanilla JS + GitHub Actions; no server, no database

---

## How It Works

### Posting a Job (Issue-based)

1. Go to the [Contribute page](https://jobs.owaspblt.org/add.html)
2. Click **"Open issue: Post job from URL"** or **"Open issue: Post job (form)"**
3. For URL: paste the job link and submit the issue. For form: fill company, title, location, description, how to apply, and submit
4. The `process-submissions.yml` workflow runs: it scrapes the URL (or parses the form), creates `jobs/<slug>.md`, pushes to `main`, comments on the issue, and **closes the issue**. The build workflow then updates `data/jobs.json` and the site.

No fork or PR needed.

### Creating a Seeker Profile

1. On the [Contribute page](https://jobs.owaspblt.org/add.html), click **"Open issue: Create seeker profile"**
2. Fill in the issue template (name, location, title, skills, about, links) and submit
3. The workflow creates `seekers/<name-slug>.md`, pushes to `main`, comments, and closes the issue. Your profile appears on [Find Talent](https://jobs.owaspblt.org/seekers.html).

---

## Supported Job Platforms

The scraper uses native APIs and structured data extraction, not fragile HTML parsing:

| Platform | Method | Example URL format |
|---|---|---|
| **Greenhouse** | Native JSON API | `boards.greenhouse.io/{company}/jobs/{id}` |
| **Lever** | Native JSON API | `jobs.lever.co/{company}/{id}` |
| **Workable** | JSON-LD schema | `apply.workable.com/{company}/j/{id}` |
| **LinkedIn** | JSON-LD schema | `linkedin.com/jobs/view/{id}` |
| **Indeed** | JSON-LD schema | `indeed.com/viewjob?jk={id}` |
| **Any other site** | Jina Reader API | Any URL (JS-rendered pages supported) |

---

## GitHub Actions

### `process-submissions.yml` (issue-based)

Triggers when an issue is **opened** or **edited** with a relevant label:

- **`job-posting-from-link`**: Extracts the first URL from the issue body, runs `scrape-job-url.py`, commits `jobs/<slug>.md` to `main`, comments on the issue, and closes the issue.
- **`job-posting`** (form): Parses the issue body, creates `jobs/<slug>.md` with YAML frontmatter, commits to `main`, comments, and closes the issue.
- **`job-seeker`**: Parses the issue body, creates `seekers/<slug>.md`, commits to `main`, comments, and closes the issue.

### `build-jobs.yml`

Triggers on push to `main` when any file under `jobs/`, `seekers/`, or `scripts/build-jobs.js` changes:

1. Runs `node scripts/build-jobs.js`
2. If `data/jobs.json` or `data/seekers.json` changed, commits them back to `main` with `[skip ci]`
3. GitHub Pages redeploys automatically

---

## Local Development

```bash
# Install Node dependencies
npm ci

# Build data/jobs.json and data/seekers.json from Markdown files
npm run build:jobs

# Serve locally (required — fetch() doesn't work over file://)
python3 -m http.server 8000
```

| URL | Page |
|---|---|
| `http://localhost:8000/` | Landing page |
| `http://localhost:8000/jobs.html` | Job listings |
| `http://localhost:8000/seekers.html` | Seeker profiles |
| `http://localhost:8000/add.html` | Contribute |

To test the scraper locally:

```bash
pip install requests beautifulsoup4
python3 scripts/scrape-job-url.py "https://boards.greenhouse.io/cloudflare/jobs/7411392"
```

---

## Project Structure

```
BLT-Jobs/
├── index.html                  # Landing page
├── jobs.html                   # Full job listings with search
├── job.html                    # Individual job detail
├── seekers.html                # Job seeker profiles
├── add.html                    # Contribute page
├── jobs/                       # Job posting Markdown files
├── seekers/                    # Seeker profile Markdown files
├── data/                       # Auto-generated JSON files
├── assets/js/
│   ├── theme.js                # Dark/light mode toggle
│   ├── landing.js              # Recent Listings on home page
│   ├── app.js                  # Jobs page search and rendering
│   └── job.js                  # Job detail page
├── scripts/
│   ├── build-jobs.js           # Builds data/*.json from Markdown
│   └── scrape-job-url.py       # Scrapes job URLs for Quick Add
└── .github/workflows/
    ├── process-submissions.yml # Issue-based job/seeker creation
    └── build-jobs.yml          # Rebuilds data JSON on push
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, Tailwind CSS (CDN), Vanilla JS |
| Typography | Inter (Google Fonts), Font Awesome 6 |
| Markdown rendering | [marked.js](https://marked.js.org/) |
| Dark mode | Tailwind `darkMode: "class"` + `localStorage` |
| Data | YAML frontmatter + Markdown → JSON via `gray-matter` |
| Scraping | Python `requests` + `beautifulsoup4` + Jina Reader API |
| CI/CD | GitHub Actions + GitHub Pages |

---

## Contributing

This is a community project under OWASP BLT. Contributions of all kinds are welcome.

1. Fork this repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes
4. Push and open a Pull Request

Please follow the existing code style (Tailwind classes, vanilla JS, no build step for the frontend).
