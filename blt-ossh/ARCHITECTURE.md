# BLT-OSSH Architecture

This project is a pure static web application hosted on Cloudflare from the `public/` directory.

## 📁 Project Structure

```
BLT-OSSH/
├── .github/
│   └── workflows/
│       ├── update-catalog.yml
│       └── update-profiles.yml
├── public/
│   ├── data/
│   │   ├── ossh_catalog.json
│   │   └── profiles.json
│   ├── static/
│   │   └── logo.png
│   ├── js/
│   │   └── app.js
│   ├── index.html
│   └── community.html
└── wrangler.toml
```

## 🏗️ Architecture Overview

The application is a static browser app served from `public/` that:

1. Renders the UI using Tailwind CSS (loaded from CDN)
2. Accepts a GitHub username from the user
3. Calls the **GitHub REST API** directly from the browser to fetch profile and repository data
4. Builds recommendations client-side from the API data
5. Renders the results dynamically via JavaScript

There is no server-side component — everything runs in the browser.

## 🔄 Request Flow

```
User enters username
       ↓
public/index.html (JavaScript)
       ↓
GET https://api.github.com/users/{username}
GET https://api.github.com/users/{username}/repos
       ↓
buildRecommendations() — client-side logic
       ↓
displayResults() — DOM update
```

## 🚀 Deployment

Cloudflare serves the checked-in `public/` directory directly. `wrangler.toml` declares the publish root for both Cloudflare Pages and Workers Static Assets style deploys:

```toml
pages_build_output_dir = "public"

[assets]
directory = "public"
```

GitHub Actions remain only for refreshing static JSON data under `public/data/`.

## 📝 Code Organization Principles

1. **No build step** — the site is pure HTML/CSS/JS; no bundler or transpiler needed
2. **Privacy-friendly** — no server logs, no cookies, no analytics
3. **GitHub API only** — all data comes from the public GitHub REST API
4. **Graceful degradation** — rate-limit and 404 errors are surfaced to the user

## 📚 Further Reading

- [Cloudflare Pages Documentation](https://developers.cloudflare.com/pages/)
- [Cloudflare Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub REST API](https://docs.github.com/en/rest)
