# OWASP BLT Documentation

OWASP Bug Logging Tool (BLT) is an open source OWASP project for reporting, tracking, and improving security-related issues across websites, applications, and community projects. This documentation site explains how the BLT ecosystem is organized, how contributors can get started, and how the current platform modules fit together.

BLT-docs is the documentation hub for the project. It covers user workflows, contributor guidance, repository routing, API documentation, and platform maintenance notes.

## Start here

<div class="grid cards" markdown>

-   **Set up the docs locally**

    Run the MkDocs site, validate changes, and understand the repository layout.

    [Open the setup guide](getting-started/setup.md)

-   **Choose a project**

    Find the right BLT repository based on whether you want to work on docs, APIs, jobs, platform data, or user-facing workflows.

    [Open the project map](getting-started/projects.md)

-   **Contribute safely**

    Learn the expected contribution workflow, review checklist, and documentation standards.

    [Open the contributing guide](developer-guide/contributing.md)

-   **Understand the platform**

    Read how BLT user workflows, API services, background jobs, and documentation work together.

    [Open the feature overview](features/overview.md)

</div>

## What you can find here

| Area | Use it for |
| ---- | ---------- |
| Getting Started | Local setup, project map, and proposal context. |
| Features | High-level description of BLT capabilities and current platform direction. |
| User Guide | Page-by-page guidance for common BLT workflows. |
| Developer Guide | Contributor workflow, platform architecture, docs maintenance, and deployment notes. |
| Repositories | Repository-specific notes for active BLT modules. |

## Current documentation priorities

The BLT ecosystem is moving toward a clearer, more modular platform structure. The documentation is being updated to reflect that direction:

- Keep BLT-docs as the source of truth for contributor-facing documentation.
- Document confirmed GitLab repositories first.
- Separate user documentation from developer and maintainer documentation.
- Keep API details grounded in the current BLT-API implementation.
- Remove stale README content, broken badges, and outdated repository lists.

## Contributing to these docs

Documentation changes should be small, verifiable, and easy to review. Before opening a merge request, run a strict MkDocs build locally and check that new pages are linked from the navigation when needed.

[Read the contributing guide](developer-guide/contributing.md)
