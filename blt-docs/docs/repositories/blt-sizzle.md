# BLT-Sizzle

BLT-Sizzle is the organization check-in and daily contributor activity application for OWASP BLT.

## Current repository status

The current repository is [owasp-blt/blt-sizzle](https://git.owaspblt.org/BLT/BLT/tree/main/blt-sizzle).

## Purpose

BLT-Sizzle serves organization check-ins and related contributor activity at `sizzle.owaspblt.org`. It runs a Python Cloudflare Worker alongside static assets, persists data in Cloudflare D1, and runs a scheduled Worker trigger for reminders. This is an active service in the hybrid Worker application deployment pattern described in [Platform Architecture](../developer-guide/platform-architecture.md).

Secrets, the D1 database identifier, and migration commands remain in the BLT-Sizzle repository. BLT-docs does not publish those values.

## Best starting points

Contribute here when the work involves:

- Check-in and organization workflow pages or routes.
- D1 schema or data changes for check-in data.
- The scheduled reminder Worker trigger.
- Repository-owned build and deployment configuration.

## Local development notes

Use the BLT-Sizzle repository's own README, `package.json` scripts, and `wrangler.toml` for local development. Do not rely on commands copied from BLT-docs or other BLT repositories unless BLT-Sizzle also documents them.

Keep local environment files and secrets out of git. Use placeholder names for variables in documentation, not real values.

## Migrations

Database or schema migrations belong in BLT-Sizzle. When documenting migration-related work, keep BLT-docs at the concept level and link contributors to the BLT-Sizzle repository for exact commands.

Do not publish production database identifiers, credentials, or one-off operational commands in BLT-docs.

## Scheduled reminders

BLT-Sizzle runs a scheduled Worker trigger to check for users needing check-in reminders. Document the reminder role at a conceptual level; the exact schedule and notification logic are owned by the BLT-Sizzle repository and may change independently of this page.

## Documentation notes

Keep BLT-docs focused on BLT-Sizzle's role in the platform, its deployment pattern, and its ownership boundary for check-in data and reminders. When Worker routes, D1 schema, or the reminder schedule change, update the BLT-Sizzle repository first or in the same merge request as any BLT-docs update.

## Documentation boundaries

BLT-Sizzle should own exact build commands, Worker route behavior, D1 schema and migrations, the reminder schedule, and deployment details. BLT-docs should not become a duplicate operational reference for check-in data or scheduled jobs.

## Related pages

- [Platform Architecture](../developer-guide/platform-architecture.md)
- [BLT-API](blt-api.md)
- [Contributing](../developer-guide/contributing.md)
