# Documentation maintenance

## Local commands

Build the documentation with strict validation:

```bash
uvx --with-requirements requirements.txt mkdocs build --strict
```

Serve the documentation locally:

```bash
uvx --with-requirements requirements.txt mkdocs serve -a 127.0.0.1:8000
```

## Repository layout

| Path | Purpose |
| ---- | ------- |
| `docs/` | Source Markdown pages and documentation assets. |
| `mkdocs.yml` | MkDocs configuration, navigation, theme settings, plugins, and site metadata. |
| `docs/assets/stylesheets/blt-theme.css` | Project-specific theme overrides. Do not change styling during content-only documentation work. |
| `requirements.txt` | Python dependencies used by the documentation build. |
| `wrangler.toml` | Cloudflare Workers deployment configuration for the generated static site. |
| `site/` | Generated MkDocs output. Do not hand-edit generated files. |

## Adding or updating a page

1. Choose the correct section under `docs/`.
2. Create or edit a Markdown page with a single `#` title.
3. Use relative links for other documentation pages.
4. Add the page to `mkdocs.yml` if it should appear in navigation.
5. Run the strict build.
6. Review warnings and fix them before opening a merge request.

## Navigation rules

The visible navigation is controlled by `mkdocs.yml`. When a page is added, moved, renamed, or removed, update the matching `nav` entry in the same change.

Keep navigation labels short and stable. Prefer names that describe the page purpose rather than internal repository history. Do not add pages to navigation until they exist and build successfully.

## Style rules

- Use a professional, direct tone.
- Keep paragraphs short.
- Do not use emojis.
- Avoid unsupported product claims.
- Use stable links.
- Label historical or migration-pending repository locations clearly.
- Keep exact setup commands in the repository that owns the code unless the command is verified for BLT-docs.

## Link and content freshness checks

Check internal links whenever moving or renaming pages. Prefer relative links for documentation pages so local builds and deployed builds behave consistently.

For external repository links, use confirmed GitLab links for migrated repositories. Treat other GitHub repository links as historical or migration-pending unless maintainers confirm they are current.

When a page describes API behavior, deployment behavior, or automation, confirm the current behavior in the owning repository before documenting it as final.

## Build troubleshooting

MkDocs strict mode can fail for missing navigation files, broken internal links, invalid Markdown, invalid configuration, or plugin errors.

Common fixes:

- If a nav entry fails, confirm the file exists at the path listed in `mkdocs.yml`.
- If Markdown fails, check headings, code fences, tables, and indentation.
- If a local server fails because port `8000` is already in use, choose another local port, such as `127.0.0.1:8001`.
- If generated output looks stale, remove generated files only when you are sure they are build artifacts and rerun the build.
