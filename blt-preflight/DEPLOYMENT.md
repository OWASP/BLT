# Deployment

BLT-Preflight uses Cloudflare Pages to host the static site in the `public/` directory.

## Current Setup

The repository already includes a `wrangler.toml` file:

```toml
name = "blt-preflight"
compatibility_date = "2026-05-31"

[assets]
directory = "./public"
```

The static site entry point is:

```text
public/index.html
```

No build step is required because the site is already static HTML.

## Prerequisites

- Node.js and npm installed.
- Access to a Cloudflare account that can deploy this Pages project.

## Preview Locally

From the repository root, run:

```bash
npx wrangler pages dev public
```

This starts a local Cloudflare Pages preview using the files in `public/`.

## Log In To Cloudflare

Before deploying, authenticate Wrangler:

```bash
npx wrangler login
```

## Deploy To Cloudflare Pages

Deploy the `public/` directory:

```bash
npx wrangler pages deploy public --project-name=blt-preflight
```

If the Pages project does not exist yet, create it first:

```bash
npx wrangler pages project create blt-preflight --production-branch=main
```

After deployment, Wrangler prints the Cloudflare Pages URL.
