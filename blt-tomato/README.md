# BLT-Tomato
Scripts related to projects mainly for high level OWASP project management
1) Funding site served from `public/`

## Cloudflare

This is a static Cloudflare site. The publish directory is `public/`, and
`wrangler.toml` points both Pages and Workers Static Assets at that folder.

## Manually Triggering the Workflow

The workflow can be manually triggered using the `workflow_dispatch` event. This allows you to run the workflow on demand without waiting for a push event to the `main` branch.

To manually trigger the workflow, follow these steps:
1. Go to the "Actions" tab in your GitHub repository.
2. Select the workflow you want to run.
3. Click on the "Run workflow" button.
4. Optionally, provide any required inputs and click "Run workflow" again.
