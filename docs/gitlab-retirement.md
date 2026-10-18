# Retiring gitlab.com/owasp-blt

On 2026-10-18 the owners decided to close gitlab.com/owasp-blt. Every BLT project now lives in this monorepo, hosted at
<https://git.owaspblt.org/BLT>. That is a ForkMesh instance in single-organization mode: organization `owasp-blt`,
repository `BLT`, public API under `https://git.owaspblt.org/api/repo/owasp-blt/BLT/...`. Project folders and their
names are listed in [`scripts/routing/projects.tsv`](../scripts/routing/projects.tsv). The 57 GitLab projects map one
to one to folders; `owasp-blt/blt` is `blt-core`.

This page lists every GitLab dependency left in the monorepo (found with `git grep -i gitlab`, about 300 files, on
2026-10-18). For each one it says what git.owaspblt.org can replace it with and what to do. Done so far:

- **blt-hackathons** (`2bc7daab38`): the hackathon statistics now come from git.owaspblt.org. See
  [blt-hackathons/README.md](../blt-hackathons/README.md#statistics-updates).
- **blt-cron** (`d039ea2504`): the GSoC 2026 progress job is turned off. That job was the GitLab-commit reader in
  blt-gsoc.
- **blt-jobs**: every link points at git.owaspblt.org (`/BLT/tree/main/blt-jobs`, `/BLT/blob/main/blt-jobs/...`,
  `/BLT/issues/new`); the issue templates moved to `blt-jobs/issue-templates/`, and the GitLab polling script is
  gone (`createFromIssue()` is in `scripts/submissions.js`).
- **blt-pages links**: the `/BLT/BLT-Pages/-/issues` links now go to `/BLT/issues?label=blt-pages` (the forge's issue
  list takes one `label` filter), `/BLT/issues/new` and `/BLT/issues/<n>`.
- **blt-safecloak**: `install.sh` builds from a sparse clone of `blt-safecloak/client` (or `SAFECLOAK_SOURCE_DIR`);
  the GitLab artifact download, `.gitlab-ci.yml` and the gitlab.com link tests are gone.
- **README contributors**: `gitlab_authors()` is replaced by `forge_authors()`, which reads pull, issue and comment
  authors from the git.owaspblt.org ledgers (`scripts/forkmesh/ledger.py`). No gitlab.com avatar or profile links;
  `readme.yml` no longer passes `GITLAB_TOKEN`.
- **blt-pages**: the leaderboard reads `bug` + blt-pages issues from the forge ledger, and the browser no longer
  falls back to the gitlab.com API. Elections were redesigned instead of dropped: nominations are `[NOMINATION]`
  forge issues, votes are the forge's native issue votes (one per account, counted once per role), and the fake
  "Sign in with GitLab" is gone. The data and pre-rendered pages live in KV (see docs/workflows.md).
- **blt-design-contest**: submissions are open forge issues (project label or `[blt-design-contest]` prefix, plus a
  contest label or prefix); votes are forge votes plus `+1` comments; the browser fetch of gitlab.com is gone; the 7
  GitLab templates are documented bodies in `issue-templates/`. The 45 GitLab-era submissions and their final votes
  are kept in `data/gitlab-archive.json` and shown as "GitLab archive". Pages are rebuilt on issue events and daily
  and served from KV.
- **blt-waypoint**: `generate_forge_data.py` replaces `generate_gitlab_data.py`: one row per folder of `projects.tsv`
  with 30/90/365-day commits and authors from `history?path` (live since 2026-10-18), issues and pulls from the
  ledgers, descriptions from `info.json`. Stars, forks, languages and releases are null and hidden. Output is
  `forge_data.json` in KV (the old `/gitlab_data.json` URL is aliased). The "GitLab migration" column and tab are
  retired, `github_data.json` and `main_data.*` use forge folder URLs, and `GITLAB_TOKEN` is gone.
- **blt-mcp**: `blt://good-first-issues` reads open `good first issue` issues from the forge ledger
  (`blt_mcp/forge_issues.py`: anonymous, 5-minute cache; the server is a pip-installed process, so it has its own
  reader). `upload_screenshot` and `GITLAB_API_TOKEN` are removed, and so are the gitlabci Renovate manager and
  `.gitlab-ci.yml`. blt-cli needs no change (same JSON shape).
- **blt-toasty**: deleted `gitlab_client.py`, `gitlab_linker.py` and the shadow-mode pipeline that read closed issues
  of GitLab project 14998512 (`/admin/shadow-report`, `SHADOW_*` vars; `on_scheduled` is now a no-op).
  `/webhook/gitlab` stays as an integration for external GitLab projects. `.gitlab-ci.yml` is removed.
- **blt-profiles**: the inbound GitLab issue webhook (branch, commit, MR, note) is replaced by
  `.forkmesh/blt-profiles--add-profile.yml`, which commits the profile to main, deploys, comments and closes the
  issue; only the account that created a profile can update it. The template is
  `blt-profiles/issue-templates/add-profile.md`. The Worker endpoint and `GITLAB_ACCESS_TOKEN`, `GITLAB_WEBHOOK_TOKEN`
  and `GITLAB_PROJECT_PATH` are gone (delete the Worker secrets and the gitlab.com project webhook).

## What git.owaspblt.org can serve

These were checked read-only against the live instance on 2026-10-18. Every read is
`GET https://git.owaspblt.org/api/repo/owasp-blt/BLT/<operation>`.

| Need | ForkMesh read | Status |
| --- | --- | --- |
| Files and folders | `tree?path=&ref=`: each entry carries its git oid. `blob`, `blobs?path=..` (50 per call), `raw` | Works, anonymous. |
| Pull requests | The `forkmesh/pulls` ledger branch has `.forkmesh/pulls/<n>/pull.md` (front matter: title, status, ts, authorName, mergedAt), `NNNN-review.md`, `NNNN-comment.md` and similar, plus `changes.patch` and `commits.mbox`. Read them with `tree`/`blobs` and `ref=forkmesh/pulls`. | Works. There is no ledger yet (no pull requests so far): `tree` answers 404, which means zero. |
| Issues | `.forkmesh/issues/{open,closed}/<n>/issue-<n>.json` on `main` (labels, status, events, authorName, timestamps). | Works (1 issue today). |
| What a branch changes | `compare?base=&head=` returns an mbox with the diff. | Works. |
| Commits | `history?ref=` returns 60 commits; `since`/`until` widen it. `history?path=<folder>` returns one project's commits. | The path filter is on the platform branch `instance-actions` (`b7f7fc65c`, "Project addresses for monorepos"), but the live instance ignores `path`. **Deploy it before any per-project commit reader moves.** |
| Contributors | `stats`: commit counts and weekly activity per author, for the whole repository. | Works. Not per folder. |
| Pull and issue lists | `/pulls`, `/issues` | Answer **401** to anonymous callers. Read the ledger files instead, as above. |
| Folder descriptions | `<folder>/.forkmesh/info.json` (folder About box: name, about, website, topics). | Supported, but no folder has one yet. |
| Stars, forks, releases, tags, languages per project | none | Not available per folder. Drop these features or derive them some other way. |
| Votes | Issue records carry `votes` and one signed `vote` event per vote (`authorName`); signed-in users press Vote on the issue page. | Works: `scripts/forkmesh/ledger.py` `voters()`, `vote_count()`. Use instead of 👍 award emoji. |
| Issue templates (`?issuable_template=`), prefilled new issues, webhooks to external services, write APIs for bots | not found | **Unavailable.** Link to a template file in the folder (blt-jobs `issue-templates/`) and use `.forkmesh/` workflows on issue events, as blt-jobs does. Issue `reaction` events exist on the ledger but are not used by any BLT page. |

## How items are attributed to projects

blt-hackathons uses one rule for "which project is this pull request or issue for?", and the other readers should use
the same one:

1. A pull request belongs to every top-level folder its diff touches. `.forkmesh/<folder>--*.yml` counts for
   `<folder>`. Files outside project folders count for no project.
2. A pull request with no readable diff belongs to the folder named by a `<folder>:` or `[<folder>]` title prefix.
   Commit subjects in this repository already use that prefix.
3. An issue belongs to the folders named by its labels (`blt-leaf` or `project:blt-leaf`), and otherwise to its
   title prefix.

The implementation is `blt-hackathons/forkmesh_source.py`. It reads incrementally: each pull and issue folder's git
oid is cached, so a later run re-reads only what changed.

## Inventory and plan by project

Kinds of dependency:

- **API**: a runtime call to gitlab.com.
- **token**: `GITLAB_TOKEN` or a similar secret.
- **paths**: hardcoded `owasp-blt/...` project paths.
- **CI**: a `.gitlab-ci.yml` or `.gitlab/` leftover.
- **links**: links or text that users see.
- **keep**: a GitLab feature for external users, not a dependency on our group.

### Live readers of gitlab.com (break when the group closes)

| Project | What it reads, and from where | Can git.owaspblt.org replace it? | Proposed change |
| --- | --- | --- | --- |
| **blt-hackathons** | Merge requests, notes, issues and metadata of 57 projects. | Yes | **Done.** Reads the ForkMesh ledger by folder, incremental and resumable, with Slack counts (`trackSlack`). GitLab support stays for third-party groups. |
| **root README contributors**: `scripts/readme/contributors.py` (`readme.yml`) | `:533` reads `GET /groups/owasp-blt/merge_requests` (MR author, name and avatar, re-checked every 7 days). `:652` and `:777` build gitlab.com avatar and profile fallbacks. Uses `GITLAB_TOKEN`. | Yes: pull authors from the ledger (`authorName`) plus the instance accounts it already reads (`:556`). | Replace `gitlab_authors()` with a reader of ledger pull authors. Drop the gitlab.com avatar and profile fallbacks. Keep the GitLab noreply-email parsing (`:67`) and the `gitlab:` overrides, because old commits still carry them. Remove `GITLAB_TOKEN` from `readme.yml`. The `"gitlab"` cache in `.forkmesh/contributors/lookups.json` is rebuilt on the next run. |
| **blt-gsoc** | `worker/progress.js:54-61` reads `/projects/OWASP-BLT%2F<repo>/repository/commits` for each contributor. Optional `GITLAB_TOKEN` Worker secret. | Yes, once `history?path=` is deployed. | **The nightly run is off** (GSoC 2026 ended, `d039ea2504`). Before a 2027 tracker reuses it, switch to `history?path=<folder>&since&until`, matching by author. Delete the Worker secret `GITLAB_TOKEN` (`npx wrangler secret delete GITLAB_TOKEN` in `blt-gsoc`). Historical MR links in `contributors/2026/netguardian/*` (6) lead to merge requests that will disappear. Mark them "archived" or point them at the commits. |
| **blt-pages** (leaderboard) | `scripts/generate_leaderboard.py:44,639,689,732` reads bug-labelled issues, their notes and award emoji. `public/js/app.js:21-26` falls back to the gitlab.com API in the browser. `public/js/leaders.js:115,687` (elections) reads group projects and award-emoji votes, and has a fake "Sign in with GitLab". Uses `GITLAB_TOKEN` or `CI_JOB_TOKEN`. | Issues and comments: yes, by label and folder. Reactions: no. | Switch the generator to the issue ledger: label `bug` plus attribution `blt-pages`, with comment counts from the issue events. Remove the browser fallback. **Fix the current bug:** `config.js` already sets `PROJECT_URL` to the forge, so `/-/issues` links come out as `git.owaspblt.org/BLT/BLT-Pages/-/issues`. Drop elections (`leaders.js`, `data/leaders.json` is empty) or redesign them without GitLab login and reactions. |
| **blt-waypoint** | `scripts/generate_gitlab_data.py` reads, for each group project: commits, MRs, issues, languages, contributors, releases, tags, branches and raw files. Output goes to `public/gitlab_data.json`. Uses `GITLAB_TOKEN`. | Mostly: per-folder commits (after the `history?path` deploy), pulls, issues and repository-wide stats. Releases, tags, languages and stars: no. | Replace it with a per-folder generator: `projects.tsv`, then folder `history?path`, the pull and issue ledger (attribution as above), and `info.json`. Retire the "GitLab migration" column and tab in `public/script.js`, `index.html` and `issues.html`. Rewrite the gitlab.com URLs in `public/github_data.json` and `main_data.csv`. |
| **blt-design-contest** | `scripts/build_showcase.py` reads open issues (submissions), `award_emoji` (votes) and notes. It parses issue-template bodies. Six generated pages fetch the gitlab.com issues API in the browser for live vote counts. Uses `GITLAB_TOKEN`. | Issues: yes. Votes (reactions): no. Templates: no. | Read submissions from the issue ledger (label or `[blt-design-contest]` prefix). Choose a vote mechanism that does not use reactions, such as `+1` comments counted from issue events or a vote file per submission. Remove the browser fetch. Port `.gitlab/issue_templates/` (7) to a documented issue body format. Regenerate the pages. |
| **blt-mcp** (and **blt-cli**, which reads it) | `blt_mcp/server.py:148` reads `GET /groups/133215711/issues?labels=good first issue` anonymously. `upload_screenshot` posts to `/projects/:id/uploads` with `GITLAB_API_TOKEN`. | Good-first-issues: yes (issue ledger by label). Uploads: no. | Switch `blt://good-first-issues` to the issue ledger. Drop `upload_screenshot`, or keep it as an explicitly external GitLab tool that takes any project (not ours). Remove the gitlabci manager from `renovate.json` and the `.gitlab-ci.yml` leftover. |
| **blt-toasty** | `src/shadow_pipeline.py` reads closed issues of project 14998512. It is unscheduled (`crons = []`). `gitlab_linker.py` and `gitlab_client.py` (notes and labels) have no callers. There is an inbound `/webhook/gitlab`. | Reads: yes. Webhooks and writes: unknown. | Delete the dead `gitlab_client.py` and `gitlab_linker.py` and the shadow config. Decide whether triage targets forge issues (through a `.forkmesh/` issue workflow) or stays a GitLab integration for external users. Update the mocks and labels. |
| **blt-profiles** | An inbound GitLab issue webhook, then GitLab writes: branch, commit, MR and note (`GITLAB_ACCESS_TOKEN`, `GITLAB_WEBHOOK_TOKEN`, `GITLAB_PROJECT_PATH`). | Webhook and write APIs: no. A forge workflow can do it. | Replace it with a `.forkmesh/` `issues:` workflow that commits the profile directly, as blt-jobs `process-submission.mjs` does. Remove the Worker endpoint and its three GitLab secrets. Port `.gitlab/issue_templates/Add Profile.md`. |

### Pages that send users to gitlab.com (bugs today)

| Project | Problem | Fix |
| --- | --- | --- |
| **blt-jobs** | `public/assets/js/provider.js:2,9` hardcodes `https://gitlab.com/owasp-blt/blt-jobs` and **rewrites every forge link back to gitlab.com** on page load (9 pages; `index.html:1128` has the same fallback). It also builds `/-/issues/new?issuable_template=` and `/-/blob/` URLs. | Point it at `https://git.owaspblt.org/BLT` (`issues/new`, `blob/main/blt-jobs/...`). Default `source_platform` to the forge. Move `createFromIssue()` out of `scripts/process-gitlab-submissions.js` and delete its dead polling `main()`. Port `.gitlab/issue_templates/` (4). |
| **blt-safecloak** | `public/install.sh:13-14,48,51` downloads prebuilt clients from `$REPO_URL/-/jobs/artifacts/...`, a GitLab CI API the forge does not have. It falls back to a source build. `tests/test_pages.py:100-102,289-291` assert a gitlab.com link that no page has, **so CI fails**. `.gitlab-ci.yml` is still read by `tests/test_desktop_installer.py`. | Drop the artifact download, or publish forge releases. Make the tests assert the forge link. Fix the `CONTRIBUTING.md:6` clone URL. Remove the CI leftover with its test. |
| **blt-pages** | The `/-/issues` URL bug (see above). | See above. |

### Workflows and secrets

`GITLAB_TOKEN` is passed by these workflows:

- `.forkmesh/readme.yml`
- `blt-design-contest--build-showcase.yml`, which also sets `GITLAB_PROJECT_PATH`
- `blt-pages--update-leaderboard.yml`, which also sets `CI_PROJECT_PATH`
- `blt-waypoint--build-site.yml`
- `blt-hackathons--update-stats.yml`, now only for third-party GitLab events

Remove each one when its reader is switched. Then delete the Actions secret `GITLAB_TOKEN` and the Worker secrets:

- `blt-gsoc`: `GITLAB_TOKEN`
- `blt-toasty`: `GITLAB_ACCESS_TOKEN` (`GITLAB_WEBHOOK_SECRET` stays for external GitLab webhooks)
- `blt-hackerhouse`: `GITLAB_WEBHOOK_SECRET`, `GITLAB_API_TOKEN`

The "Ported from …/.gitlab-ci.yml" comments in five workflows are history and are harmless.

### CI and template leftovers

These `.gitlab-ci.yml` files are not run anywhere:

- blt-hackerhouse
- blt-netguardian
- blt-pages
- blt-university

Delete them once nothing reads them; `docs/workflows.md` records what each one did. (blt-mcp, blt-safecloak and
blt-toasty: deleted.)

The `.gitlab/issue_templates/` folders are ported: blt-design-contest (7), blt-jobs (4), blt-pages (1) and
blt-profiles (1) now keep documented issue bodies in `<folder>/issue-templates/`, and their pages link to
`/BLT/issues/new` plus the template file, since ForkMesh has no templates and cannot prefill a new issue.

### Links and labels only (no data dependency)

The URLs here already point at git.owaspblt.org. Only "GitLab" wording, `fa-gitlab` icons or old clone URLs remain.
Replace them with forge wording and a neutral icon such as `fa-code-branch`.

| Project | Where |
| --- | --- |
| root `README.md` | `:8` lists the read-only mirror `gitlab.com/owasp-blt/blt`. Remove it when the group closes, unless a mirror there is kept (plan.md, "Mirrors"). |
| blt-university | "Submit/Enroll via GitLab" (`_pages/enroll.html`, `about.html`, `contributing.html`, built `public/` copies, about 18); `QUICKSTART.md:48` clone URL; `README.md:42`. |
| blt-start | `public/index.html` (14, including the clone URL at `:292`); `README.md:70,146,163`. |
| blt-design | `fa-gitlab` on forge "Contribute" buttons (17 files); placeholder `https://gitlab.com/...` in `inputs.html:25`. |
| blt-monitor, blt-next, blt-api, blt-vanish, blt-cli, blt-mayo, blt-autopatch, blt-gitcaster, blt-owasp-metadata, blt-newsletter | One to nine labels or titles each ("Source code on GitLab" and similar). |
| blt-hackerhouse | "GitLab repository" titles on forge links. Its GitLab event ingestion is a product feature (below). |
| blt-owasp-bumper, blt-owasp-projects | README sections that describe a `.gitlab-ci.yml` which no longer exists. |
| dot_github, coderabbit, blt-autopatch | The stock GitLab "Getting started" README boilerplate. Delete it. |
| blt-ossh | **Done**: the `gitlab.com/owasp-blt/...` catalog entry is removed and filtered on every refresh (`scripts/refresh-kv.sh`). |
| blt-core | `MIGRATION_PLAN.md:20` says source links use the GitLab group. Update it. |
| blt-docs | Plan and history pages. Leave them, or say "GitLab (closed)". |
| docs/workflows.md | Port notes. Update the token columns as readers move. |

### Keep (GitLab as a feature for external users)

- **blt-preflight**: GitLab MR webhook adapter; makes no API calls to our group. Optionally add a forge pull-request adapter.
- **blt-hackerhouse**: GitLab webhook ingestion (`/webhook/gitlab`). Either retarget it to forge events or keep it as an optional external source.
- **blt-owasp-wich**: checks scanned repositories for `.gitlab-ci.yml`.
- **blt-jobs** and **blt-profiles**: the `gitlab` profile field for seekers and users.
- **blt-core**: tech-stack taxonomy.
- **blt-timer-web** and **blt-newsletter**: guard tests asserting there is no GitLab.
- Vendored Font Awesome CSS.
- **blt-hackathons**: GitLab provider for third-party groups (`create-hackathon.mjs` still offers it). Adding a "git.owaspblt.org" choice to the hackathon-creation form is a small follow-up.

## Before the group is closed

1. Deploy the platform's `history?path=` support (`instance-actions` `b7f7fc65c`). The live instance ignores `path`
   today.
2. Switch the readers above in this order: README contributors, blt-pages, blt-waypoint, blt-design-contest,
   blt-mcp, blt-profiles. Then fix the blt-jobs and blt-safecloak bugs, which already affect users. blt-gsoc is off
   and only needs the change before a 2027 tracker.
3. Bring open GitLab merge requests and issues across as forge pull requests and issues. Snapshot what pages link to
   (blt-gsoc netguardian MRs, design-contest submissions and votes, pages leaderboard issues) so the history stays
   readable.
4. Remove the `GITLAB_TOKEN` workflow env lines and the secrets listed above.
5. Confirm the list of the 57 projects (58 counting the group's other repositories), then archive them, and delete
   them only after confirming again. Deletion cannot be undone.
