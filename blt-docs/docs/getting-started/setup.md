# Set up BLT-docs locally

This guide is for running and verifying the BLT documentation site. It is not a setup guide for BLT-API or other platform services.

## Prerequisites

- Git.
- Python.
- `uvx` or a compatible Python tool runner that can install from `requirements.txt`.

## Clone the repository

Use SSH if your GitLab account is configured for it:

```bash
git clone git@gitlab.com:owasp-blt/blt-docs.git
cd blt-docs
```

If SSH is not available, use HTTPS:

```bash
git clone https://gitlab.com/owasp-blt/blt-docs.git
cd blt-docs
```

## Build the site

Run a strict MkDocs build before submitting changes:

```bash
uvx --with-requirements requirements.txt mkdocs build --strict
```

The generated site is written to `site/`.

## Serve the site locally

Run the local development server:

```bash
uvx --with-requirements requirements.txt mkdocs serve -a 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/` in a browser. If port `8000` is already in use, stop the existing process or serve on another local port, such as `8001`:

```bash
uvx --with-requirements requirements.txt mkdocs serve -a 127.0.0.1:8001
```

## Editing guide

| Area | Where to edit |
| ---- | ------------- |
| Documentation pages | `docs/` |
| Site navigation | `mkdocs.yml` |
| Theme overrides | `docs/assets/stylesheets/blt-theme.css` |

Most documentation changes should only touch Markdown files under `docs/`. Update `mkdocs.yml` only when adding, moving, or removing pages from the navigation. Avoid theme changes unless the work item specifically requires them.

## Verification checklist

- Run `uvx --with-requirements requirements.txt mkdocs build --strict`.
- Confirm new or moved pages are linked from `mkdocs.yml` when they should appear in navigation.
- Check internal links from changed pages.
- Keep wording factual and avoid unsupported feature, deployment, or migration claims.
- Review the diff before opening a merge request.
