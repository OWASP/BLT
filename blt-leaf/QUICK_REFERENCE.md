# Quick Reference Guide

## UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ 🍃 PR Readiness Checker                                         │
├────────────┬───────────────────────────────────────────────────┤
│            │  Enter GitHub PR URL                              │
│ REPOS      │  ┌────────────────────────────┐  ┌────────────┐  │
│            │  │ https://github.com/...     │  │  Add PR    │  │
│ ┌────────┐ │  └────────────────────────────┘  └────────────┘  │
│ │  All   │ │                                                   │
│ │ Repos  │ │  ┌─────────────────────────────────────────────┐ │
│ │        │ │  │ 👤  PR Title                    [Open]      │ │
│ │ 2 PRs  │ │  │    owner/repo #123 by username  [Approved]  │ │
│ └────────┘ │  │                                             │ │
│            │  │ Merge Status: ✓ Ready to merge              │ │
│ ┌────────┐ │  │ Files Changed: 5                            │ │
│ │facebook│ │  │ Last Updated: 2 hours ago                   │ │
│ │/react  │ │  │ Checks: ✓ 15 passed | ✗ 0 failed | - 2 skip │ │
│ │        │ │  │                           [Refresh]         │ │
│ │ 1 PR   │ │  └─────────────────────────────────────────────┘ │
│ └────────┘ │                                                   │
│            │  ┌─────────────────────────────────────────────┐ │
│ ┌────────┐ │  │ 👤  Another PR Title              [Merged]  │ │
│ │owner/  │ │  │    owner/repo #456 by user2      [Pending]  │ │
│ │repo    │ │  │                                             │ │
│ │        │ │  │ Merge Status: ✗ Conflicts                   │ │
│ │ 1 PR   │ │  │ Files Changed: 12                           │ │
│ └────────┘ │  │ Last Updated: 1 day ago                     │ │
│            │  │ Checks: ✓ 8 passed | ✗ 2 failed | - 1 skip  │ │
│            │  │                           [Refresh]         │ │
│            │  └─────────────────────────────────────────────┘ │
└────────────┴───────────────────────────────────────────────────┘
```

## Color Scheme (GitHub Dark Theme)

- **Background**: Dark gray (#0d1117)
- **Cards**: Darker gray (#161b22)
- **Borders**: Medium gray (#30363d)
- **Primary (Links)**: Blue (#58a6ff)
- **Success**: Green (#238636)
- **Error/Danger**: Red (#da3633)
- **Warning**: Yellow (#d29922)
- **Text**: Light gray (#c9d1d9)
- **Muted text**: Medium gray (#8b949e)

## Badge Colors

- **Open**: Green background
- **Closed**: Red background
- **Merged**: Purple background
- **Approved**: Green background
- **Changes Requested**: Red background
- **Pending Review**: Yellow background
- **No Reviews**: Gray background

## PR States

### State (Open/Closed/Merged)
- **Open**: PR is currently open for review
- **Closed**: PR was closed without merging
- **Merged**: PR was successfully merged

### Mergeable State
- **✓ Ready to merge**: No conflicts, all checks passed
- **✗ Conflicts**: Merge conflicts need resolution
- **⊘ Blocked**: Blocked by branch protection rules
- **⚠ Unstable**: Failing checks or incomplete
- **unknown**: Status not yet determined

### Review Status
- **Approved**: At least one approving review
- **Changes Requested**: Reviewer requested changes
- **Pending Review**: Awaiting reviews
- **No Reviews**: No reviews submitted yet

### Check Status
- **Passed (Green ●)**: Check completed successfully
- **Failed (Red ●)**: Check failed
- **Skipped (Gray ●)**: Check was skipped

## API Usage Examples

### Add a PR
```bash
curl -X POST https://your-worker.workers.dev/api/prs \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/facebook/react/pull/12345"}'
```

### List all PRs
```bash
curl https://your-worker.workers.dev/api/prs
```

### List PRs for a specific repo
```bash
curl https://your-worker.workers.dev/api/prs?repo=facebook/react
```

### List all repositories
```bash
curl https://your-worker.workers.dev/api/repos
```

### Refresh a PR
```bash
curl -X POST https://your-worker.workers.dev/api/refresh \
  -H "Content-Type: application/json" \
  -d '{"pr_id": 1}'
```

## Keyboard Shortcuts

- **Enter** in PR URL input: Add the PR

## Browser Requirements

- Modern browsers with ES6+ support
- JavaScript enabled
- No external dependencies required
- Works on mobile and desktop

## Performance

- Initial page load: < 1s
- PR data fetch: 2-5s (depends on GitHub API)
- List refresh: < 500ms (from cache)
- Concurrent requests: Up to 6 parallel GitHub API calls per PR

## Data Persistence

- All PR data is stored in Cloudflare D1 database
- Data persists across sessions
- Manual refresh required to update PR status
- No automatic background updates (by design)

## Privacy & Security

- No user authentication required
- No personal data collected
- Uses GitHub public API (no tokens required for public repos)
- All API requests are server-side (backend)
- CORS enabled for API endpoints

## Troubleshooting

### "Failed to add PR"
- Check PR URL format: `https://github.com/owner/repo/pull/123`
- Verify PR exists and is public
- Check GitHub API rate limits

### "Error loading PRs"
- Check browser console for errors
- Verify database is properly initialized
- Check Cloudflare Workers logs

### PRs not showing updated data
- Click the "Refresh" button on individual PRs
- PR data is cached and not automatically updated

### GitHub API rate limit exceeded
- Wait for rate limit reset (60 requests per hour for unauthenticated)
- Consider adding GitHub token for higher limits (5000/hour)

## Tips

1. **Bulk refresh**: Refresh individual PRs rather than re-adding them
2. **Organization**: Use repository filtering to focus on specific projects
3. **Monitoring**: Check the checks summary to quickly identify failing PRs
4. **Review status**: Use review badges to prioritize PR reviews
5. **Time tracking**: "Last updated" shows PR activity recency
