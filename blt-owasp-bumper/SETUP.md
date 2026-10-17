# Setup Instructions

This guide will help you set up the OWASP Repository List Generator in your repository.

## Prerequisites

- Repository with GitHub Actions enabled
- Permissions to configure GitHub Pages

## Setup Steps

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click on **Settings**
3. Scroll down to **Pages** in the left sidebar
4. Under **Source**, select **GitHub Actions**
5. Click **Save**

### 2. Run the Workflow

The workflow will run automatically:
- **Daily** at 00:00 UTC
- **On push** to main branch (when `generate_repo_list.py` or `.github/workflows/generate-repo-list.yml` are modified)

To run it manually:
1. Go to the **Actions** tab
2. Select **Generate OWASP Repository List** workflow
3. Click **Run workflow** button
4. Select the branch (usually `main`)
5. Click **Run workflow**

### 3. Access Your Page

After the workflow completes successfully:
1. Go to **Settings** → **Pages**
2. You'll see a message: "Your site is live at `https://[your-username].github.io/[repository-name]/`"
3. Click the URL to view your generated repository list

## Configuration

### Change the Organization

To list repositories from a different GitHub organization:

1. Edit `.github/workflows/generate-repo-list.yml`
2. Change the `GITHUB_ORG` environment variable:
   ```yaml
   env:
     GITHUB_ORG: your-org-name  # Change 'owasp' to your organization
   ```

### Change Update Frequency

To change how often the list is updated:

1. Edit `.github/workflows/generate-repo-list.yml`
2. Modify the cron schedule:
   ```yaml
   schedule:
     - cron: '0 0 * * *'  # Daily at midnight UTC
   ```

Common schedules:
- `'0 */6 * * *'` - Every 6 hours
- `'0 0 * * 1'` - Weekly on Monday
- `'0 0 1 * *'` - Monthly on the 1st

## Troubleshooting

### Workflow Fails

If the workflow fails:
1. Go to **Actions** tab
2. Click on the failed workflow run
3. Review the error messages
4. Common issues:
   - GitHub API rate limit (wait an hour or add `GITHUB_TOKEN`)
   - GitHub Pages not enabled in repository settings

### Page Not Updating

If the page doesn't show new repositories:
1. Clear your browser cache
2. Check the workflow ran successfully
3. Verify the deployment step completed
4. Wait a few minutes for GitHub Pages to update

### Empty Repository List

If no repositories are shown:
1. Verify the organization name is correct
2. Check that the organization has public repositories
3. Ensure the GitHub token has access to read the organization

## Local Testing

To test the script locally:

```bash
# Set your GitHub token (optional, but recommended)
export GITHUB_TOKEN=your_personal_access_token

# Set the organization
export GITHUB_ORG=owasp

# Run the script
python3 generate_repo_list.py

# Open the generated index.html in your browser
open index.html  # macOS
xdg-open index.html  # Linux
start index.html  # Windows
```

## Support

For issues or questions:
- Open an issue in this repository
- Check existing issues for similar problems
- Review the workflow logs in the Actions tab