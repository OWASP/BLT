# BLT Blog

**Live Site:** [https://blog.owaspblt.org/](https://blog.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-Blog](https://git.owaspblt.org/BLT/BLT-Blog)

<p align="center"><img src="logo.svg" alt="blt-blog logo" width="160" height="160"></p>

The OWASP BLT blog: news, release notes and contributor stories, written as Markdown files in this folder and built into a static site.

## Write a post

Add a Markdown file to `posts/`, named `YYYY-MM-DD-short-title.md`, and open a pull request:

```markdown
---
title: "What we shipped this week"
date: "2026-11-07"
author: "Your Name"
author_url: "https://git.owaspblt.org/@you"
description: "One or two sentences for the home page, link previews and the feed."
tags: ["release", "owasp"]
cover: "/images/what-we-shipped-this-week/cover.png"
---

Your post, in Markdown.
```

- `title`, `date` and `author` are required. The page lives at `/<slug>/`; the slug comes from the title unless you set `slug`.
- Put images in `public/images/<slug>/` and link them as `/images/<slug>/name.png`. A cover is shown at 1000×420.
- `draft: true` keeps a post out of the build.
- A post first published somewhere else sets `canonical` to that address, so search engines credit the original.

Preview it:

```bash
npm ci
npm run build
python3 -m http.server 8787 --directory dist
```

## Posts from dev.to

The blog started on [dev.to/owaspblt](https://dev.to/owaspblt). `scripts/import_devto.py` copied those posts into `posts/devto/`, as dev.to's rendered HTML with scripts and event handlers removed, and saved their images under `public/images/`. Each one keeps its author and its canonical address on dev.to (or wherever it was first published) and says where it came from. Run it again to pick up new or edited posts there:

```bash
python3 scripts/import_devto.py
```

The blog that was built into the old BLT web app (blt.owasp.org/blog/, removed in February 2026) kept its posts in that app's database. Those posts aren't in this repository; they can only come back from a web archive.

## How it works

`scripts/build.mjs` reads `posts/` (Markdown through [marked](https://marked.js.org/), or HTML as it is) and writes `dist/`: the home page, a page per post and per tag, `feed.xml`, `sitemap.xml`, `robots.txt` and `404.html`, plus everything in `public/`. Pages use the shared OWASP BLT top bar (`<blt-nav>`) and the BLT colors, with light and dark mode.

Cloudflare serves `dist/` as Workers static assets on blog.owaspblt.org (`wrangler.toml`). From the repository root:

```bash
scripts/deploy.sh blt-blog
```

## Tests

```bash
npm test
```
