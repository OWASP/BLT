# BLT-Jobs

BLT-Jobs is the jobs and community portal module for the OWASP BLT ecosystem.

## Current repository status

The current repository is [owasp-blt/blt-jobs](https://git.owaspblt.org/BLT/BLT-Jobs).

## Purpose

BLT-Jobs supports jobs, community contribution flows, and related automation workflows. It serves static assets directly, with no Worker code, and is the Git-native static content deployment pattern described in [Platform Architecture](../developer-guide/platform-architecture.md).

Do not assume historical GitHub Pages or GitHub Actions details are still current unless the BLT-Jobs repository confirms them.

## Best starting points

Contribute here when the work involves:

- Job or community portal pages.
- Job data format or publishing workflows.
- Automation that updates job or profile data.
- Repository-owned deployment and build configuration.
- Documentation for contributors maintaining the jobs portal.

## Local development notes

Use the BLT-Jobs repository's own README and configuration files for setup, build, and deployment commands. Keep BLT-docs focused on the module purpose, ownership, and documentation boundaries.

Do not commit credentials, webhook URLs, API keys, or local environment files while working on jobs automation.

## Documentation notes

BLT-docs should describe the role of BLT-Jobs in the broader platform and point contributors to the current repository. The BLT-Jobs README should own exact local commands, deployment workflow details, data file formats, and automation behavior.

If the jobs workflow changes, update BLT-Jobs first or in the same pull request as any BLT-docs update.

## Related pages

- [Platform Architecture](../developer-guide/platform-architecture.md)
- [BLT-Sizzle](blt-sizzle.md)
- [Contributing](../developer-guide/contributing.md)
- [Deployment](../developer-guide/deployment.md)
