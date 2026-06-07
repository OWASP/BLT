# BLT-API

BLT-API is the API service and platform integration layer for OWASP BLT.

## Current repository status

The current repository is [owasp-blt/blt-api](https://gitlab.com/owasp-blt/blt-api).

## Purpose

BLT-API owns API behavior and integration points for the BLT platform. Current documentation direction references Python on Cloudflare Workers and Cloudflare D1 where those are used by the API repository, but exact runtime, database, and deployment details should be confirmed in BLT-API before changing code.

The `/v2` API path is the current API documentation direction. Do not document unstable endpoints as final until the owning repository treats them as stable.

## Best starting points

Contribute here when the work involves API behavior, API tests, request or response contracts, platform integrations, API access gates, or database-backed API changes.

Good first review areas include:

- API documentation that needs to distinguish stable `/v2` behavior from exploratory endpoints.
- Tests for documented API behavior.
- Clarifying access control and identity documentation.
- Repository-local setup notes maintained by the API repository.

## Local development notes

Use the BLT-API repository's own README, configuration files, and test instructions for local development. Do not rely on commands copied from BLT-docs or older GitHub-era pages unless the current repository still documents them.

Keep local environment files and secrets out of git. Use placeholder names for variables in documentation, not real values.

## Migrations

Database or schema migrations belong in BLT-API. When documenting migration-related work, keep BLT-docs at the concept level and link contributors to the API repository for exact commands.

Migration notes should explain:

- What data or schema area is affected.
- Whether the change is local-only, staging, or production-facing.
- What verification was run.
- How rollback or remediation should be handled by maintainers.

Do not publish production database identifiers, credentials, or one-off operational commands in BLT-docs.

## Dashboard and API exploration

Use repository-owned tools, dashboards, or API exploration pages when BLT-API provides them. BLT-docs can describe how contributors should approach exploration, but endpoint catalogs and request examples should stay close to the API code unless they are stable user-facing documentation.

For `/v2`, document stable concepts and routes only after maintainers confirm they are ready. Label experimental or migration-era API notes clearly.

## API access and identity concepts

`X-BLT-API-Key` should be described as an API access gate for protected API access. It is separate from user identity.

JWT or session concepts represent user identity or authenticated user flows where the application uses them. Do not treat an API key as a user session, and do not describe JWT/session implementation details unless BLT-API currently documents those details.

## Documentation notes

Keep BLT-docs focused on contributor-facing API concepts, architecture boundaries, and stable documentation conventions. When API behavior changes, update the API repository first or in the same merge request as any BLT-docs update.

## Documentation boundaries

BLT-API should own exact setup commands, endpoint behavior, migration commands, test commands, and deployment details. BLT-docs should not become a replacement API reference for unstable endpoints or repository-owned operations.

## Related pages

- [Platform Architecture](../developer-guide/platform-architecture.md)
- [Contributing](../developer-guide/contributing.md)
- [Documentation Maintenance](../developer-guide/docs-maintenance.md)
