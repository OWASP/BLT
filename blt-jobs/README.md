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
