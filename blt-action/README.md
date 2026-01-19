# BLT-Action README

## Introduction

**BLT-Action** is an innovative GitHub Action designed to streamline the issue and pull request management process in GitHub repositories. It provides a powerful suite of features to automatically assign users to issues, track progress, engage contributors, and maintain an organized workflow. The action runs on comment events, scheduled intervals, and can be manually triggered to ensure your repository stays organized and contributors stay engaged.

## Features

### Assignment Management
- **Automatic Assignment**: Users can self-assign to issues using multiple natural language commands:
  - `/assign`
  - `assign to me`
  - `assign this to me`
  - `assign it to me`
  - `assign me this`
  - `work on this`
  - `i can try fixing this`
  - `i am interested in doing this`
  - `be assigned this`
  - `i am interested in contributing`
- **Manual Unassignment**: Users can unassign themselves using `/unassign`.
- **Assignment Validation**: Prevents users from being assigned to multiple issues without active pull requests.
- **Smart PR Tracking**: Automatically checks for linked pull requests before unassigning users.

### Automated Workflow Management
- **Time-Based Unassignment**: Automatically unassigns users from issues after 24 hours of inactivity if no pull request is linked, keeping issues available for others.
- **Smart Pull Request Detection**: Identifies cross-referenced open pull requests in issue timelines to avoid premature unassignment.
- **Duplicate Prevention**: Avoids creating duplicate unassignment notifications by checking existing comments.
- **Scheduled Execution**: Runs daily via cron schedule to check for stale assignments and maintain repository hygiene.
- **Manual Triggers**: Supports workflow_dispatch for on-demand execution.

### Engagement Features
- **GIF Integration**: Post GIFs from Giphy using `/giphy [search term]` to add fun and personality to discussions.
- **Kudos System**: Send appreciation to contributors using `/kudos @username [optional message]` to recognize great work.
  - Integrates with OWASP BLT team API to track and record kudos
  - Provides confirmation when kudos are successfully sent
  - Supports custom appreciation messages
- **Tip System**: Support contributors financially using `/tip @username $amount` to send tips via GitHub Sponsors.
  - Generates direct links to contributor's GitHub Sponsors page
  - Validates GitHub Sponsors availability for the recipient
  - Provides clear instructions for completing one-time payments
  - Works on both issues and pull request comments

### Compatibility & Branding
- **Issue and PR Support**: Works on both issue comments and pull request review comments for maximum flexibility.
- **Attribution**: All bot-generated comments include an attribution footer linking back to the BLT-Action repository for transparency and recognition.
- **Built on Node.js 20**: Leverages the latest GitHub Actions runtime for reliability and performance.

## How It Works

The BLT-Action operates through multiple triggers:

1. **Comment-Triggered Actions**: When users comment on issues with specific commands (`/assign`, `/unassign`), the action processes these commands immediately. These commands do not work for pull requests.

2. **Scheduled Monitoring**: A daily cron job (configurable) checks all assigned issues for inactivity:
   - Identifies issues assigned for more than 24 hours without updates
   - Verifies if the issue has a linked pull request via cross-references
   - Automatically unassigns inactive issues without PRs to keep them available

3. **Smart Assignment Logic**:
   - Prevents users from being assigned to multiple issues without active pull requests
   - Blocks duplicate assignments to the same issue
   - Validates existing assignments before allowing new ones
   - Automatically adds and removes the "assigned" label for tracking

4. **Engagement & Recognition**: Commands like `/giphy`, `/kudos`, and `/tip` work across both issues and pull requests, making it easy to keep discussions lively, recognize contributor efforts, and support them financially via GitHub Sponsors.

## Getting Started

### Prerequisites

- A GitHub account.
- A GitHub repository where you have administrative privileges.

### Configuration

#### Required Inputs

| Parameter | Description |
|-----------|-------------|
| `repo-token` | GitHub token for authentication (use `${{ secrets.GITHUB_TOKEN }}`) |
| `repository` | Repository identifier (use `${{ github.repository }}`) |
| `giphy-api-key` | API key for Giphy integration (required for `/giphy` command) |

#### Setting Up Giphy API Key

