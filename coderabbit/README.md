# coderabbit

**Source Code:** [https://git.owaspblt.org/BLT/coderabbit](https://git.owaspblt.org/BLT/coderabbit)

This folder came over from the `coderabbit` project of the old GitLab group. It holds an [AGPL-3.0](LICENSE) license along with a reference CodeRabbit configuration ([`.coderabbit.yml`](.coderabbit.yml)).

## Configuration

The [`.coderabbit.yml`](.coderabbit.yml) file defines review profiles, automated labeling, and issue enrichment rules:

- **Reviews:** Uses the `chill` profile, provides detailed code review guidelines (checking functionality, security, style, and testing), enables the request-changes workflow, and disables poems.
- **Pull Request Labeling:** Automatically classifies PRs using `quality: low`, `quality: medium`, and `quality: high` labels based on impact.
- **Issue Enrichment:** Automatically enriches issues and applies `bug` or `enhancement` labels.
- **Privacy & Knowledge Base:** Automatically assigns reviewers and opts out of CodeRabbit's training knowledge base.

> [!NOTE]
> **Status:** CodeRabbit only reads configuration files located at the repository root (`/.coderabbit.yml`). The `.coderabbit.yml` in this folder is **inactive and kept for reference only**.

