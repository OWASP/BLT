# BLT-Next

BLT-Next is the user-facing frontend application for the OWASP BLT platform.

## Current repository status

The current repository is [owasp-blt/blt-next](https://git.owaspblt.org/BLT/BLT-Next).

## Purpose

BLT-Next serves the primary BLT product experience at `next.owaspblt.org`. It combines a static-asset frontend with a Python Cloudflare Worker that handles application routes. This is the hybrid Worker application deployment pattern described in [Platform Architecture](../developer-guide/platform-architecture.md).

API contracts, data persistence, and authentication implementation are owned by BLT-Next and BLT-API together. BLT-docs does not restate exact request or response contracts; confirm current behavior in the owning repository before changing code.

## Best starting points

Contribute here when the work involves:

- Frontend layout, styling, and user-facing product workflows.
- Worker routes that render or serve the BLT-Next application.
- Client-side integration with BLT-API endpoints.
- Repository-owned build and deployment configuration.

## Local development notes

Use the BLT-Next repository's own README, `package.json` scripts, and `wrangler.toml` for local development. Do not rely on commands copied from BLT-docs or other BLT repositories unless BLT-Next also documents them.

Keep local environment files and secrets out of git. Use placeholder names for variables in documentation, not real values.

## Documentation notes

Keep BLT-docs focused on BLT-Next's role in the platform, its deployment pattern, and its ownership boundary with BLT-API. When frontend behavior or Worker routes change, update the BLT-Next repository first or in the same pull request as any BLT-docs update.

## Documentation boundaries

BLT-Next should own exact build commands, Worker route behavior, frontend architecture, and deployment details. BLT-docs should not become a duplicate frontend reference or restate authentication implementation details that belong in BLT-Next or BLT-API.

## Related pages

- [Platform Architecture](../developer-guide/platform-architecture.md)
- [BLT-API](blt-api.md)
- [Contributing](../developer-guide/contributing.md)
