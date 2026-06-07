# BLT documentation and platform transformation overview

## Purpose of the transformation

BLT is being documented around a clearer modular structure so contributors can understand where work belongs and how the platform pieces relate to each other. The goal is to move away from stale project dumps and toward focused documentation for BLT-docs, BLT-API, BLT-Jobs, repository metadata, and user workflows.

## Documentation goals

- Make BLT-docs the source of truth for contributor-facing documentation.
- Route contributors to the correct repository before they start work.
- Separate user workflows from developer and maintainer guidance.
- Keep API documentation grounded in the current BLT-API implementation.
- Label historical or migration-pending repositories clearly.
- Remove stale badges, unsupported metrics, and outdated feature claims.

## Platform direction

The BLT platform direction is modular. BLT-docs provides the documentation hub, BLT-API provides the API and integration layer, BLT-Jobs covers jobs and automation workflows, repository metadata helps organize project information, and user-guide pages explain common BLT workflows.

This structure should make it easier to maintain documentation without implying that every historical repository or proposed feature is active.

## Repository migration awareness

Confirmed GitLab repositories should be documented first. Current confirmed repositories include BLT-docs, BLT-API, and BLT-Jobs. Other repositories may still appear on GitHub while migration details are reviewed.

When a repository is migration-pending or historical, documentation should say so plainly. Do not replace links, rename repositories, or describe migration status as complete unless it has been confirmed.

## How contributors can use this plan

Contributors can use this plan to decide where to start, what to verify, and how to scope documentation changes. A good contribution should identify the relevant module, update only the pages needed for the work item, and run the repository's verification commands before review.

For documentation changes, start with the local setup guide, then use the project map to confirm the correct module and repository.

## Current priority areas

- Keep the public documentation entry points concise and accurate.
- Document confirmed GitLab repositories before migration-pending repositories.
- Update user-guide pages against current workflows.
- Expand BLT-API documentation only from confirmed implementation details.
- Add repository-specific setup and maintenance notes where they are missing.
- Remove stale proposal text, unsupported claims, and old repository metrics.
