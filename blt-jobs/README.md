# BLT Jobs

A community-driven job board for the [OWASP BLT](https://owasp.org/www-project-bug-logging-tool/) ecosystem, deployed on GitHub Pages. The UI exactly matches [jobs.owaspblt.org](https://jobs.owaspblt.org) (Inter font, slate/red palette, dark mode) and uses a fully automated **PR-based contribution workflow** — no backend required.

**Live site:** [jobs.owaspblt.org](https://jobs.owaspblt.org) · [pritz395.github.io/BLT-Jobs](https://pritz395.github.io/BLT-Jobs/) *(fork preview)*

---

## Features

- **Quick Add from URL** — paste any job posting link; a bot scrapes it and creates the structured Markdown file automatically
- **Manual Job Posting** — create a Markdown file directly via GitHub's editor and open a PR
- **Job Seeker Profiles** — professionals can list themselves on the Find Talent page
- **Dark Mode** — persistent dark/light toggle, respects system preference by default
- **Full-text Search** — client-side search across all job listings and seeker profiles
- **Automated Data Pipeline** — GitHub Actions rebuild `data/jobs.json` and `data/seekers.json` on every merge, GitHub Pages redeploys instantly
- **Zero Backend** — static HTML + vanilla JS + GitHub Actions; no server, no database

---

## Quick Add — Supported Job Sites

The scraper uses native APIs and structured data extraction, not fragile HTML parsing. Supported platforms:

| Platform | Method | Example URL format |
|---|---|---|
| **Greenhouse** | Native JSON API | `boards.greenhouse.io/{company}/jobs/{id}` |
| **Lever** | Native JSON API | `jobs.lever.co/{company}/{id}` |
| **Workable** | JSON-LD schema | `apply.workable.com/{company}/j/{id}` |
| **LinkedIn** | JSON-LD schema | `linkedin.com/jobs/view/{id}` |
| **Indeed** | JSON-LD schema | `indeed.com/viewjob?jk={id}` |
| **Any other site** | Jina Reader API | Any URL (JS-rendered pages supported) |

For Greenhouse and Lever, the scraper calls their **public JSON APIs** directly — no JavaScript rendering required, full structured data (title, company, location, description, salary) extracted reliably.

For other sites, the scraper first looks for a [JSON-LD `JobPosting` schema](https://schema.org/JobPosting) embedded in the page HTML. If that's absent (JS-rendered page), it falls back to [Jina Reader](https://jina.ai/reader/) which renders the page server-side and returns clean Markdown.

---

## How It Works

### Posting a Job

#### Option 1 — Quick Add (Recommended)

1. Go to the [Contribute page](https://jobs.owaspblt.org/add.html)
2. Click **"Open a new pull request (quick add)"**
3. GitHub opens a `job-url.txt` file editor — if you don't have write access to the repo, GitHub automatically forks it for you
4. Paste the job posting URL as the file content (one URL, one line)
5. Commit to a **new branch** (not directly to `main`)
6. Click **"Propose new file"** → **"Create pull request"**
7. The `quick-add-job.yml` GitHub Action triggers automatically, scrapes the URL, and commits a structured `jobs/<company>-<title>.md` file to your PR branch
8. Review the generated file, then merge

> **Tip:** You can also paste the job URL directly in the **PR description body** instead of creating `job-url.txt` — the bot reads both.

#### Option 2 — Manual Add

1. Create a new file in `jobs/` named `company-slug-job-title-slug.md`
2. Use this YAML frontmatter template:

```yaml
---
title: "Senior Engineer"
organization_name: "Acme Corp"
organization_logo: ""
location: "Remote"
job_type: "full-time"
salary_range: "USD 120,000–160,000"
expires_at: ""
application_email: ""
application_url: "https://acme.com/careers/senior-engineer"
application_instructions: ""
requirements: ""
created_at: "2026-02-18T00:00:00Z"
views_count: 0
---

Write the full job description here in Markdown.
```

3. Open a pull request — the build action will validate and include it automatically on merge

### Creating a Seeker Profile

1. Go to the [Contribute page](https://pritz395.github.io/BLT-Jobs/add.html) and scroll to **"Create a job seeker profile"**
2. Click **"Create new seeker profile file"** — opens GitHub editor pre-filled with `seekers/your-name.md`
3. Rename the file to `seekers/your-actual-name.md` and use this template:

```yaml
---
name: "Jane Doe"
headline: "Senior Security Engineer"
location: "Remote (US/EU-friendly)"
skills: "Application security, threat modeling, Python, AWS"
experience_summary: "8+ years in AppSec, leading security reviews and secure SDLC programs."
profile_url: "https://linkedin.com/in/your-profile"
availability: "Open to full-time roles"
created_at: "2026-02-18T00:00:00Z"
---

## About Me

Write a short bio here in Markdown. This appears on your full profile card.
```

4. Commit to a new branch → open PR → merge
5. Your profile appears on the [Find Talent](https://pritz395.github.io/BLT-Jobs/seekers.html) page

---

## File Structure

```
BLT-Jobs/
├── index.html                  # Landing page (hero, How It Works, Recent Listings)
├── jobs.html                   # Full job listings with search
├── job.html                    # Individual job detail (markdown-rendered description)
├── seekers.html                # Job seeker profiles with search
├── add.html                    # Contribute page (Quick Add, Manual Add, Seeker Profile)
│
├── jobs/                       # Job posting Markdown files
│   ├── README.md               # Template and instructions
│   ├── example-company-sample-job.md
│   └── <company-slug>-<title-slug>.md
│
├── seekers/                    # Seeker profile Markdown files
│   ├── README.md               # Template and instructions
│   ├── example-seeker.md
│   └── <name-slug>.md
│
├── data/                       # Auto-generated — do not edit manually
│   ├── jobs.json               # Built from jobs/*.md
│   └── seekers.json            # Built from seekers/*.md
│
├── assets/
│   └── js/
│       ├── theme.js            # Dark/light mode toggle + localStorage persistence
│       ├── landing.js          # Recent Listings on home page
│       ├── app.js              # Jobs page search and rendering
│       └── job.js              # Job detail page (marked.js Markdown rendering)
│
├── scripts/
│   ├── build-jobs.js           # Node.js: builds data/jobs.json + data/seekers.json
│   ├── scrape-job-url.py       # Python: scrapes job URLs for Quick Add workflow
│   └── requirements-scrape.txt # Python deps for scraper (requests, beautifulsoup4)
│
├── .github/
│   ├── workflows/
│   │   ├── build-jobs.yml      # Triggered on push to main (jobs/** or seekers/**)
│   │   └── quick-add-job.yml   # Triggered on PR open/sync — scrapes job-url.txt
│   └── PULL_REQUEST_TEMPLATE/
│       └── job_submission.md
│
├── package.json
└── README.md
```

---

## GitHub Actions

### `build-jobs.yml`
Triggers on push to `main` when any file under `jobs/`, `seekers/`, or `scripts/build-jobs.js` changes.

1. Runs `node scripts/build-jobs.js`
2. If `data/jobs.json` or `data/seekers.json` changed, commits them back to `main` with `[skip ci]`
3. GitHub Pages redeploys automatically

### `quick-add-job.yml`
Triggers on every PR `opened` or `synchronize` event.

1. Looks for a URL in `job-url.txt` (first line) or falls back to the PR description body
2. Runs `python3 scripts/scrape-job-url.py <url>`
3. The scraper tries in order: Greenhouse API → Lever API → JSON-LD → static HTML → Jina Reader
4. Commits the generated `jobs/<slug>.md` file to the PR branch

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

Open in browser:

| URL | Page |
|---|---|
| `http://localhost:8000/` | Landing page |
| `http://localhost:8000/jobs.html` | Job listings |
| `http://localhost:8000/seekers.html` | Seeker profiles |
| `http://localhost:8000/job.html?id=<job-id>` | Job detail |
| `http://localhost:8000/add.html` | Contribute |

> **Note:** `fetch("data/jobs.json")` requires an HTTP server — opening HTML files directly from the filesystem (`file://`) will not work due to CORS restrictions.

To test the scraper locally:

```bash
pip install requests beautifulsoup4
python3 scripts/scrape-job-url.py "https://boards.greenhouse.io/cloudflare/jobs/7411392"
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, Tailwind CSS (CDN), Vanilla JS |
| Typography | Inter (Google Fonts), Font Awesome 6 |
| Markdown rendering | [marked.js](https://marked.js.org/) |
| Dark mode | `darkMode: "class"` Tailwind config + `localStorage` |
| Data | YAML frontmatter + Markdown → JSON via `gray-matter` |
| Scraping | Python `requests` + `beautifulsoup4` + Jina Reader API |
| CI/CD | GitHub Actions + GitHub Pages |

---

## Design

The UI exactly matches [jobs.owaspblt.org](https://jobs.owaspblt.org):

- Tailwind CSS utility classes, Inter font, slate/red color palette
- Gradient background (`slate-50 → red-50/40 → white` in light; `gray-900` in dark)
- Responsive layout (mobile-first)
- Dark mode toggle in the nav bar, persistent via `localStorage`
- OWASP BLT logo links to [owaspblt.org](https://owaspblt.org)

---

## Contributing

This is a community project under [OWASP BLT](https://owasp.org/www-project-bug-logging-tool/). Contributions of all kinds are welcome.

1. Fork this repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes
4. Push and open a Pull Request

Please follow the existing code style (Tailwind classes, vanilla JS, no build step for the frontend).

---

## License

Part of the [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/). See the upstream repository for license details.
