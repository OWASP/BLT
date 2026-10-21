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
| `/_shared/blt-nav.js` | the OWASP BLT top bar every BLT site loads (see below); it, `/_home/blt-logo.svg`, `/_home/logos/*` and `/_home/symbols/*` are sent with `Cross-Origin-Resource-Policy: cross-origin` |
| `/_shared/blt-analytics.js` | the shared analytics loader (see "Analytics"); the top bar loads it, sent with the same cross-origin headers |
| `/api/home-stats` | live numbers as JSON, cached for 15 minutes |
| legacy Django paths (`/issue/…`, `/profile/…`, `/api/v1/…`, `/static/…`, … see `src/legacy.js`) | 308 to `https://next.owaspblt.org/moved?from=<path + query, URL-encoded>`, BLT-Next's "this page moved" page (the legacy app is off until its data is migrated) |
| anything else (`/pages/report-bug.html`, `/api/stats`, `/assets/…`, …) | 308 to the same path and query on `https://next.owaspblt.org` (BLT-Next) |

The legacy list is built from `blt-core/blt/urls.py` (or `blt-legacy/` after a rename); `test/legacy.test.mjs` fails if urls.py gains a route the list does not cover.

## Live numbers

`/api/home-stats` fetches these public sources server-side (the forge sends no CORS headers, so the browser cannot read it directly), caches the summary for 15 minutes, and returns `null` for any source that fails:

| Key | Source | Shown as |
|---|---|---|
| `forge` | `https://git.owaspblt.org/api/repo/owasp-blt/BLT/stats` | contributors (bots excluded), commits, open issues, and a 52-week commit heatmap with the last four weeks' total |
| `pool` | `https://pool.owaspblt.org/api/leaderboard` | this month's top three on the BLT-Pool leaderboard |
| `pages` | `https://pages.owaspblt.org/data/leaderboard.json` | bugs logged, once there is at least one |

The page inserts values with `textContent` only. A number whose source is down stays hidden; the page never shows a placeholder number.

## Changing the page

- **Banner:** the `<a id="announcement">` element near the top of `public/index.html`. Edit its text and `href`, or delete it.
- **Products:** the Explore cards in `public/index.html` are the single list; the tabs, the logo orbit and the apps menu are built from them. Logos are in `public/_home/logos/`: each is the project's `logo.svg`, a wasp badge made by `scripts/wasp-badges/build.mjs` (see its README; `npm test` checks they are current). Only projects with a live site belong here.
- **Shared top bar:** `public/_shared/blt-nav.js` is the one header of every other BLT site: `<script src="https://owaspblt.org/_shared/blt-nav.js" defer></script>` puts it at the top of the page (options are at the top of the file). A site configures it on a `<blt-nav>` element: `project` (slug; its plain round symbol is `/_home/symbols/<slug>.svg`), `name` (short name shown after the OWASP BLT brand) and `home`; its own links are the element's children (`slot="actions"` for buttons on the right, `data-primary` for the red one), so the site's scripts keep working on them. Example:
  ```html
  <blt-nav project="blt-zero" name="Zero" data-sticky>
    <a href="/" aria-current="page">Submit</a>
    <a href="/docs/security">Security</a>
    <a href="https://git.owaspblt.org/BLT/BLT-Zero" slot="actions" data-primary>Contribute</a>
  </blt-nav>
  ```
  Without children it shows the OWASP BLT links (and, on a `*.owaspblt.org` site in its list, that project's symbol and name). Its `APPS` list must match the Explore cards; `npm test` checks that, so update both together.
- **Project symbols:** `public/_home/symbols/` holds each project's own round symbol without the wasp badge (written by `scripts/wasp-badges/build.mjs` from `scripts/wasp-badges/symbols/`). The top bar's project part and both apps choosers use them; the Explore cards and project logos keep the wasp badges in `public/_home/logos/`.
- **Analytics:** see "Analytics" below.
- **Styles:** Tailwind is compiled once, so there is no CDN at runtime. After changing classes, run:

```bash
npm install
npm run build:css   # writes public/_home/home.css
```

## Analytics

Every BLT site is measured with the forge's own first-party **Analytics** package on git.owaspblt.org; there is no third-party analytics (PostHog was removed in October 2026). `public/_shared/blt-analytics.js` loads the SDK from `https://git.owaspblt.org/analytics-sdk.js` and sends to `https://git.owaspblt.org/api/analytics/_/capture`:

- **Where it runs:** `blt-nav.js` loads it, so every site with the shared top bar is counted. This page and the sites without the bar load it with `<script src="https://owaspblt.org/_shared/blt-analytics.js" defer></script>`. `data-analytics="off"` on either tag turns it off for that page.
- **What it sends:** pageviews, page leaves (time on page, scroll depth) and web vitals. URLs and referrers lose their query string and `#fragment`. No autocapture, heatmaps, session recordings, surveys or error reports. Pages may add their own events with `window.bltTrack(name, properties)` (queued until the SDK loads, dropped when analytics is off).
- **Privacy:** no cookies; an anonymous visitor id and the send queue live in the site's `localStorage`. Nothing loads when the browser sends Do Not Track or Global Privacy Control, or on localhost. The forge stores no IP address (only a two-letter country).
- **CSP:** a site with a Content-Security-Policy needs `https://git.owaspblt.org` in `script-src` and `connect-src` (this page's is in `src/app.js`).
- **Key:** `KEY` in `blt-analytics.js` is the write key of the "OWASP BLT sites" project (git.owaspblt.org, Dashboard, Analytics, owasp-blt). Write keys are public; the project's allowed origins limit which sites may send. With `KEY` empty the file does nothing.

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
