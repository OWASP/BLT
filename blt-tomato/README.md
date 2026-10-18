# BLT-Tomato

**Live Site:** [https://tomato.owaspblt.org/](https://tomato.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-Tomato](https://git.owaspblt.org/BLT/BLT-Tomato)

<p align="center"><img src="logo.png" alt="blt-tomato logo" width="160" height="160"></p>
Scripts related to projects mainly for high level OWASP project management
1) Funding site served from `public/`

## Cloudflare and the weekly refresh (Workers KV)

`wrangler.toml` deploys a Worker (`worker/index.js`) with `public/` as its static assets. Deploy
with `scripts/deploy.sh blt-tomato` from the monorepo root; test with `scripts/ci/test.sh blt-tomato`.

`.forkmesh/blt-tomato--scrape_funding.yml` runs every Friday at 18:00 UTC on git.owaspblt.org (also
on demand, and when the scraper changes). It runs `scripts/refresh-kv.sh`, which runs
`.github/scripts/funding/owasp_funding_yml_scraper.py` with `OUTPUT_DIR=public` and writes
`index.html` and `project_repos_links.json` into the Worker's KV namespace, unless the new list
has fewer than half as many projects as before. Nothing is committed and nothing is redeployed.
The Worker serves `/`, `/index.html` and `/project_repos_links.json` from KV and falls back to the
committed copies in `public/` (no longer updated) while KV has none. The workflow needs the
Actions secrets `GH_API_TOKEN`, `CLOUDFLARE_API_TOKEN` (Workers KV Storage: Edit) and
`CLOUDFLARE_ACCOUNT_ID`. Run it by hand from the Actions page of https://git.owaspblt.org/BLT
(workflow_dispatch).
