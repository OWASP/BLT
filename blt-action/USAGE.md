# GitHub Action that Auto-Assigns Issues and Manages Repository Workflow

This GitHub Action provides automated issue assignment, engagement features, and workflow management for your repository.

## Inputs

| Parameter        | Required | Description                                                                |
| ---------------- | -------- | -------------------------------------------------------------------------- |
| `repo-token`     | true     | The GITHUB_TOKEN, needed to update the Issue.                              |
| `repository`     | true     | The GITHUB_REPOSITORY identifier (format: owner/repo).                     |
| `giphy-api-key`  | true     | API key for Giphy integration (required for `/giphy` command).             |

## Features

- **Assignment Management**: Human users self-assign via `/assign` or natural language phrases (bot accounts and GitHub Apps are excluded)
- **Unassignment**: Human users can unassign via `/unassign` or natural language phrases (bot accounts and GitHub Apps are excluded)
- **Stale Issue Handling**: Auto-unassigns after 24 hours of inactivity without a PR
- **GIF Integration**: Post GIFs using `/giphy [search term]` on issues or PRs
- **Kudos System**: Send appreciation using `/kudos @username [message]` (works with any GitHub username) - integrates with OWASP BLT API
- **Tip System**: Support contributors financially using `/tip @username $amount` - generates GitHub Sponsors links
- **Smart PR Tracking**: Validates linked pull requests via cross-references before unassignment
- **Multi-assignment Prevention**: Blocks new assignments if user has issues without PRs
- **Scheduled Execution**: Daily cron job checks for stale assignments
- **Attribution**: All bot comments include an attribution footer for transparency

## Example usage

Here's a complete example workflow configuration:

```yml
name: Auto Assign Issues

on:
  # Trigger on issue comments for /assign, /unassign, /giphy, /kudos commands
  issue_comment:
    types: [created]
  # Trigger on PR review comments for command support
  pull_request_review_comment:
    types: [created]
  # Run daily at midnight UTC to check for stale assignments (24+ hours inactive)
  schedule:
    - cron: '0 0 * * *'
  # Allow manual triggering from Actions tab
  workflow_dispatch:

jobs:
  slash_assign:
    # Filter to only run on relevant events
    if: >
      (github.event_name == 'issue_comment' && (
      contains(github.event.comment.body, '/assign') || 
      startsWith(github.event.comment.body, '/unassign') || 
      startsWith(github.event.comment.body, '/giphy') || 
      startsWith(github.event.comment.body, '/kudos') || 
      startsWith(github.event.comment.body, '/tip') || 
      contains(github.event.comment.body, 'assign to me') || 
      contains(github.event.comment.body, 'assign this to me') || 
      contains(github.event.comment.body, 'assign it to me') || 
      contains(github.event.comment.body, 'assign me this') || 
      contains(github.event.comment.body, 'work on this') || 
      contains(github.event.comment.body, 'i can try fixing this') || 
      contains(github.event.comment.body, 'i am interested in doing this') || 
      contains(github.event.comment.body, 'be assigned this') || 
      contains(github.event.comment.body, 'i am interested in contributing'))) || 
      github.event_name == 'schedule' || 
      github.event_name == 'workflow_dispatch' ||
      github.event_name == 'pull_request_review_comment'
    runs-on: ubuntu-latest
    steps:
      - name: BLT Action
        uses: OWASP-BLT/BLT-Action@main
        with:
            # GitHub token - automatically available, no secret needed
            repo-token: ${{ secrets.GITHUB_TOKEN }}
            # Repository identifier - automatically provided
            repository: ${{ github.repository }}
            # Giphy API key - add this as a repository secret
            giphy-api-key: ${{ secrets.GIPHY_API_KEY }}

```


