# BLT-Action README

## Introduction

**BLT-Action** is an innovative GitHub Action designed to streamline the issue and pull request management process in GitHub repositories. It provides a powerful suite of features to automatically assign users to issues, track progress, engage contributors, and maintain an organized workflow.

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
- **Pull Request Detection**: Identifies cross-referenced open pull requests to avoid premature unassignment.
- **Duplicate Prevention**: Avoids creating duplicate unassignment notifications.

### Engagement Features
- **GIF Integration**: Post GIFs from Giphy using `/giphy [search term]` to add fun and personality to discussions.
- **Kudos System**: Send appreciation to contributors using `/kudos @username [optional message]` to recognize great work.

### Compatibility
- **Issue and PR Support**: Works on both issue comments and pull request review comments for maximum flexibility.

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
      issue_comment:
        types: [created]
      pull_request_review_comment:
        types: [created]
      schedule:
        - cron: '0 0 * * *'
      workflow_dispatch:
    
    jobs:
      auto-assign:
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
  
- **Send Kudos**: Comment `/kudos username [optional message]`
  - Example: `/kudos alice great work on the PR!`
  - Sends appreciation to the OWASP BLT platform
  - The username should be the recipient's BLT username (without @ symbol)
  - If the user doesn't have their GitHub account linked to BLT, they'll need to do so at https://owaspblt.org
  - Recognizes contributors for their efforts and tracks kudos on their BLT profile

#### Automated Features
- **Stale Issue Unassignment**: If an issue remains inactive for 24 hours without a linked pull request, the action automatically:
  - Unassigns the user
  - Removes the "assigned" label
  - Posts a notification that the issue is available again
  - Runs daily via scheduled workflow

- **Assignment Protection**: Users cannot be assigned to new issues if they have existing assigned issues without open pull requests.

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

