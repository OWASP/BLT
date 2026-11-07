# Dependency updates (Renovate)

Every Monday at 03:41 UTC, `.forkmesh/renovate.yml` looks for dependency updates across the
monorepo and proposes them as pull requests. This follows the plan agreed in
[discussion #1](https://git.owaspblt.org/BLT/discussions/1).

## What it covers

| Manager | Files | Applied? |
| --- | --- | --- |
| `npm` | every `package.json`, with `package-lock.json` regenerated | yes |
| `pep621` | `pyproject.toml`, with `uv.lock` regenerated | yes |
| `pip_requirements` | `requirements*.txt` | yes |
| `pub` | `pubspec.yaml` (Flutter) | listed on the dashboard only |
| `cargo` | `blt-cli/Cargo.toml` | listed on the dashboard only |

The runner has no Flutter or Rust toolchain, so Flutter and Rust updates can't be applied or tested
there. Update them by hand from the dashboard list. CDN pins in HTML (`cdnjs`, `jsdelivr`,
`unpkg`) are out of scope for now: bumping one needs its SRI hash updated too.

Configuration is in [`renovate.json`](../renovate.json):

- `minimumReleaseAge: 3 days`: a version has to be at least three days old before it is proposed.
- Groups: all non-major npm updates go in one pull request (`renovate/npm-minor`) and all
  non-major Python updates in another (`renovate/python-minor`). `wrangler` gets its own group
  across every Worker (`renovate/wrangler`). Each major update gets its own pull request, one per
  package.
- No automerge. Every pull request waits for a maintainer, as agreed in the discussion. CI does not
  yet tell "tested" apart from "skipped" (missing toolchain, low memory, or no row in
  `scripts/ci/tests.tsv`), so a green check alone is not enough to merge.

## How it runs

ForkMesh has no Gitea- or GitHub-style API, so Renovate can't open pull requests on the forge by
itself. The job therefore runs in two stages ([`scripts/renovate/run.sh`](../scripts/renovate/run.sh)):

1. **Lookup.** Renovate (pinned, on a pinned and checksum-verified Node 24; the runner has Node 22)
   runs with `platform=local` and `reportType=file`. It only reads the checkout and the package
   registries. It runs once per project folder, because one run over the whole repository held
   every npm document it fetched and peaked near 1 GB, and Actions jobs are capped at 700 MB with
   no swap. Per folder the peak is about 550 MB. The on-disk cache is shared, so each registry
   document is downloaded once.
2. **Apply** ([`scripts/renovate/apply.mjs`](../scripts/renovate/apply.mjs)). For each group, in
   order (npm, Python, wrangler, then majors):
   - the edits are made in a scratch worktree: manifest values are changed in place, and
     `npm install --package-lock-only --ignore-scripts` or `uv lock --upgrade-package
     name==version` regenerates the lockfile with the exact versions Renovate chose. A folder whose
     lockfile can't be regenerated is left out of the group and named on the dashboard;
   - the change is committed as `blt-renovate` and sent to the forge's pull inbox as a signed
     patch (the same `forkmesh-pull-event-v2` signature the web client makes;
     [`forge-pulls.mjs`](../scripts/renovate/forge-pulls.mjs)). The head is the group's name,
     such as `renovate/npm-minor`; nothing is pushed to the repository;
   - at most **5** of the bot's pull requests are open at once. Groups beyond that wait for a slot;
   - when a group's open pull request lists a different set of updates (newer versions, or more
     packages), the next run sends a revision of the same pull request. Each description ends with
     `<!-- blt-renovate:<head>:<fingerprint> -->`, so an unchanged group is left alone;
   - a pull request **closed** without merging is not proposed again until the group's update set
     changes (newer versions appear).
3. **Dashboard.** An open issue titled "Dependency Dashboard" (opened by the workflow through the
   job API, label `dependencies`) gets a comment listing the open pull requests, the groups
   waiting for a slot, closed groups, the Flutter/Rust list and any problems. A comment is only
   posted when this list changed since the last one.

## Setup

- **`BLT_RENOVATE_SEED`** (Settings → Actions secrets): 32 random bytes, base64url or 64 hex
  characters, for example `openssl rand -hex 32`. Its Ed25519 public key is the pull requests'
  author. Without it the job only refreshes the dashboard.
- Pull requests from a key that no forge account owns are shown with the claimed name
  `blt-renovate`, and their CI runs wait for a maintainer's approval (Approve on the pull
  request's checks). To have CI start by itself, register the key's public key to a bot account
  and mark that account as a trusted author.
- **`GH_API_TOKEN`** (optional, already used by other workflows) lifts the anonymous GitHub rate
  limit for lookups that go through GitHub.

## Running it by hand

- Actions → "Renovate: dependency updates" → Run workflow, with `mode` `pulls` (default), `report`
  (dashboard only) or `dry-run` (build the patches and print the dashboard; changes nothing).
- Locally: `scripts/renovate/run.sh --dry-run`. Downloads go to `RENOVATE_WORK_DIR` (default
  `$TMPDIR/blt-renovate`).

## Reviewing a Renovate pull request

1. Read the table in the description and each package's changelog, majors especially.
2. Check which projects CI tested. A project shown as `SKIPPED`, or one with no tests, needs a
   local run (`scripts/ci/test.sh <project>`).
3. Lockfile-only rows (marked "(lockfile)") change only what is installed, not the declared range.
4. Packages that touch auth, crypto or the Worker runtime (`cryptography`, `pyjwt`, `wrangler`,
   `@cloudflare/workers-types`, ...) deserve a deploy to a test Worker first.
