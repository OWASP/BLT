# OWASP BLT Documentation

**Live Site:** [https://docs.owaspblt.org/](https://docs.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-Docs](https://git.owaspblt.org/BLT/BLT-Docs)

<p align="center"><img src="logo.png" alt="blt-docs logo" width="160" height="160"></p>

This repository contains the MkDocs Material source for OWASP Bug Logging Tool (BLT) documentation. It is the documentation hub for BLT user workflows, contributor guidance, repository routing, API notes, and platform maintenance references.

## Architecture

```text
Markdown -> MkDocs strict build -> site/ -> Cloudflare Workers Static Assets -> docs.owaspblt.org
```

`site/` is the generated MkDocs output. It is gitignored and must never be hand-edited; run the strict build to regenerate it. `wrangler.toml` identifies `site/` as the deployed static asset directory for Cloudflare Workers.

## Local development

Run a strict build before submitting documentation changes:

```bash
uvx --with-requirements requirements.txt mkdocs build --strict
```

Serve the site locally while editing:

```bash
uvx --with-requirements requirements.txt mkdocs serve -a 127.0.0.1:8000
```

## Repository layout

| Path | Purpose |
| ---- | ------- |
| `README.md` | Repository overview and local development commands. |
| `docs/index.md` | Documentation site homepage. |
| `docs/getting-started/` | Local setup, project map, and transformation context. |
| `docs/features/` | High-level BLT platform and feature overview. |
| `docs/user-guide/` | User-facing workflow documentation. |
| `docs/developer-guide/` | Contributor workflow and maintenance guidance. |
| `docs/repositories/` | Repository-specific notes for BLT modules. |
| `mkdocs.yml` | MkDocs configuration and navigation. |

## Contributing

Keep documentation changes small, verifiable, and easy to review. See [the contributing guide](docs/developer-guide/contributing.md) before opening a pull request.
