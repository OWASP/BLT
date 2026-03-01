# BLT-OSSH Architecture

This project is a pure static web application hosted on GitHub Pages and deployed automatically via GitHub Actions.

## 📁 Project Structure

```
BLT-OSSH/
├── .github/
│   └── workflows/
│       └── deploy.yml      # GitHub Actions: build & deploy to GitHub Pages
├── static/
│   └── logo.png            # BLT logo asset
└── index.html              # Single-page application (HTML + CSS + JS)
```

## 🏗️ Architecture Overview

The application is a **single HTML file** (`index.html`) that:

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
index.html (JavaScript)
       ↓
GET https://api.github.com/users/{username}
GET https://api.github.com/users/{username}/repos
       ↓
buildRecommendations() — client-side logic
       ↓
displayResults() — DOM update
```

## 🚀 Deployment

Deployments are triggered automatically on every push to `main` via the GitHub Actions workflow (`.github/workflows/deploy.yml`):

1. **Checkout** — clone the repository
2. **Configure Pages** — set up GitHub Pages environment
3. **Prepare site files** — copy `index.html` and `static/` into `_site/`
4. **Upload artifact** — upload `_site/` as a Pages artifact
5. **Deploy** — publish the artifact to GitHub Pages

To enable GitHub Pages for the repository, go to **Settings → Pages** and set the source to **GitHub Actions**.

## 📝 Code Organization Principles

1. **No build step** — the site is pure HTML/CSS/JS; no bundler or transpiler needed
2. **Privacy-friendly** — no server logs, no cookies, no analytics
3. **GitHub API only** — all data comes from the public GitHub REST API
4. **Graceful degradation** — rate-limit and 404 errors are surfaced to the user

## 📚 Further Reading

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub REST API](https://docs.github.com/en/rest)
