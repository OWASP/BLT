# Website Monitor

A simple GitHub Actions-based website monitoring solution that checks website availability and content every 5 minutes, providing a visual dashboard with a compact list view and detailed monitor pages.

## Features

- **Multi-Monitor Support**: Monitor multiple websites from a single dashboard
- **Compact List View**: Homepage shows all monitors at a glance with sparkline charts
- **Detailed Monitor Pages**: Click any monitor for comprehensive status information
- Monitors website availability every 5 minutes
- Checks for specific keywords in website content
- Maintains a 30-day history of response times and keyword status
- Visual dashboard with response time charts
- Slack notifications for downtime and missing keywords
- Automatic updates via GitHub Pages
- Configurable websites and keywords via `monitors.json`

## Dashboard Structure

- **Homepage (`index.html`)**: Displays a compact list of all monitors with inline sparkline charts
- **Monitor Detail Page (`monitor.html`)**: Shows comprehensive information for a specific monitor
- **Configuration (`monitors.json`)**: Defines the monitors to track

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

5. **Configure Monitors**:
   - Edit the `monitors.json` file in the repository root
   - Add or modify monitor configurations:
     ```json
     [
       {
         "id": "owaspblt",
         "name": "OWASP BLT",
         "url": "https://owaspblt.org",
         "keyword": "OWASP"
       },
       {
         "id": "example",
         "name": "Example Site",
         "url": "https://example.com",
         "keyword": "Example"
       }
     ]
     ```
   - Each monitor requires:
     - `id`: Unique identifier (used in filenames)
     - `name`: Display name for the monitor
     - `url`: Website URL to monitor
     - `keyword`: Text to search for in the page content

6. **Configure Workflow (Optional)**:
   You can also configure the website URL and keyword in the workflow file:

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
- Run automatically every 5 minutes for each configured monitor
- Update the homepage at `https://<your-username>.github.io/<repository-name>/` with a compact list of all monitors
- Each monitor card shows:
  - Monitor name and URL
  - Current status (Up/Warning/Down)
  - Latest response time
  - Time since last check
  - Inline sparkline chart showing recent response times
- Click any monitor card to view detailed information
- Send Slack notifications when:
  - A website is down
  - A specified keyword is not found
- Maintain a 30-day history of response times and keyword status for each monitor

## Dashboard Features

### Homepage
The homepage (`index.html`) displays all monitors in a compact, easy-to-scan format:
- **Monitor Cards**: Each monitor appears as a clickable card
- **Status at a Glance**: Color-coded status badges (green=up, yellow=warning, red=down)
- **Sparkline Charts**: Small inline charts show response time trends
- **Quick Info**: See response time and last check time without clicking

### Monitor Detail Page
Click any monitor to see comprehensive information:
- Current configuration (website URL and keyword)
- Last check timestamp
- Current response time with min/max values
- Website status (up/down)
- Keyword status (found/not found)
- Full response time chart with 30-day history
- Recent checks table with detailed status
- Links to run workflow, edit config, and view raw data

## Manual Testing

You can manually trigger the monitor with custom configuration:
1. Go to the "Actions" tab in your repository
2. Select "Website Monitor" workflow
3. Click "Run workflow"
4. Optionally enter:
   - Website URL to monitor (defaults to DEFAULT_WEBSITE_URL)
   - Keyword to check for (defaults to DEFAULT_KEYWORD)
5. Click "Run workflow"

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