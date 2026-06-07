# Contributing to OWASP BLT docs

## Start from the right repository

OWASP BLT is documented across several repositories. Start in the repository that owns the change:

| Repository | Current status | Use it for |
| ---------- | -------------- | ---------- |
| [BLT-docs](https://gitlab.com/owasp-blt/blt-docs) | Current documentation repository | MkDocs pages, documentation navigation, writing standards, and contributor guidance. |
| [BLT-API](https://gitlab.com/owasp-blt/blt-api) | Current API repository | API service work, platform integration code, API tests, and API-owned operational notes. |
| [BLT-Jobs](https://gitlab.com/owasp-blt/blt-jobs) | Current jobs/community repository | Jobs portal work, community portal content, and related automation workflows. |
| Other BLT support repositories | Migration status should be confirmed | Metadata, project catalog, discovery, and automation modules that may still have historical GitHub locations. |

If a repository is migration-pending or unclear, confirm the current location with maintainers before opening new work.

## Work from an issue or work item

Use GitLab issues or work items when the repository has a confirmed GitLab home. Link the issue or work item in the merge request so reviewers can understand the reason for the change.

For migration-pending repositories, ask maintainers where new work should be tracked before starting. Avoid opening duplicate issues across historical GitHub repositories and current GitLab repositories.

## Keep changes reviewable

Prefer small, focused merge requests. A documentation change should usually cover one topic, one workflow, or one repository page.

Avoid large rewrites unless maintainers have agreed on the scope first. If a larger cleanup is needed, split it into reviewable parts such as navigation changes, content rewrites, link updates, and follow-up corrections.

## Documentation contribution workflow

1. Create a branch with a short, descriptive name.
2. Edit Markdown under `docs/`.
3. Update `mkdocs.yml` navigation when adding, moving, or renaming pages.
4. Run the strict documentation build:

   ```bash
   uvx --with-requirements requirements.txt mkdocs build --strict
   ```

5. Open a merge request with a summary of the change and the verification command you ran.

## Code contribution workflow

Use the setup, test, and deployment instructions from the repository that owns the code. Do not copy setup commands from another BLT repository unless that repository explicitly shares the same tooling.

For code changes:

- Follow the repository-specific development setup.
- Run the relevant tests before opening a merge request.
- Do not commit secrets, API keys, tokens, generated credentials, or local `.env` files.
- Avoid changing unrelated files.
- Keep generated output out of the commit unless the repository explicitly requires it.

## Review checklist

- [ ] The change uses a professional, direct tone.
- [ ] The change contains no emojis.
- [ ] Internal links are relative and resolve in MkDocs.
- [ ] External repository links use confirmed GitLab locations where migration is complete.
- [ ] Migration-pending repositories are labeled as such.
- [ ] Product and architecture claims are supported by current repository context.
- [ ] `uvx --with-requirements requirements.txt mkdocs build --strict` passes.
- [ ] Screenshots, diagrams, or assets are included only when they are needed and reviewed.

## Communication

Use project maintainers, GitLab discussions, issues, and work items to clarify scope before making broad changes. OWASP community channels, including OWASP Slack, can help contributors find the right maintainer or project area, but implementation decisions should be recorded in the repository that owns the work.
