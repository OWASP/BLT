# Toasty GitHub Pages

This directory contains the GitHub Pages site for the Toasty project.

## Viewing the Site

Once GitHub Pages is enabled for this repository, the site will be available at:
`https://owasp-blt.github.io/Toasty/`

## Enabling GitHub Pages

To enable GitHub Pages for this repository:

1. Go to the repository settings on GitHub
2. Navigate to "Pages" in the left sidebar
3. Under "Build and deployment":
   - **Source**: Select "GitHub Actions"
4. The site will automatically deploy when changes are pushed to the main branch

## Local Development

To view the site locally, simply open `index.html` in your web browser:

```bash
cd docs
open index.html  # On macOS
# or
xdg-open index.html  # On Linux
# or
start index.html  # On Windows
```

Alternatively, you can use a simple HTTP server:

```bash
cd docs
python -m http.server 8000
# Then open http://localhost:8000 in your browser
```

## Files

- `index.html` - Main page with project information
- `styles.css` - CSS styling for the page
- `_config.yml` - GitHub Pages configuration
- `.nojekyll` - Tells GitHub Pages not to use Jekyll processing

## Updating the Site

To update the site, simply edit the HTML and CSS files in this directory and push to the main branch. The GitHub Actions workflow will automatically deploy the changes.
