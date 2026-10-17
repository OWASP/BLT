# Agentic development guidance

## Purpose

This page explains how contributors can use AI agents safely and reviewably for BLT documentation or code tasks. Agent-assisted work is acceptable only when a human contributor remains responsible for scope, accuracy, security, and final review.

## Safe use cases

- Documentation cleanup.
- Content outlines.
- Test generation.
- Issue triage.
- Code review assistance.

## Required human review

Every generated change must be reviewed by a contributor before it is merged. The reviewer should inspect the diff, run the relevant verification commands, and confirm that the change matches the issue or work item.

Generated output is not evidence by itself. Treat it as a draft until a human contributor verifies the result.

## Guardrails

- No secrets.
- No destructive commands.
- No unsupported claims.
- No unreviewed mass rewrites.
- No generated credentials.
- No changes outside the agreed scope.
- No replacement of repository-owned setup instructions with guessed commands.

## Recommended workflow

1. Plan the work and define the allowed files or modules.
2. Create a small branch.
3. Use the agent for scoped changes.
4. Review the diff manually.
5. Run strict documentation builds or repository tests.
6. Open a merge request with a human-written summary and verification notes.

## What belongs where

README files should provide a human overview and a fast path into the repository. BLT-docs should contain contributor documentation, cross-repository guidance, and stable operations notes.

Repo-specific agent context should live in agent files only when maintainers approve that workflow. Do not put agent-only instructions in a human-facing README unless maintainers explicitly request it.

## Verification checklist

- [ ] The generated change matches the issue or work item.
- [ ] The diff is small enough to review.
- [ ] No secrets, tokens, keys, credentials, or `.env` files were added.
- [ ] No unsupported product, security, or architecture claims were introduced.
- [ ] Repository links use confirmed current locations.
- [ ] Documentation builds or code tests were run as appropriate.
- [ ] A human contributor reviewed the final diff.
