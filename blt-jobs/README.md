# OWASP BLT Job Board (Standalone)

Standalone job board for OWASP BLT, hosted on **GitHub Pages**. Read-only list and detail views; no backend at runtime.

## Adding a job

- **[Add a job](add.html)** – Use **Quick add** (recommended) or **Manual add**.
  - **Quick add:** Open a [new pull request](https://github.com/OWASP-BLT/BLT-Jobs/compare) and paste the job listing URL in the PR description (or in a file named `job-url.txt`). Our bot (GitHub Action + scraper) will create a new job Markdown file in the repo for you. Supported sites: Greenhouse, Lever, Workable, and other common ATS and career pages.
  - **Manual add:** Create a new file under `_jobs/` with the filename format `company-slug-job-title-slug.md` (e.g. `acme-senior-engineer.md`). Use [the sample job](_jobs/example-company-sample-job.md) as a template. Open a PR with your new file.

### Adding a seeker profile

- **[Create a seeker profile](add.html)** – Use the seeker section at the bottom of the page.
  - Create a new file under `seekers/` named after you (e.g. `jane-doe.md`).
  - Use the frontmatter + body format from [`seekers/example-seeker.md`](seekers/example-seeker.md).
  - Open a PR and your profile will appear on `seekers.html` once merged.

## Data

Jobs are stored as **one Markdown file per job** in `_jobs/`, with YAML frontmatter and a body (description). Filename format: `company-slug-job-title-slug.md`. The file `data/jobs.json` is **generated** from `_jobs/*.md` by a build step (`npm run build:jobs`); a GitHub Action runs this on push to `main` so the site always has an up-to-date `data/jobs.json`.

Seeker profiles are stored as **one Markdown file per person** in `seekers/`. The build step also generates `data/seekers.json` from `seekers/*.md` for the seekers page.

### Canonical schema (`data/jobs.json`)

Each job object in the `jobs` array has exactly these 15 fields (aligned with BLT's `JobPublicSerializer`):

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Job ID (slug from filename, e.g. `acme-senior-engineer`) |
| `organization_name` | string | Organization name |
| `organization_logo` | string \| null | Absolute URL to organization logo image |
| `title` | string | Job title |
| `description` | string | Job description |
| `requirements` | string \| null | Job requirements |
| `location` | string \| null | Location (e.g. city, Remote, Hybrid) |
| `job_type` | string | One of: `full-time`, `part-time`, `contract`, `internship`, `freelance` |
| `salary_range` | string \| null | Salary range if provided |
| `expires_at` | string \| null | ISO 8601 datetime if job expires |
| `application_email` | string \| null | Email for applications |
| `application_url` | string \| null | URL for external application |
| `application_instructions` | string \| null | Custom apply instructions |
| `created_at` | string | ISO 8601 datetime when posted |
| `views_count` | number | View count (as of last sync) |

Root shape: `{"jobs": [...], "count": N, "generated_at": "<iso8601>"}`.

## Frontend

- `index.html`: Job list page
- `seekers.html`: Job seekers list page (reads `data/seekers.json`).
- `add.html`: Contribute page – add a job (Quick add or manual) and create seeker profiles.
  - Loads `data/jobs.json`
  - Client-side search (`q`) over title, description, organization name, and location
  - Filters:
    - `job_type`: `full-time`, `part-time`, `contract`, `internship`, `freelance`
    - `location`: case-insensitive substring match
  - Empty state with optional “Clear filters” when filters are active.
- `job.html`: Job detail page
  - Reads `id` from the query string (`job.html?id=<pk>`)
  - Renders:
    - Organization logo/name
    - Title, location, job type, salary range, created_at
    - Description, requirements, application instructions
    - Apply buttons:
      - `mailto:` if `application_email` is set
      - External link if `application_url` is set
    - “Applications Closed” if there is no active apply method.

Both pages use **Tailwind CSS via CDN** for styling.

## Deployment (GitHub Pages)

This repository is designed to be deployed as a static site using **GitHub Pages**.

1. Go to the repository settings in GitHub: **Settings → Pages**.
2. Under “Build and deployment”, choose:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main`, folder `/ (root)`.
3. Save. GitHub Pages will build and serve the site from `index.html`.

After a successful deploy, your site will be available at a URL like:

- `https://<your-username>.github.io/BLT-Jobs/`

or at the custom domain configured by the OWASP BLT organization once they point DNS at the Pages site.

### Local Preview

For quick local testing, you can serve the repository with a simple HTTP server, for example:

```bash
python -m http.server 8000
```

Then open:

- `http://localhost:8000/index.html` – job list
- `http://localhost:8000/job.html?id=<some-job-id>` – job detail

Note: `fetch("data/jobs.json")` requires running over HTTP/HTTPS; opening `index.html` directly from the filesystem (`file://`) will not work.

### Build jobs JSON from Markdown (local)

```bash
npm ci
npm run build:jobs
```

This reads all `_jobs/*.md` and writes `data/jobs.json`. The same script runs in CI on push to `main` when `_jobs/` or the build script changes.

