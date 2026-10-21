# Contributing to OWASP BLT

Thanks for helping. All BLT work happens on our own forge, **[git.owaspblt.org/BLT](https://git.owaspblt.org/BLT)**:
issues, pull requests, discussions and reviews. [github.com/OWASP/BLT](https://github.com/OWASP/BLT) is a read-only
mirror and the old gitlab.com/owasp-blt projects are retired; don't open issues or pull requests there.

Before you start, read the [AI Policy](https://git.owaspblt.org/BLT/blob/AI_POLICY.md) and the
[Code of Conduct](https://git.owaspblt.org/BLT/blob/CODE_OF_CONDUCT.md). Security problems go through
[SECURITY.md](https://git.owaspblt.org/BLT/blob/SECURITY.md), never a public issue.

## How the repository is laid out

BLT is one monorepo. Each project is a top-level folder with its own README, tests, licence and deploy config:

| Path | What it is |
|---|---|
| `blt-*/` | One folder per project (`blt-api`, `blt-next`, `blt-leaf`, ...), mostly Cloudflare Workers |
| `scripts/` | Shared tooling: `ci/test.sh` (tests), `deploy.sh` (deploys), `readme/` (README generator), `routing/projects.tsv` |
| `.forkmesh/` | Forge workflows (CI, deploys, scheduled jobs), the issue ledger and repository settings |
| `docs/` | Repository-wide docs, for example [workflows.md](https://git.owaspblt.org/BLT/blob/docs/workflows.md) |

### Finding the right folder

- The Projects table in the [README](https://git.owaspblt.org/BLT) lists every project with a one-line description and its live site.
- [`scripts/routing/projects.tsv`](https://git.owaspblt.org/BLT/blob/scripts/routing/projects.tsv) maps each folder to its display name and old repository names. For example, `blt-api/` is BLT-API, and <https://git.owaspblt.org/BLT/BLT-API> opens that folder.
- Issues carry a project label named after the folder, for example `blt-leaf`.

## Find something to work on

- [Good first issues](https://git.owaspblt.org/BLT/issues?label=good%20first%20issue): small, well-scoped tasks for newcomers.
- [Hacktoberfest issues](https://git.owaspblt.org/BLT/issues?label=hacktoberfest): contributor issues across every project.
- One project's issues: `https://git.owaspblt.org/BLT/issues?label=<folder>`, for example [`?label=blt-leaf`](https://git.owaspblt.org/BLT/issues?label=blt-leaf). The issue list filters on one label at a time.

To claim an issue, comment `/assign` on it (you need to be signed in). You can hold one open assignment at a time;
open a pull request within 7 days or comment `/unassign` to release it. Every issue also has a **copy AI prompt**
you can paste into a coding agent to start.

## Workflow: fork, branch, pull request

1. Sign in to [git.owaspblt.org](https://git.owaspblt.org) and **fork** the BLT repository.
2. Clone your fork (copy the clone URL from your fork's page) and create a branch:

   ```bash
   git clone <your-fork-clone-url> BLT
   cd BLT
   git switch -c blt-leaf/fix-login-redirect
   ```

3. Make your change inside the project folder. Keep it to one issue and one concern; don't touch unrelated projects.
4. Run that project's tests (see below).
5. Push to your fork and choose **Contribute: Open pull request** on the forge to open a pull request into `BLT` `main`.
6. Fill in the pull request form, including the required **AI model** field, and link the issue it addresses (for example `#123`).

Maintainers review on the forge. CI runs the tests of every folder your push touches, and a merge to `main` deploys
the changed projects automatically.

## Tests

```bash
scripts/ci/test.sh blt-leaf              # one project
scripts/ci/test.sh blt-leaf blt-api      # several
scripts/ci/test.sh --changed main        # the folders your branch changed
```

The commands per project live in [`scripts/ci/tests.tsv`](https://git.owaspblt.org/BLT/blob/scripts/ci/tests.tsv).
Python projects get a fresh virtualenv; Node, Rust and Flutter projects need those toolchains installed. Behaviour
changes need a test. Each project's README has its own setup and local-run instructions.

## Commit and pull request conventions

- **Commit subject:** start with the project folder, then a short summary in the imperative or as a plain statement:
  `blt-next: save bug reports through blt-api`. For changes to several projects, list them
  (`blt-flutter, blt-extension: ...`); for repository-wide changes use the area (`README: ...`, `docs: ...`).
- **Body:** say why, not only what. Wrap at about 72 characters.
- **AI disclosure (required):** every pull request fills in the **AI model** field with the model(s) and tool you
  used, for example `Claude Opus 5.5 via Claude Code`, or `None`. The forge enforces this
  (`.forkmesh/pulls.json` sets `requireAiDisclosure`). Commits written or substantially edited by an agent end with
  a trailer naming the model:

  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```

- **Pull request description:** what changed, why, and how you tested it. Small, focused pull requests get reviewed faster.
- Never commit secrets, tokens or `.env` files.
- Don't edit the generated README sections (between `<!-- ...-START -->` and `<!-- ...-END -->`); they are rebuilt by
  `scripts/readme/update_readme.py`.

## Licensing

Each project has its own `LICENSE` file; most are AGPL-3.0. Your contribution is licensed under the licence of the
folder you change. See [LICENSE](https://git.owaspblt.org/BLT/blob/LICENSE).

## Getting help

See [SUPPORT.md](https://git.owaspblt.org/BLT/blob/SUPPORT.md): ask on the issue, in a forge discussion, or in
`#project-blt` on the OWASP Slack.
