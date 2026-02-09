# Technical Architecture

## Overview

BLT-Leaf is a serverless PR tracking application built on Cloudflare Workers with a Python backend and vanilla JavaScript frontend.

## Architecture Components

### Frontend (public/index.html)
- Single-page application with no external dependencies
- Embedded CSS with GitHub-inspired dark theme
- Vanilla JavaScript for all interactions
- Real-time updates using Fetch API
- Responsive design for desktop and mobile

### Backend (src/index.py)
- Python runtime on Cloudflare Workers
- RESTful API endpoints
- GitHub API integration for PR data fetching
- Asynchronous request handling

### Database (Cloudflare D1)
- SQLite-compatible serverless database
- Single table schema for PR tracking
- Indexed queries for performance

## Data Flow

1. **Adding a PR**:
   ```
   User Input (PR URL)
   → Frontend validates format
   → POST /api/prs
   → Backend parses URL
   → GitHub API requests (PR details, files, reviews, checks)
   → Data aggregation
   → D1 database INSERT/UPDATE
   → Response to frontend
   → UI update
   ```

2. **Listing PRs**:
   ```
   Page Load / Repo Filter
   → GET /api/prs?repo=owner/name
   → D1 database SELECT
   → JSON response
   → Frontend renders PR cards
   ```

3. **Refreshing PR Data**:
   ```
   User clicks Refresh
   → POST /api/refresh with pr_id
   → Fetch PR from database
   → GitHub API requests (fresh data)
   → D1 database UPDATE
   → Response to frontend
   → UI update
   ```

## GitHub API Integration

The application fetches data from four GitHub API endpoints:

1. **PR Details**: `/repos/{owner}/{repo}/pulls/{number}`
   - Title, state, mergeable_state, author, timestamps

2. **PR Files**: `/repos/{owner}/{repo}/pulls/{number}/files`
   - Count of files changed

3. **PR Reviews**: `/repos/{owner}/{repo}/pulls/{number}/reviews`
   - Review status (approved, changes_requested, pending)
   - Latest review per reviewer

4. **Check Runs**: `/repos/{owner}/{repo}/commits/{sha}/check-runs`
   - CI/CD check results
   - Passed, failed, skipped counts

## Database Schema

```sql
CREATE TABLE prs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_url TEXT NOT NULL UNIQUE,              -- Full GitHub PR URL
    repo_owner TEXT NOT NULL,                 -- Repository owner
    repo_name TEXT NOT NULL,                  -- Repository name
    pr_number INTEGER NOT NULL,               -- PR number
    title TEXT,                               -- PR title
    state TEXT,                               -- open, closed
    is_merged INTEGER DEFAULT 0,              -- 0 or 1
    mergeable_state TEXT,                     -- clean, dirty, blocked, unstable
    files_changed INTEGER DEFAULT 0,          -- Count of files
    author_login TEXT,                        -- GitHub username
    author_avatar TEXT,                       -- Avatar URL
    checks_passed INTEGER DEFAULT 0,          -- CI checks passed
    checks_failed INTEGER DEFAULT 0,          -- CI checks failed
    checks_skipped INTEGER DEFAULT 0,         -- CI checks skipped
    review_status TEXT,                       -- approved, changes_requested, pending, none
    last_updated_at TEXT,                     -- Last PR update from GitHub
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,-- Record creation time
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP -- Record update time
);
```

Indexes:
- `idx_repo`: Composite index on (repo_owner, repo_name) for fast filtering
- `idx_pr_number`: Index on pr_number for lookups

## API Endpoints

### GET /
Returns the HTML frontend application

### GET /api/repos
Lists all unique repositories with PR counts

**Response**:
```json
{
  "repos": [
    {
      "repo_owner": "facebook",
      "repo_name": "react",
      "pr_count": 5
    }
  ]
}
```

### GET /api/prs?repo=owner/name
Lists PRs, optionally filtered by repository

**Query Parameters**:
- `repo` (optional): Filter by "owner/name"

**Response**:
```json
{
  "prs": [
    {
      "id": 1,
      "pr_url": "https://github.com/facebook/react/pull/12345",
      "repo_owner": "facebook",
      "repo_name": "react",
      "pr_number": 12345,
      "title": "Fix: Memory leak in hooks",
      "state": "open",
      "is_merged": 0,
      "mergeable_state": "clean",
      "files_changed": 3,
      "author_login": "gaearon",
      "author_avatar": "https://avatars.githubusercontent.com/u/810438",
      "checks_passed": 15,
      "checks_failed": 0,
      "checks_skipped": 2,
      "review_status": "approved",
      "last_updated_at": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-10T08:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### POST /api/prs
Adds a new PR or updates existing one

**Request Body**:
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123"
}
```

**Response**:
```json
{
  "success": true,
  "data": { /* PR data */ }
}
```

### POST /api/refresh
Refreshes PR data from GitHub

**Request Body**:
```json
{
  "pr_id": 1
}
```

**Response**:
```json
{
  "success": true,
  "data": { /* Updated PR data */ }
}
```

## Error Handling

All API endpoints return errors in this format:
```json
{
  "error": "Error message description"
}
```

HTTP status codes:
- 200: Success
- 400: Bad Request (invalid input)
- 404: Not Found
- 500: Internal Server Error

## Frontend Components

### Sidebar
- Lists all repositories with PR counts
- "All Repositories" option to view all PRs
- Click to filter PRs by repository
- Active state highlighting

### Main Content
- PR URL input with Add button
- Error message display
- PR card list with:
  - Author avatar and username
  - PR title (clickable link to GitHub)
  - State badges (Open/Closed/Merged)
  - Review status badges
  - Merge readiness indicator
  - Files changed count
  - Time since last update
  - Check results with counts
  - Refresh button per PR

### Styling
- GitHub-inspired dark theme
- Colors:
  - Background: #0d1117
  - Cards: #161b22
  - Borders: #30363d
  - Links: #58a6ff
  - Success: #238636
  - Error: #da3633
  - Warning: #d29922

## Performance Considerations

1. **Database**: Indexed queries for fast filtering
2. **API Calls**: Parallel GitHub API requests when fetching PR data
3. **Frontend**: Minimal DOM manipulation, efficient rendering
4. **Caching**: PRs are cached in D1, refresh on-demand

## Limitations

1. **GitHub API Rate Limiting**:
   - Unauthenticated: 60 requests/hour
   - Authenticated: 5000 requests/hour
   - Consider adding GitHub token for production use

2. **Database**: No automatic PR updates (manual refresh required)

3. **Pagination**: Not implemented for large PR lists

## Future Enhancements

1. Add GitHub authentication for higher API rate limits
2. Implement automatic background refresh
3. Add webhook integration for real-time updates
4. Implement pagination for large datasets
5. Add PR search and advanced filtering
6. Add PR comparison and diff viewing
7. Add notifications for PR status changes
8. Add export functionality (CSV, JSON)
