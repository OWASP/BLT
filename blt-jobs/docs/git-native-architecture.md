# BLT-Jobs Git-native architecture

BLT-Jobs is a Git-native job platform for open-source and security communities.

The core product contract is simple:

> Jobs and job seekers are Git-managed open data.

The repository is the database, Markdown is the data model, Git history is the audit log, Git hosting is the workflow engine, and Cloudflare serves the generated static frontend.

## Goals

- Keep job listings and seeker profiles portable, reviewable, and forkable.
- Make every published record traceable to a file, commit, issue, or merge request.
- Preserve a static hosting model with no application database requirement.
- Treat GitLab as the first polished provider while keeping GitHub and generic Git-compatible providers easy to add later.
- Make public-data and privacy boundaries explicit before adding application workflows.

## Non-goals

- BLT-Jobs is not a random crawler that republishes jobs from the internet.
- BLT-Jobs is not a proprietary hiring dashboard with a hidden database.
- BLT-Jobs should not collect private applicant data in public Git by default.
- BLT-Jobs should not require a centralized backend before a feature can be useful.

A user-submitted job URL may still be useful, but only as an input for generating a reviewable Git submission draft. It should not imply automatic scraping and publication.

## System model

```text
GitLab issue or merge request
        |
        v
Maintainer review
        |
        v
Markdown source files in the repository
        |
        v
npm run build:jobs
        |
        v
Generated static JSON under public/data/
        |
        v
Static HTML/CSS/JS frontend under public/
        |
        v
Cloudflare Workers static asset hosting
```

Current source paths:

| Data | Canonical source | Generated output | Public pages |
| --- | --- | --- | --- |
| Job listings | `jobs/*.md` | `public/data/jobs.json` | `public/jobs.html`, `public/job.html` |
| Seeker profiles | `seekers/*.md` | `public/data/seekers.json` | `public/seekers.html`, `public/seeker.html` |
| Static site | `public/` | committed site assets | Cloudflare Workers |

The generated JSON is a build artifact derived from Markdown. If Markdown and JSON disagree, Markdown is the source of truth and the JSON should be regenerated.

## Repository as database

BLT-Jobs intentionally stores public platform data in Git instead of a private database.

This gives the platform:

- transparent review through issues and merge requests;
- durable history through commits;
- easy rollback through Git;
- portable forks and mirrors;
- simple static deployment;
- contributor-friendly local development.

The tradeoff is that repository data is public by default. Anything sensitive must stay out of public Markdown files unless the contributor explicitly chooses to publish it.

## Markdown as the canonical data model

Each job or profile is a Markdown document with structured YAML frontmatter and freeform Markdown body content.

The frontmatter is for fields the frontend can filter, sort, validate, and display consistently. The body is for human-readable detail.

Current job fields include:

- `organization_name`
- `organization_logo`
- `title`
- `location`
- `job_type`
- `salary_range`
- `expires_at`
- `application_email`
- `application_url`
- `application_instructions`
- `created_at`
- `added_by`
- `added_by_url`
- `needs_manual_review`

Current seeker fields include:

- `name`
- `headline`
- `location`
- `skills`
- `experience_years`
- `experience_summary`
- `profile_url`
- `availability`
- `github`
- `gitlab`
- `linkedin`
- `portfolio`
- `email`
- `twitter`
- `resume_url`
- `created_at`

Future schema work should add richer fields for provider traceability, review state, organization profiles, public contact preferences, proof-of-work links, and application policy. New schema fields should remain backward-compatible with current Markdown records until a migration is explicitly planned.

## Generated frontend boundary

`scripts/build-jobs.js` is the boundary between canonical data and the public frontend.

It reads Markdown from:

- `jobs/`
- `seekers/`

It writes generated JSON to:

- `public/data/jobs.json`
- `public/data/seekers.json`

The browser should read generated JSON and render static pages. It should not need direct access to GitLab APIs, private tokens, or repository internals.

Validation currently runs with:

```bash
npm run build:jobs
npm run validate:jobs
```

These commands must continue to pass after architecture, schema, or provider changes.

## GitLab-first provider contract

GitLab is the current provider for submission and review workflows.

Current GitLab-backed flows:

1. A contributor opens an issue using an issue template in `.gitlab/issue_templates/`.
2. GitLab labels or template headings identify the submission type.
3. A maintainer reviews the issue and may request changes.
4. `process_submissions` runs through GitLab CI on a schedule or manual pipeline.
5. `scripts/process-gitlab-submissions.js` reads open issues with the GitLab API.
6. The script converts accepted issues into Markdown files under `jobs/` or `seekers/`.
7. The build script regenerates JSON.
8. CI commits the Markdown/JSON update to `main` and closes the processed issue.
9. Cloudflare serves the updated static frontend after deployment.

Current templates:

