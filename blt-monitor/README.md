# Website Monitor

A simple GitHub Actions-based website monitoring solution that checks website availability and content every 5 minutes, providing a visual dashboard of uptime, response times, and keyword presence.

## Features

- Monitors website availability every 5 minutes
- Checks for specific keywords in website content
- Maintains a 30-day history of response times and keyword status
- Visual dashboard with response time chart
- Slack notifications for downtime and missing keywords
- Automatic updates via GitHub Pages
- Configurable website URL and keyword

## Setup Instructions

1. **Fork this repository** to your GitHub account

2. **Configure Slack Webhook**:
   - Go to your Slack workspace
   - Create a new Slack App (https://api.slack.com/apps)
   - Enable Incoming Webhooks
   - Create a new webhook URL
   - Copy the webhook URL

3. **Add Slack Webhook to GitHub Secrets**:
   - Go to your repository settings
   - Navigate to "Secrets and variables" > "Actions"
   - Click "New repository secret"
   - Name: `SLACK_WEBHOOK_URL`
   - Value: Paste your Slack webhook URL
   - Click "Add secret"

4. **Enable GitHub Pages**:
   - Go to your repository settings
   - Navigate to "Pages"
   - Under "Source", select "Deploy from a branch"
   - Select the "main" branch
   - Click "Save"

5. **Configure Website and Keyword**:
   You can configure the website URL and keyword in two ways:

   a. **Default Configuration**:
   - Edit the `.github/workflows/website-monitor.yml` file
   - Find the `env` section at the top of the file
   - Update the default values:
     ```yaml
     env:
       DEFAULT_WEBSITE_URL: 'https://owasp.org'  # Change this URL
       DEFAULT_KEYWORD: 'OWASP'                  # Change this keyword
     ```

   b. **Manual Run Configuration**:
   - Go to the "Actions" tab in your repository
   - Select "Website Monitor" workflow
   - Click "Run workflow"
   - Optionally enter:
     - Website URL to monitor (defaults to the value in DEFAULT_WEBSITE_URL)
     - Keyword to check for (defaults to the value in DEFAULT_KEYWORD)
   - Click "Run workflow"

## Usage

Once set up, the monitor will:
- Run automatically every 5 minutes using the default configuration
- Update the dashboard at `https://<your-username>.github.io/<repository-name>/`
- Send Slack notifications when:
  - The website is down
  - The specified keyword is not found
- Maintain a 30-day history of response times and keyword status

## Manual Testing

You can manually trigger the monitor with custom configuration:
1. Go to the "Actions" tab in your repository
2. Select "Website Monitor" workflow
3. Click "Run workflow"
4. Optionally enter:
   - Website URL to monitor (defaults to DEFAULT_WEBSITE_URL)
   - Keyword to check for (defaults to DEFAULT_KEYWORD)
5. Click "Run workflow"

## Dashboard Features

The dashboard shows:
- Current configuration (website URL and keyword)
- Last check timestamp
- Current response time
- Website status (up/down)
- Keyword status (found/not found)
- 30-day history chart with:
  - Green bars for successful checks with keyword found
  - Yellow bars for successful checks with keyword not found
  - Red bars for failed checks
  - Response time in seconds

## Troubleshooting

- If the dashboard isn't updating, check the GitHub Actions logs
- Ensure the Slack webhook URL is correctly set in repository secrets
- Verify GitHub Pages is enabled and configured correctly
- Check that the target website allows automated monitoring
- Verify the keyword exists in the website content
- Check if the website's content is dynamically loaded (which might not be detected)
- Ensure the website URL is properly formatted (include https:// or http://)

## Contributing

Feel free to submit issues and enhancement requests! 