# Writing documentation

## Writing principles

- Clear before clever.
- Professional and direct.
- Short paragraphs.
- No emojis.
- Avoid unsupported claims.

## Page template

```markdown
# Page title

Short summary of what this page helps the reader do.

## Purpose

Explain why the page exists and who should use it.

## Main topic

Describe the workflow, concept, or reference material.

## Related pages

- [Related page](docs-maintenance.md)
```

## User-guide page template

```markdown
# Workflow name

Short summary of the user task.

## When to use this

Explain the user scenario.

## Before you start

List prerequisites or assumptions.

## Steps

1. Do the first action.
2. Do the second action.
3. Confirm the expected result.

## Troubleshooting

List common user-facing issues and what to check.

## Related pages

- [Related workflow](../user-guide/report-bug.md)
```

## Repository page template

```markdown
# Repository name

Short summary.

## Current repository status

State the current repository link if confirmed. If it is not confirmed, say migration status should be confirmed before opening new work.

## Purpose

Explain what the repository or module does.

## Best starting points

Explain who should contribute here and what kind of work belongs here.

## Local development notes

Keep this high-level unless verified commands are maintained in the page.

## Documentation notes

Explain what should be documented in BLT-docs and what belongs in the repository README.

## Related pages

- [Related page](platform-architecture.md)
```

## Admonitions

Use Material admonitions when they make important information easier to scan.

```markdown
!!! note
    Use notes for helpful context that is not required to complete the task.

!!! warning
    Use warnings for risks such as data loss, secrets exposure, or irreversible changes.

!!! tip
    Use tips for practical suggestions that save time or reduce confusion.
```

## Cards

Use simple grid cards for short navigation groups. Keep card text concise.

```markdown
<div class="grid cards" markdown>

- **Repository guide**

  Contributor notes for a BLT repository.

  [Open guide](../repositories/blt-api.md)

- **Maintenance guide**

  Build, navigation, and content maintenance notes.

  [Open guide](docs-maintenance.md)

</div>
```

## Link rules

Use relative links for pages inside BLT-docs. Use confirmed GitLab links for migrated repositories:

- BLT-docs: `https://gitlab.com/owasp-blt/blt-docs`
- BLT-API: `https://gitlab.com/owasp-blt/blt-api`
- BLT-Jobs: `https://gitlab.com/owasp-blt/blt-jobs`

Label historical links and migration-pending repositories clearly. Do not present historical GitHub links as current unless maintainers confirm that they are still authoritative.
