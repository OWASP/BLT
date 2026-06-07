# BLT feature overview

## What BLT provides

OWASP Bug Logging Tool (BLT) is a project ecosystem for reporting bugs, tracking issue activity, organizing contributor work, maintaining project metadata, and connecting related platform modules. The documentation should describe confirmed behavior clearly and avoid treating exploratory or historical ideas as live functionality.

BLT is documented as a set of related modules rather than a single repository. The main public documentation belongs in BLT-docs, API and integration details belong with BLT-API, jobs and automation workflows belong with BLT-Jobs, and repository metadata should be documented only when the current source is confirmed.

## User workflows

The user guide covers common BLT workflows from the perspective of someone using the platform:

- Reporting a bug with enough detail for review.
- Reviewing issue details, status, comments, and related activity.
- Creating an account, signing in, and managing account access.
- Viewing leaderboards, weekly activity, statistics, and profile pages.
- Browsing company, project, and bug hunt views where those pages are documented.
- Finding community pages such as member lists, invitations, and BLT TV references.

Some existing user-guide pages may describe older interface behavior. Treat those pages as workflow references until they are reviewed against the current platform.

## Contributor workflows

Contributor documentation should help people choose the right work area before editing code or docs:

- Use the project map to select the right repository for documentation, API, jobs, metadata, or user-guide work.
- Start from an issue, merge request, or clearly scoped work item.
- Keep documentation updates focused and verify them with a strict MkDocs build.
- Use BLT-API documentation for API behavior and integration details.
- Use BLT-Jobs documentation for jobs, community portal, and automation workflows.
- Follow repository-specific setup instructions when working outside BLT-docs.

## Platform modules

| Module | Current role | Documentation posture |
| ------ | ------------ | --------------------- |
| BLT-docs | MkDocs documentation hub for user, contributor, repository, and maintenance documentation. | Confirmed active GitLab repository. |
| BLT-API | API service and platform integration layer for BLT. | Confirmed active GitLab repository; document behavior from implementation. |
| BLT-Jobs | Jobs/community portal and automation workflow module. | Confirmed active GitLab repository; keep setup and deployment notes specific to this module. |
| BLT-OWASP metadata/projects | Repository and project metadata used to organize BLT and OWASP project information. | Document only confirmed sources and label migration status clearly. |
| Legacy/historical UI docs | Existing user-facing pages that may describe earlier BLT interface behavior. | Preserve useful workflow context, but verify before presenting as current behavior. |

## API and integration direction

BLT-API is the API layer for the platform. Documentation should explain confirmed concepts and avoid promising endpoints, integrations, or deployment behavior that has not been checked against the current implementation.

API docs should distinguish API-key access from user identity, browser session, and JWT concepts. If a page describes authentication or authorization, it should state which access model it is describing and where the behavior is implemented.

## Current and planned documentation scope

| Scope | What belongs here | Documentation posture |
| ----- | ----------------- | --------------------- |
| Current documented | BLT-docs setup, contributor routing, high-level feature overview, and existing user-guide workflows. | Keep accurate, concise, and linked from navigation. |
| In progress | API documentation, repository-specific setup notes, jobs automation notes, and platform architecture explanations. | Ground each page in confirmed repository behavior before expanding. |
| Needs confirmation | Historical GitHub repositories, older UI pages, advanced integrations, rewards, scanners, and deployment claims. | Label as historical or migration-pending until confirmed by maintainers or current code. |