| Template | Purpose | Current label |
| --- | --- | --- |
| `.gitlab/issue_templates/job-posting.md` | Manual job submission | `job-posting` |
| `.gitlab/issue_templates/job-posting-from-link.md` | Job URL to reviewable draft input | `job-posting-from-link` |
| `.gitlab/issue_templates/job-seeker.md` | Public seeker profile submission | `job-seeker` |
| `.gitlab/issue_templates/flag-job-posting.md` | Request listing removal | `flag-job-posting` |

The GitLab provider owns provider-specific details such as issue templates, labels, issue URLs, merge request URLs, project API paths, and pipeline behavior.

## Future provider abstraction points

Provider-specific behavior should be centralized before adding GitHub or generic Git support. The UI and data model should not hard-code GitLab everywhere.

Recommended provider capabilities:

| Capability | GitLab now | GitHub later | Generic Git later |
| --- | --- | --- | --- |
| Open job issue | GitLab issue template | GitHub issue form/template | Patch instructions or hosted form that emits Markdown |
| Open seeker issue | GitLab issue template | GitHub issue form/template | Patch instructions or hosted form that emits Markdown |
| Direct Markdown change | GitLab merge request | GitHub pull request | Git patch/commit |
| Source traceability | issue/MR/commit URL | issue/PR/commit URL | remote URL + commit hash |
| Review state | labels + Markdown fields | labels + Markdown fields | Markdown fields + maintainer commits |
| Automation | GitLab CI | GitHub Actions | maintainer-run script |

A provider adapter should eventually define:

- provider id: `gitlab`, `github`, `generic-git`, `forgejo`, or `gitea`;
- display name;
- repository URL;
- issue/MR/PR creation URLs;
- labels or states;
- source file URL generation;
- commit URL generation;
- CI or automation notes;
- user identity URL generation from a Git username.

GitHub and generic Git support should be planned as provider paths, but GitLab should remain the first implementation target until the current workflow is polished.

## Trust and maintainer review

The current trust model is human maintainer review.

For this phase, BLT-Jobs does not require external company verification, domain ownership proof, signed commits, or a proprietary account system.

Maintainers should be able to review:

- who submitted the issue or merge request;
- what Markdown file will be created or changed;
- whether required fields are present;
- whether application/contact data is safe to publish;
- whether a listing is stale, duplicated, suspicious, or out of scope.

Future verification can add company Git identity, domain checks, signed commits, or organization profiles, but those are not required for the first GitLab-first contract.

## Public Git data rules

Data that belongs in public Git:

- public job listing metadata;
- public job description and requirements;
- public application URL or intentionally public contact route;
- public seeker profile fields explicitly chosen by the seeker;
- Git usernames, public profile URLs, portfolio URLs, and proof-of-work links;
- source issue/MR/PR URLs and review status;
- public organization profile metadata.

Data that should not be stored in public Git by default:

- private applicant notes;
- resumes or CV files unless intentionally public and externally hosted;
- private phone numbers;
- private email addresses unless explicitly marked public;
- compensation negotiations;
- interviewer notes;
- identity documents;
- API tokens, private keys, or webhook secrets.

Seeker profiles and future applications need clear warnings that submitted Markdown becomes public repository data.

## Applications policy

Applications are privacy-sensitive and should be conservative at first.

Preferred initial model:

- jobs link to an external apply URL, public email, or contact preference;
- seekers publish optional public profiles;
- applicants do not submit resumes or private application packets into this public repository.

Possible future Git-native application models must first define a minimal safe public object, such as:

- Git username;
- seeker profile link;
- short public note;
- contact preference.

Do not add `applications/<job-id>/<username>.md` or public application issues until the privacy contract is explicit.

## Forking, mirroring, and upstream sync

Forks and mirrors are part of the platform model, not just a development convenience.

Expected patterns:

- a community can fork BLT-Jobs and run its own static board;
- a company can maintain Markdown listings in its own Git repo and submit changes upstream;
- an ecosystem maintainer can mirror the repository to another Git-compatible provider;
- upstream remains the canonical source for jobs.owaspblt.org;
- conflicts are resolved through normal Git review.

Federation work should document how to sync forks, identify canonical records, and avoid duplicate listings.

## Implementation checklist for issue #3

- [x] Document repository-as-database, Markdown data, generated JSON, and static frontend boundaries.
- [x] Define the current GitLab workflow.
- [x] Define future provider abstraction points for GitHub and generic Git.
- [x] Define what belongs in public Git and what should stay outside it.
- [x] Clarify maintainer review as the current trust model.
- [x] Include the issue/MR -> Markdown -> JSON -> static site flow.
- [x] Link this architecture document from the repository README.

## Related issues

- Parent: [#2 GSoC 2026 BLT-Jobs Git-native job platform](https://gitlab.com/owasp-blt/blt-jobs/-/work_items/2)
- This work item: [#3 Define BLT-Jobs Git-native architecture and provider contract](https://gitlab.com/owasp-blt/blt-jobs/-/work_items/3)
