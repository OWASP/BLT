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

`wrangler.toml` configures the `blt-docs` Worker to run `mkdocs build` and serve the resulting `./site` directory as static assets. Missing paths fall back to the site's `404-page` handling. Keep the file focused on this deployment metadata and asset configuration.

Do not commit secrets to `wrangler.toml`. Configure secrets and environment-specific values through the approved Cloudflare or project workflow.

## Environment variables

The docs site needs no environment variables to build. Page analytics come from the shared OWASP BLT top bar (the forge's own analytics, loaded from `owaspblt.org/_shared/`), so there is no analytics key to configure here.

## Custom domains

`docs.owaspblt.org` is a Cloudflare-managed custom domain routed to the `blt-docs` Worker. Domain ownership, DNS, and production routing changes are configured through Cloudflare and the approved project settings, not through files in this repository.

## Deployment checklist

- Build strict.
- Review the generated site locally if needed.
- Confirm environment variables are configured outside git.
- Deploy through the approved project workflow.
- Verify the homepage and key pages.

## Troubleshooting

If deployment output is missing pages, run the strict build locally and check `mkdocs.yml` navigation paths. If the deployed site serves stale content, confirm the latest build completed and that Cloudflare is serving the expected static assets directory.
