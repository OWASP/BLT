# Deployment

## Deployment model

BLT-docs is a static documentation site. MkDocs builds the Markdown source into the `site/` directory, and Cloudflare Workers Static Assets serves the generated site.

The `wrangler.toml` file records deployment metadata and points Cloudflare Workers to the generated assets. It should not contain account IDs, API tokens, or other secrets.

## Build locally

Run a strict local build before deployment:

```bash
uvx --with-requirements requirements.txt mkdocs build --strict
```

## Wrangler configuration

`wrangler.toml` controls the worker name, compatibility date, build command, and static asset directory for deployment. Keep it focused on deployment metadata and asset configuration.

Do not commit secrets to `wrangler.toml`. Configure secrets and environment-specific values through the approved Cloudflare or project workflow.

## Environment variables

`mkdocs.yml` references `GOOGLE_ANALYTICS_KEY` as an environment variable for Google Analytics configuration. Do not place a literal analytics key in `mkdocs.yml` or any committed file.

## Custom domains

Custom domains are configured through Cloudflare and the approved project settings. Keep domain ownership, DNS, and production routing changes in the deployment workflow used by maintainers.

## Deployment checklist

- Build strict.
- Review the generated site locally if needed.
- Confirm environment variables are configured outside git.
- Deploy through the approved project workflow.
- Verify the homepage and key pages.

## Troubleshooting

If deployment output is missing pages, run the strict build locally and check `mkdocs.yml` navigation paths. If analytics is not active, confirm `GOOGLE_ANALYTICS_KEY` is configured in the deployment environment without committing the value. If the deployed site serves stale content, confirm the latest build completed and that Cloudflare is serving the expected static assets directory.
