# BLT Ideas

**Live Site:** [https://ideas.owaspblt.org/](https://ideas.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT/tree/main/blt-ideas](https://git.owaspblt.org/BLT/BLT/tree/main/blt-ideas)

BLT Ideas is a collection of brainstorming proposals for potential future development of [OWASP BLT](https://git.owaspblt.org/BLT/BLT/tree/main/blt-core). Each idea is scoped to a standalone 350-hour development slot and represents community-driven direction — not official project commitments.

For the full list of ideas, descriptions, differentiation guide, and hours analysis, visit the deployed Cloudflare Worker.

For detailed written documentation, see [DETAILS.md](DETAILS.md).

## Cloudflare Workers deployment

The site is served by a Cloudflare Python Worker. Deploy it with:

```sh
npx wrangler deploy
```

Wrangler runs `python scripts/generate_page.py` before each deployment and uploads the generated `dist/` assets. Set `GITHUB_TOKEN` when deploying to include GitHub discussion participants and upvotes.

For a repository connected in the Cloudflare dashboard, set the build command to `python scripts/generate_page.py` and leave the deploy command as `npx wrangler deploy`. Cloudflare hosted Builds does not run Wrangler custom build hooks.
