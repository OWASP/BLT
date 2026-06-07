# BLT project map

## How to use this page

Use this page to choose the right BLT module before starting work. The BLT ecosystem is being documented around a clearer modular structure, and each repository has a different purpose. Repository status matters: confirmed active repositories should be used for current work, while migration-pending or historical repositories should be treated carefully until maintainers confirm their role.

## Confirmed active repositories

| Project | Current repository | Purpose | Best for |
| ------- | ------------------ | ------- | -------- |
| BLT-docs | [gitlab.com/owasp-blt/blt-docs](https://gitlab.com/owasp-blt/blt-docs) | MkDocs documentation hub. | Docs, writing, information architecture, deployment docs. |
| BLT-API | [gitlab.com/owasp-blt/blt-api](https://gitlab.com/owasp-blt/blt-api) | API service and platform integration layer. | Python, Cloudflare Workers, D1, API design. |
| BLT-Jobs | [gitlab.com/owasp-blt/blt-jobs](https://gitlab.com/owasp-blt/blt-jobs) | Jobs/community portal and automation workflows. | Static site, jobs data, worker deployment. |

## Migration-pending or historical repositories

Some BLT repositories may still exist on GitHub while migration details are being confirmed. Treat those repositories as historical or migration-pending unless a maintainer, current issue, or current documentation page identifies them as active. Do not rewrite links from GitHub to GitLab unless the migration has been confirmed.

When documenting a migration-pending repository, make the status visible in the page title, introduction, or repository table. Avoid describing old repository metrics, badges, roadmap items, or feature lists as current platform behavior.

## Choosing where to contribute

| Contributor interest | Suggested starting repository |
| -------------------- | ----------------------------- |
| Documentation | BLT-docs |
| API/backend | BLT-API |
| Cloudflare deployment | BLT-API or BLT-Jobs, depending on the issue |
| Data/metadata | BLT-OWASP metadata/projects, after confirming the current source |
| User-guide writing | BLT-docs |
| Product/design docs | BLT-docs |
| Automation/jobs | BLT-Jobs |

## Before starting work

- Read the issue or work item.
- Confirm the current repository and branch.
- Keep changes small.
- Run repo-specific verification.
- Avoid rewriting migration-pending links without confirmation.
