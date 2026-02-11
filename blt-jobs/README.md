# OWASP BLT Job Board (Standalone)

Standalone job board for OWASP BLT, hosted on **GitHub Pages**. Read-only list and detail views; no backend at runtime.

## Data

Job data is synced from the main BLT application. The process for syncing is TBD in a later PR.

### Canonical schema (`data/jobs.json`)

Each job object in the `jobs` array has exactly these 15 fields (aligned with BLT's `JobPublicSerializer`):

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Job ID |
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

