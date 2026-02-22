# BLT Jobs

A community-driven job board for the [OWASP BLT](https://owasp.org/www-project-bug-logging-tool/) ecosystem, deployed on GitHub Pages. The UI exactly matches [jobs.owaspblt.org](https://jobs.owaspblt.org) (Inter font, slate/red palette, dark mode). **Issue-based workflow** — open an issue with a job URL or form, we add the listing and close the issue; no fork or PR required.

**Live site:** [jobs.owaspblt.org](https://jobs.owaspblt.org)

---

## Features

- **Add job via issue** — paste a job URL or fill a form; a bot scrapes or parses it, adds the listing, and closes the issue
- **Add seeker profile via issue** — fill a template; we publish your profile and close the issue
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

### Posting a Job (issue-based — easiest)

1. Go to the [Contribute page](https://jobs.owaspblt.org/add.html)
2. Click **"Open issue: Post job from URL"** or **"Open issue: Post job (form)"**
3. For URL: paste the job link and submit the issue. For form: fill company, title, location, description, how to apply, and submit.
4. The `process-submissions.yml` workflow runs: it scrapes the URL (or parses the form), creates `jobs/<slug>.md`, pushes to `main`, comments on the issue, and **closes the issue**. The build workflow then updates `data/jobs.json` and the site.

No fork or PR needed.

### Creating a Seeker Profile (issue-based)

1. On the [Contribute page](https://jobs.owaspblt.org/add.html), click **"Open issue: Create seeker profile"**
2. Fill in the issue template (name, location, title, skills, about, links) and submit
3. The workflow creates `seekers/<name-slug>.md`, pushes to `main`, comments, and closes the issue. Your profile appears on [Find Talent](https://jobs.owaspblt.org/seekers.html).

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
│   │   ├── process-submissions.yml  # Issue-based: add job/seeker from issue, then close
│   │   └── build-jobs.yml           # Push to main: rebuild data JSON, redeploy
│   └── ISSUE_TEMPLATE/
│       ├── job-posting-from-link.yml
│       ├── job-posting.yml
│       └── job-seeker.md
│
├── package.json
└── README.md
```

---

## GitHub Actions

### `process-submissions.yml` (issue-based)
Triggers when an issue is **opened** or **edited** with a relevant label.

- **`job-posting-from-link`**: Extracts the first URL from the issue body, runs `scrape-job-url.py`, commits `jobs/<slug>.md` to `main`, comments on the issue, and **closes the issue**.
- **`job-posting`** (form): Parses the issue body with `issue-form-to-job.js`, creates `jobs/<slug>.md` with YAML frontmatter, commits to `main`, comments, and closes the issue.
- **`job-seeker`**: Parses the issue body with `issue-form-to-seeker.js`, creates `seekers/<slug>.md`, commits to `main`, comments, and closes the issue.

### `build-jobs.yml`
Triggers on push to `main` when any file under `jobs/`, `seekers/`, or `scripts/build-jobs.js` changes.

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
