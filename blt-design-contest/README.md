# BLT Design Contest

Community design showcase for [OWASP BLT](https://owasp.org/www-project-blt/).

**View the Showcase:** deploy `public/` with Cloudflare Workers Static Assets.

## How it works

1. **Submit** – Open a new GitLab issue using one of the templates in `.gitlab/issue_templates/`. Fill in your name, upload a preview image, link your design file, and submit.
2. **Rate** – Anyone can leave a thumbs-up or other GitLab reaction on any submission issue.
3. **Showcase** – GitLab CI rebuilds the showcase pages into `public/` and deploys them to Cloudflare. Automatic timed rebuilds are not configured.

## Stack

| Layer | Technology |
|---|---|
| HTML | Pure HTML5 |
| CSS | Tailwind CSS (CDN) |
| Icons | Font Awesome 6 (CDN) |
| Build | Python 3 (`scripts/build_showcase.py`) |
| CI/CD | GitLab CI (`.gitlab-ci.yml`) + Cloudflare Wrangler |
| Hosting | Cloudflare Workers Static Assets (`public/`) |

## Local development.

```bash
# Generate all showcase HTML pages into public/
GITLAB_TOKEN=glpat-... python scripts/build_showcase.py

# Serve locally
python -m http.server 8080 --directory public
# open http://localhost:8080
```

## Cloudflare deployment

This repository is configured for Cloudflare Workers Static Assets. The generated
HTML files are served from `public/`.

```bash
npx wrangler deploy
```

## Brand

Follows the [BLT Official Style Guide](https://www.figma.com/file/2lfEZKvqcb4WxRPYEwJqeE/OWASP-BLT):

- Primary: `#E10101`
- Dark base: `#111827` · Dark surface: `#1F2937`
- Neutral border: `#E5E5E5`