To use the `/giphy` command:
1. Get a free API key from [Giphy Developers](https://developers.giphy.com/)
2. Add it as a repository secret named `GIPHY_API_KEY`
3. Reference it in your workflow as shown below

### Installation

1. **Add the Action to Your Repository**:
   - Navigate to your GitHub repository.
   - Create a `.github/workflows` directory if it doesn't exist.
   - Create a new YAML file inside the workflows directory (e.g., `blt-action.yml`).
   - Add the following content to the YAML file:

    ```yml
    name: Auto Assign Issues
    
    on:
      # Trigger on new comments on issues
      issue_comment:
        types: [created]
      # Trigger on new review comments on pull requests
      pull_request_review_comment:
        types: [created]
      # Run daily at midnight UTC to check for stale assignments
      schedule:
        - cron: '0 0 * * *'
      # Allow manual triggering from the Actions tab
      workflow_dispatch:
    
    jobs:
      auto-assign:
        # Only run on relevant events to avoid unnecessary workflow runs
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
              # GitHub token is automatically available - no need to create a secret
              repo-token: ${{ secrets.GITHUB_TOKEN }}
              # Repository identifier is automatically provided by GitHub
              repository: ${{ github.repository }}
              # Giphy API key must be added as a repository secret
              giphy-api-key: ${{ secrets.GIPHY_API_KEY }}
    
    ```


### Usage

#### Assignment Commands
- **Self-assign to an issue**: Comment any of these on an issue:
  - `/assign`
  - `assign to me`
  - `assign this to me`
  - `work on this`
  - `i can try fixing this`
  - `i am interested in doing this`
  - `i am interested in contributing`
  
  The action will:
  - Check if you have any other open assigned issues without pull requests
  - Assign you if eligible and add an "assigned" label
  - Give you 24 hours to submit a pull request
  
- **Unassign yourself**: Comment `/unassign` on the issue
  - Removes you from the issue
  - Removes the "assigned" label
  - Makes the issue available for others

#### Fun & Engagement Commands
- **Post a GIF**: Comment `/giphy [search term]`
  - Example: `/giphy celebration`
  - Posts an animated GIF from Giphy matching your search term
  - Works on both issues and pull request comments
  - Shows a message if no GIF is found for the search term
  
- **Send Kudos**: Comment `/kudos @username [optional message]`
  - Example: `/kudos @alice great work on the PR!`
  - Posts kudos publicly on the issue/PR for everyone to see
  - Works with any GitHub username - no BLT account required!
  - If the recipient has a [BLT profile](https://owaspblt.org), kudos are automatically tracked there
  - If they don't have a BLT profile yet, they'll be encouraged to create one to track all their kudos
  - Works on both issues and pull request comments

- **Send Tips**: Comment `/tip @username $amount`
  - Example: `/tip @contributor $10`
  - Generates a direct link to the contributor's GitHub Sponsors page
  - Supports any amount (e.g., `$5`, `$10.50`, `$100`)
  - Validates that the recipient has GitHub Sponsors enabled
  - Provides clear instructions for completing the one-time payment
  - Works on both issues and pull request comments
  - Note: Due to GitHub API limitations, tips cannot be sent automatically and require manual completion on the GitHub Sponsors page

#### Automated Features
- **Stale Issue Unassignment**: If an issue remains inactive for 24 hours without a linked pull request, the action automatically:
  - Unassigns the user
  - Removes the "assigned" label
  - Posts a notification that the issue is available again
  - Runs daily via scheduled workflow (cron: `'0 0 * * *'`)
  - Can also be triggered manually via workflow_dispatch
  - Checks issue timeline for cross-referenced PRs to prevent premature unassignment
  - Avoids duplicate unassignment notifications

- **Assignment Protection**: Users cannot be assigned to new issues if they have existing assigned issues without open pull requests.
  - Lists all blocking issues in the response message
  - Prevents users from hoarding issues without active work

- **Duplicate Assignment Prevention**: The action prevents multiple users from being assigned to the same issue and notifies if an issue is already claimed.

## Implementation Details

### Attribution
All comments generated by the BLT-Action include an attribution footer:
```
---
*This comment was generated by [OWASP BLT-Action](https://github.com/OWASP-BLT/BLT-Action)*
```
This ensures transparency and helps users understand that comments are automated.

### Event Triggers
The action responds to the following GitHub events:
- `issue_comment.created`: For commands on issue and PR comments
- `pull_request_review_comment.created`: For commands on PR review comments
- `schedule`: Daily cron job for stale issue checking
- `workflow_dispatch`: Manual trigger option

### Label Management
The action automatically manages an "assigned" label:
- Added when a user is successfully assigned to an issue
- Removed when a user is unassigned (manually or automatically)
- Used to track which issues are actively claimed

### API Integrations
- **GitHub API**: Uses `@actions/github` with the provided `GITHUB_TOKEN` for all GitHub operations
- **Giphy API**: Requires a free API key from https://developers.giphy.com/
- **OWASP BLT Team API**: Sends kudos data to https://owaspblt.org/teams/give-kudos/

## Contributing

Contributions are what make the open-source community an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. **Find an Issue**:
   - Check the [issues page](../issues) of the BLT-Action repository.
   - Choose an issue you would like to work on.

2. **Fork the Project**:
   - Fork the repository to your GitHub account.

3. **Create your Feature Branch**:
   - `git checkout -b feature/AmazingFeature`

4. **Commit your Changes**:
   - `git commit -m 'Add some AmazingFeature'`

5. **Push to the Branch**:
   - `git push origin feature/AmazingFeature`

6. **Open a Pull Request**:
   - Once you've pushed your new branch, create a new Pull Request from your forked repository to the original BLT-Action repository.

