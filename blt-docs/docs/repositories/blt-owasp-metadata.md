# BLT-OWASP-metadata

BLT-OWASP-metadata is a supporting metadata module for OWASP project and repository data.

## Current repository status

The current repository location should be confirmed with maintainers before opening new work. Historical GitHub links may exist in older documentation, but migration status should be verified before using them as the source of truth.

## Purpose

This module supports metadata collection, normalization, and discovery workflows for OWASP projects and related repositories. It can help downstream BLT workflows reason about project attributes, repository metadata, and contributor discovery data.

## Best starting points

Contribute here when the work involves:

- OWASP project metadata fields.
- Metadata extraction or normalization.
- Data freshness checks.
- Documentation for generated metadata files.
- Integration notes for modules that consume metadata.

Before starting, confirm the current repository location and whether the work belongs in this module or another project catalog repository.

## Local development notes

Use the owning repository's README and scripts for local setup. Do not copy historical scraper commands into BLT-docs unless maintainers confirm they are current.

If a workflow requires API tokens for higher rate limits, document only the variable names and storage expectations. Do not include token examples or real values.

## Documentation notes

BLT-docs should document the module purpose, contribution boundaries, and how metadata supports the broader BLT platform. The repository README should own exact script commands, data schemas, generated file details, and automation schedules.

## Related pages

- [Platform Architecture](../developer-guide/platform-architecture.md)
- [Contributing](../developer-guide/contributing.md)
- [Writing Documentation](../developer-guide/writing-docs.md)
