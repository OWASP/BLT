# BLT-Home

**Live Site:** [https://owaspblt.org/](https://owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-Home](https://git.owaspblt.org/BLT/BLT-Home)

The owaspblt.org landing page: what OWASP BLT is, live project numbers, a card for every BLT product with a live site, and how to get involved.

The design is by Md Kaif Ansari (GitLab owasp-blt/blt!1, "feat: add new homepage"), adapted with live data, an Explore grid, dark mode and accessibility fixes.

## What it serves

One Cloudflare Worker (`blt-home`) with static assets from `public/`. The Worker runs first for every request (`run_worker_first`):

| Path | Response |
|---|---|
| `/` | `public/index.html` |
| `/_home/*`, `/favicon.ico`, `/robots.txt` | static files from `public/` |
| `/api/home-stats` | live numbers as JSON, cached for 15 minutes |
| legacy Django paths (`/issue/…`, `/profile/…`, `/api/v1/…`, `/static/…`, … see `src/legacy.js`) | 308 to `https://next.owaspblt.org/moved?from=<path + query, URL-encoded>`, BLT-Next's "this page moved" page (the legacy app is off until its data is migrated) |
| anything else (`/pages/report-bug.html`, `/api/stats`, `/assets/…`, …) | 308 to the same path and query on `https://next.owaspblt.org` (BLT-Next) |

The legacy list is built from `blt-core/blt/urls.py` (or `blt-legacy/` after a rename); `test/legacy.test.mjs` fails if urls.py gains a route the list does not cover.

## Live numbers

`/api/home-stats` fetches these public sources server-side (the forge and BLT Monitor send no CORS headers, so the browser cannot read them directly), caches the summary for 15 minutes, and returns `null` for any source that fails:

| Key | Source | Shown as |
|---|---|---|
| `forge` | `https://git.owaspblt.org/api/repo/owasp-blt/BLT/stats` | contributors (bots excluded), commits, open issues |
| `pool` | `https://pool.owaspblt.org/api/leaderboard` | this month's top three on the BLT-Pool leaderboard |
| `monitor` | `https://monitor.owaspblt.org/api/histories` | BLT sites passing their latest check, median response time |
| `pages` | `https://pages.owaspblt.org/data/leaderboard.json` | bugs logged, once there is at least one |

The page inserts values with `textContent` only. A number whose source is down stays hidden; the page never shows a placeholder number.

## Changing the page

- **Banner:** the `<a id="announcement">` element near the top of `public/index.html`. Edit its text and `href`, or delete it.
- **Products:** the Explore cards in `public/index.html` are the single list; the tabs, the logo orbit and the apps menu are built from them. Logos are in `public/_home/logos/` (SVGs copied from each project folder, PNGs resized to 96 px WebP). Only projects with a live site belong here.
- **Styles:** Tailwind is compiled once, so there is no CDN at runtime. After changing classes, run:

```bash
npm install
npm run build:css   # writes public/_home/home.css
```

## Development

```bash
npx wrangler@4 dev   # http://localhost:8787
npm test             # node --test: routing, redirects, stats, page checks
```

## Cutover (owaspblt.org from blt-next to blt-home)

1. **Deploy blt-home:** `scripts/deploy.sh blt-home` (or the Deploy workflow). `wrangler.toml` has `workers_dev = true` and no routes, so this does not touch owaspblt.org.
2. **Preview** at `https://blt-home.<account>.workers.dev/`. Check the live numbers appear, and that `/pages/report-bug.html` goes to next.owaspblt.org and `/issue/1/` goes to next.owaspblt.org/moved?from=%2Fissue%2F1%2F.
3. **Move the custom domain:** in Cloudflare, Workers & Pages, remove `owaspblt.org` (and `www.owaspblt.org`, if it should follow) from the `blt-next` Worker's custom domains and add it to `blt-home`. `next.owaspblt.org` stays on blt-next.
4. **Rollback:** move the custom domain back to `blt-next`. blt-next is unchanged and keeps serving `next.owaspblt.org` throughout.
