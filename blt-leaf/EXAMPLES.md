# Example Data

## Sample PR Data Structure

This shows what a PR record looks like in the database and API responses:

```json
{
  "id": 1,
  "pr_url": "https://github.com/facebook/react/pull/28000",
  "repo_owner": "facebook",
  "repo_name": "react",
  "pr_number": 28000,
  "title": "Add support for async rendering in concurrent mode",
  "state": "open",
  "is_merged": 0,
  "mergeable_state": "clean",
  "files_changed": 15,
  "author_login": "gaearon",
  "author_avatar": "https://avatars.githubusercontent.com/u/810438?v=4",
  "checks_passed": 12,
  "checks_failed": 0,
  "checks_skipped": 1,
  "review_status": "approved",
  "last_updated_at": "2024-01-20T15:30:45Z",
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-20T15:30:45Z"
}
```

## Sample Repository List

```json
{
  "repos": [
    {
      "repo_owner": "facebook",
      "repo_name": "react",
      "pr_count": 3
    },
    {
      "repo_owner": "microsoft",
      "repo_name": "typescript",
      "pr_count": 2
    },
    {
      "repo_owner": "OWASP-BLT",
      "repo_name": "BLT",
      "pr_count": 5
    }
  ]
}
```

## Sample Use Cases

### Use Case 1: Track Team PRs
A team wants to track all PRs across their repositories:

1. Add PRs from different repos:
   - `https://github.com/company/frontend/pull/123`
   - `https://github.com/company/backend/pull/456`
   - `https://github.com/company/mobile/pull/789`

2. View all PRs in the main view
3. Filter by specific repository in the sidebar
4. Check review status and merge readiness
5. Refresh PRs to get latest status

### Use Case 2: Monitor Open Source Contributions
A contributor tracks their open source PRs:

1. Add PRs to different projects:
   - `https://github.com/nodejs/node/pull/50000`
   - `https://github.com/rust-lang/rust/pull/120000`
   - `https://github.com/python/cpython/pull/110000`

2. Monitor check status for each PR
3. See when maintainers last updated the PR
4. Check if reviews have been submitted
5. Identify PRs needing attention

### Use Case 3: Release Management
A release manager tracks PRs for upcoming release:

1. Add all PRs planned for release:
   - Feature PRs
   - Bug fix PRs
   - Documentation PRs

2. Check mergeable state for each
3. Verify all checks pass
4. Confirm all have required approvals
5. Identify blockers (conflicts, failing checks)

## Sample GitHub API Responses

### PR Details Response
```json
{
  "url": "https://api.github.com/repos/facebook/react/pulls/28000",
  "id": 1234567890,
  "number": 28000,
  "state": "open",
  "title": "Add support for async rendering",
  "user": {
    "login": "gaearon",
    "avatar_url": "https://avatars.githubusercontent.com/u/810438?v=4"
  },
  "merged": false,
  "mergeable_state": "clean",
  "updated_at": "2024-01-20T15:30:45Z",
  "head": {
    "sha": "abc123def456..."
  }
}
```

### Files Response
```json
[
  {
    "filename": "packages/react/src/ReactHooks.js",
    "status": "modified",
    "additions": 45,
    "deletions": 12
  },
  {
    "filename": "packages/react/src/ReactAsync.js",
    "status": "added",
    "additions": 230,
    "deletions": 0
  }
]
```

### Reviews Response
```json
[
  {
    "user": {
      "login": "sophiebits"
    },
    "state": "APPROVED",
    "submitted_at": "2024-01-19T10:00:00Z"
  },
  {
    "user": {
      "login": "sebmarkbage"
    },
    "state": "CHANGES_REQUESTED",
    "submitted_at": "2024-01-18T14:30:00Z"
  }
]
```

### Check Runs Response
```json
{
  "check_runs": [
    {
      "name": "CI / test (ubuntu-latest)",
      "status": "completed",
      "conclusion": "success"
    },
    {
      "name": "CI / lint",
      "status": "completed",
      "conclusion": "success"
    },
    {
      "name": "CI / build",
      "status": "completed",
      "conclusion": "failure"
    }
  ]
}
```

## Database Queries

### Get all PRs
```sql
SELECT * FROM prs ORDER BY last_updated_at DESC;
```

### Get PRs for specific repo
```sql
SELECT * FROM prs 
WHERE repo_owner = 'facebook' AND repo_name = 'react'
ORDER BY last_updated_at DESC;
```

### Get repositories with PR counts
```sql
SELECT DISTINCT repo_owner, repo_name, COUNT(*) as pr_count
FROM prs 
GROUP BY repo_owner, repo_name
ORDER BY repo_owner, repo_name;
```

### Get PRs needing attention (failing checks or changes requested)
```sql
SELECT * FROM prs 
WHERE checks_failed > 0 OR review_status = 'changes_requested'
ORDER BY last_updated_at DESC;
```

### Get mergeable PRs (ready to merge)
```sql
SELECT * FROM prs 
WHERE state = 'open' 
  AND mergeable_state = 'clean'
  AND review_status = 'approved'
  AND checks_failed = 0
ORDER BY last_updated_at DESC;
```

## Testing Checklist

- [ ] Add a valid GitHub PR URL
- [ ] Add an invalid URL (should show error)
- [ ] Add a PR that doesn't exist (should show error)
- [ ] View all PRs
- [ ] Filter by repository
- [ ] Refresh a PR
- [ ] Check that state badges display correctly
- [ ] Check that review badges display correctly
- [ ] Check that check counts are accurate
- [ ] Verify time ago calculation
- [ ] Test on mobile device
- [ ] Test on desktop browser
- [ ] Verify CORS headers work
- [ ] Test with GitHub API rate limit
