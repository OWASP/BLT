# GitHub action that auto-assigns issues to users

## Inputs

| Parameter        | Required | Description                                                                |
| ---------------- | -------- | -------------------------------------------------------------------------- |
| `repo-token`     | true     | The GITHUB_TOKEN, needed to update the Issue.                              |
| `repository`     | true     | The GITHUB_REPOSITORY identifier (format: owner/repo).                     |
| `giphy-api-key`  | true     | API key for Giphy integration (required for `/giphy` command).             |

## Features

- **Assignment Management**: Users self-assign via `/assign` or natural language phrases
- **Unassignment**: Users can unassign via `/unassign`
- **Stale Issue Handling**: Auto-unassigns after 24 hours of inactivity without a PR
- **GIF Integration**: Post GIFs using `/giphy [search term]`
- **Kudos System**: Send appreciation using `/kudos @username [message]`
- **PR Tracking**: Validates linked pull requests before unassignment
- **Multi-assignment Prevention**: Blocks new assignments if user has issues without PRs

## Example usage

Here's a complete example workflow configuration:

```yml
name: Auto Assign Issues

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  slash_assign:
    if: >
      (github.event_name == 'issue_comment' && (
      contains(github.event.comment.body, '/assign') || 
      startsWith(github.event.comment.body, '/unassign') || 
      startsWith(github.event.comment.body, '/giphy') || 
      startsWith(github.event.comment.body, '/kudos') || 
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
            repo-token: ${{ secrets.GITHUB_TOKEN }}
            repository: ${{ github.repository }}
            giphy-api-key: ${{ secrets.GIPHY_API_KEY }}

```


