# Website Monitor

A Cloudflare Python Worker website monitor. It checks website availability and
content every minute, stores recent history in Workers KV, and provides a
visual dashboard with a compact list view and detailed monitor pages.

## Features

- **Multi-Monitor Support**: Monitor multiple websites from a single dashboard
- **Compact List View**: Homepage shows all monitors at a glance with sparkline charts
- **Detailed Monitor Pages**: Click any monitor for comprehensive status information
- Monitors website availability every minute with a Cloudflare Cron Trigger
- Checks for specific keywords in website content
- Maintains the latest 30 checks in Workers KV for each monitor
- Visual dashboard with response time charts
- Slack notifications for downtime and missing keywords
- Deployable on Cloudflare Python Workers with static assets
- Configurable websites and keywords via `monitors.json`

## Dashboard Structure

- **Homepage (`public/index.html`)**: Displays a compact list of all monitors with inline sparkline charts
- **Monitor Detail Page (`public/monitor.html`)**: Shows comprehensive information for a specific monitor
- **Configuration (`public/monitors.json`)**: Defines the monitors to track

## Setup Instructions

1. **Clone or fork the [GitLab repository](https://gitlab.com/owasp-blt/blt-monitor)**

2. **Configure Slack Webhook (Optional)**:
   - Go to your Slack workspace
   - Create a new Slack App (https://api.slack.com/apps)
   - Enable Incoming Webhooks
   - Create a new webhook URL
   - Copy the webhook URL

3. **Deploy the Cloudflare Python Worker**:
   - Install [uv](https://docs.astral.sh/uv/) and Node.js
   - Install the Python Worker development dependencies:
     ```bash
     uv sync
     ```
   - Authenticate with Cloudflare:
     ```bash
     npx wrangler login
     ```
   - Start the local development server:
     ```bash
     uv run pywrangler dev
     ```
   - Deploy the dashboard:
     ```bash
     uv run pywrangler deploy
     ```
   - Wrangler automatically provisions the `HISTORY` KV namespace on the first
     deployment and adds its ID to `wrangler.toml`
   - The Worker serves the dashboard, exposes `/api/health`, and runs the
     monitor cron every minute
   - Optionally store the Slack webhook as a Worker secret:
     ```bash
     npx wrangler secret put SLACK_WEBHOOK_URL
     ```

4. **Configure Monitors**:
   - Edit the `public/monitors.json` file
   - Add or modify monitor configurations:
     ```json
     [
       {
         "id": "owaspblt",
         "name": "OWASP BLT",
         "url": "https://owaspblt.org",
         "keyword": "OWASP",
         "enabled": true
       },
       {
         "id": "example",
         "name": "Example Site",
         "url": "https://example.com",
         "keyword": "Example",
         "enabled": false
       }
     ]
     ```
   - Each monitor requires:
     - `id`: Unique identifier (used in routes and KV keys)
     - `name`: Display name for the monitor
     - `url`: Website URL to monitor
     - `keyword`: Text to search for in the page content
     - `enabled`: Set to `false` to pause checks without removing the monitor

5. **Configure Manual Runs (Optional)**:
   - Create an ingest token and store it as a Worker secret:
     ```bash
     npx wrangler secret put INGEST_TOKEN
     ```
   - Invoke an immediate monitor run with:
     ```bash
     curl --request POST \
       --header "Authorization: Bearer <INGEST_TOKEN>" \
       https://<your-worker-domain>/api/run
     ```

## Usage

Once set up, the monitor will:
- Run automatically every minute for each configured monitor
- Store the latest 30 checks for each monitor in Workers KV
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
- Maintain recent response time and keyword status history for each monitor

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
- Full response time chart with recent history
- Recent checks table with detailed status
- Links to view source and raw JSON data

## Manual Testing

Use the authenticated `/api/run` endpoint shown in the setup instructions to
trigger an immediate monitor run.

## Troubleshooting

- If dashboard data is not updating, check the Worker Cron Events and logs in
  the Cloudflare dashboard
- Ensure the optional Slack webhook URL is set as a Worker secret
- Check that the target website allows automated monitoring
- Verify the keyword exists in the website content
- Check if the website's content is dynamically loaded (which might not be detected)
- Ensure the website URL is properly formatted (include https:// or http://)

## Contributing

Feel free to submit issues and enhancement requests!
