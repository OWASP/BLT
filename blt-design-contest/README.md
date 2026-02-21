# BLT Design Contest

Community design showcase for [OWASP BLT](https://owasp.org/www-project-blt/).

**[🎨 View the Showcase →](https://owasp-blt.github.io/BLT-Design-Contest/)**

## How it works

1. **Submit** – Open a new issue using the [Design Submission](../../issues/new?template=design-submission.yml) template. Fill in your name, upload a preview image, link your design file, and submit.
2. **Rate** – Anyone can leave a 👍 (or other) reaction on any submission issue.
3. **Showcase** – A GitHub Actions workflow automatically rebuilds `index.html` whenever a submission is opened/edited, and deploys it to GitHub Pages. The page reflects live reaction counts.

## Stack

| Layer | Technology |
|---|---|
| HTML | Pure HTML5 |
| CSS | Tailwind CSS (CDN) |
| Icons | Font Awesome 6 (CDN) |
| Build | Python 3 (`scripts/build_showcase.py`) |
| CI/CD | GitHub Actions (`.github/workflows/build.yml`) |
| Hosting | GitHub Pages (`gh-pages` branch) |

## Local development

```bash
# Generate index.html (needs GITHUB_TOKEN for > 60 API requests/hr)
GITHUB_TOKEN=ghp_... python scripts/build_showcase.py

# Serve locally
python -m http.server 8080
# open http://localhost:8080
```

## Brand

Follows the [BLT Official Style Guide](https://www.figma.com/file/2lfEZKvqcb4WxRPYEwJqeE/OWASP-BLT):

- Primary: `#E10101`
- Dark base: `#111827` · Dark surface: `#1F2937`
- Neutral border: `#E5E5E5`
