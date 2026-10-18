# BLT-Toasty Deployment Guide

This document outlines the deployment process and infrastructure requirements for the BLT-Toasty project on Cloudflare Workers.

## 1. Prerequisites

Before deploying the application, ensure the following are installed and configured:

*   **Node.js**: Version 20 or higher.
*   **Python**: Version 3.13 or higher.
*   **Wrangler CLI**: Version 3 or higher.
*   **Cloudflare Account**: A Cloudflare account with the **Workers Paid** plan is strictly required for Python Workers, Vectorize, D1, and Durable Objects support.

## 2. Environment Matrix

The project utilizes three distinct environments defined in `wrangler.toml`:

| Environment | Worker Name              | D1 Database ID | Vectorize Index             |
| :---        | :---                     | :---           | :---                        |
| Development | `toasty-backend-dev`     | `...0003`      | `toasty-embeddings-dev`     |
| Staging     | `toasty-backend-staging` | `...0002`      | `toasty-embeddings-staging` |
| Production  | `toasty-backend-prod`    | `...0001`      | `toasty-embeddings`         |

All environments contain the following bindings:
*   **D1 Database**: `DB`
*   **Durable Objects**: `CONVERSATION_DO`, `RATE_LIMITER_DO`
*   **Vectorize**: `VECTORIZE`
*   **Analytics Engine**: `ANALYTICS`

## 3. Step-by-Step Provisioning

Follow these steps to provision the required Cloudflare infrastructure for a new environment (e.g., Production).

### Step 3.1: Create D1 Database
Create the D1 database and copy the generated ID into your `wrangler.toml`.
```bash
npx wrangler d1 create toasty-db
```

Apply all required migrations (0001 through 0009):
```bash
npx wrangler d1 migrations apply toasty-db --remote
```
The migrations include:
*   `0001_initial.sql` (triage_events, redaction_audit)
*   `0002_summaries.sql` (triage_summaries)
*   `0003_embedded_pending.sql`
*   `0004_duplicate_candidates.sql`
*   `0005_rationale.sql`
*   `0006_conversations.sql` (conversation_archive)
*   `0007_rate_limiter.sql`
*   `0008_shadow_predictions.sql`
*   `0009_fix_redaction_audit.sql`

### Step 3.2: Create Vectorize Index
Create the Vectorize index with the required 384 dimensions and cosine similarity metric:
```bash
npx wrangler vectorize create toasty-embeddings --dimensions=384 --metric=cosine
```

### Step 3.3: Durable Objects Configuration
Durable Objects are automatically provisioned via the configuration in `wrangler.toml`. The migration tags are handled automatically on deployment:
*   `tag v1`: Introduces `ConversationDO`
*   `tag v2`: Introduces `RateLimiterDO`

### Step 3.4: Static Assets (Frontend)
The application serves static assets from the `./docs` directory with `run_worker_first` enabled for API routes.
Once the frontend branch is merged, the static assets must be built prior to deployment:
```bash
cd frontend
npm ci
npm run build
cd ..
```

## 4. Secrets & Variables Configuration

### Environment Variables
The following environment variables must be configured in `wrangler.toml` per environment:
*   `FASTEMBED_URL`: The URL for the FastEmbed service.
*   `ENVIRONMENT`: The deployment environment name.
*   `LOG_LEVEL`: Application logging level.

### Secrets
Secrets must be securely set using the Wrangler CLI for each environment:

```bash
# Required for X-Gitlab-Token webhook verification (external GitLab projects that send webhooks)
npx wrangler secret put GITLAB_WEBHOOK_SECRET --env production

# RS256 public key (SPKI PEM) required for JWT verification
npx wrangler secret put MCP_PUBLIC_KEY --env production
```

For CI/CD pipelines, ensure the following repository secrets are configured:
*   `CLOUDFLARE_API_TOKEN`
*   `CLOUDFLARE_ACCOUNT_ID`

## 5. Local Development Setup

To test the complete setup locally, you can use Wrangler's local development server.

1.  Start the local development server:
    ```bash
    npx wrangler dev
    ```

2.  Run the Python test suite using `pytest`:
    ```bash
    pytest
    ```

## 6. Deployment Commands

Deploy to the respective environments using the following commands:

**Development:**
```bash
npx wrangler deploy --env development
```

**Staging:**
```bash
npx wrangler deploy --env staging
```

**Production:**
```bash
npx wrangler deploy --env production
```

*Note: There is no scheduled work (the GitLab shadow-mode job was removed). The [blt-cron](../blt-cron) dispatcher Worker still calls `POST /__scheduled` hourly with a shared secret (`npx wrangler secret put CRON_SECRET`); `on_scheduled` is a no-op. This Worker has no cron trigger (`[triggers] crons = []`).*

## 7. Verification Runbook

After deployment, verify the system's operational status by performing the following checks:

1.  **Health Check**: Access the root API endpoint or `/health` (if configured) to verify the worker is responsive and properly routing traffic.
2.  **Webhook Test**: Send a test payload to the Gitlab webhook endpoint, ensuring the `X-Gitlab-Token` header matches the `GITLAB_WEBHOOK_SECRET`. Check the Cloudflare Worker logs for a successful validation and triage event generation.
3.  **Dashboard Auth**: Verify that access to the static frontend assets and subsequent API calls correctly validates your JWT against the configured `MCP_PUBLIC_KEY`.
4.  **Cron Dispatch**: At the top of the hour, the blt-cron call to `POST /__scheduled` should answer `200 {"ok": true}`.
