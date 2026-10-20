# Workflows

Automation runs as ForkMesh instance Actions from `.forkmesh/*.yml` on the instance's own runner.
These files replace `.github/workflows/` (the GitHub copy is a read-only mirror with Actions off) and the
scheduled jobs of the per-project `.gitlab-ci.yml` files.

The runner differs from GitHub Actions in a few ways:

- `uses:` steps are ignored, so every step is a `run:` step. The workspace is already a full clone.
- Toolchains are git, curl, jq, Node.js 22 with npm, and Debian Python 3.13. Python steps make a
  virtualenv (`python3 -m venv .venv`). Projects that pinned 3.11 or 3.12 run on 3.13.
  Flutter, Java, Ruby, Rust and Chromium are not installed, and there is no sudo.
- Jobs that commit set `permissions: contents: write` and call
  [`scripts/actions/commit-back.sh`](../scripts/actions/commit-back.sh). It stages only the named
  paths and skips the commit when they did not change. It then runs `git pull --rebase` and
  `git push origin HEAD:main`, retrying up to 5 times. The runner sets the bot identity.
- A push made by a workflow does not trigger other workflows, so `deploy.yml` never sees data
  commits. After a data commit, `commit-back.sh --deploy <project>` runs `scripts/deploy.sh <project>`
  itself. It only does this when `CLOUDFLARE_API_TOKEN` is set.
- Inside a job, `GITHUB_TOKEN` is the platform job token. Scripts that call api.github.com get
  `GITHUB_TOKEN: ${{ secrets.GH_API_TOKEN }}` instead. When that secret is not set, they run
  unauthenticated and hit lower rate limits.
- Issue automation calls the job API through [`scripts/actions/forge.mjs`](../scripts/actions/forge.mjs).
  It reads the event from `FORKMESH_EVENT_PATH` and uses `FORKMESH_API_URL` and `FORKMESH_TOKEN`.

## Workflows

Schedules are UTC. Every workflow with a schedule can also be run by hand (`workflow_dispatch`).
In the table, CF means `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, which the job uses to deploy after a data commit.

| File | Source | Triggers | Secrets |
| --- | --- | --- | --- |
| `ci.yml` | GitHub `ci.yml` | push (any branch): `scripts/ci/test.sh --changed $FORKMESH_BEFORE`; dispatch input `projects` (default `all`) | none |
| `deploy.yml` | new | push to main: `scripts/deploy.sh --changed $FORKMESH_BEFORE` (folders in `scripts/deploy/projects.tsv`); dispatch input `project` (a name, several space-separated, or `all`) | CF |
| `readme.yml` | GitHub `readme.yml` | push to main (any path; Projects, Deploying and Contributors), `17 6 * * *` (also refreshes Blog Posts); commits `README.md` and `.forkmesh/contributors/` | `GH_API_TOKEN` (optional) |
| `blt-cve--build-index.yml` | GitHub | push to main under `blt-cve/public/cves`, `public/schema`, `scripts/build_index.py` | CF |
| `blt-design-contest--build-showcase.yml` | GitLab `build_showcase` | issue events on contest issues (project label or `[blt-design-contest]` prefix, contest labels, `winner`), `47 7 * * *` (votes raise no issue event), push under `blt-design-contest/scripts/` or `data/`; reads the git.owaspblt.org issue ledger and writes changed pages to KV (`blt-design-contest/scripts/refresh-kv.sh`), no commit | CF (with KV write) |
| `blt-extension--release.yml` | GitHub `release.yml` + packaging from `create-release.yml` | dispatch only (input `publish`) | `CHROME_CLIENT_ID`, `CHROME_CLIENT_SECRET`, `CHROME_REFRESH_TOKEN` |
| `blt-hackathons--create-hackathon.yml` | GitHub | issues opened/labeled with `hackathon-creation` | CF |
| `blt-hackathons--process-sponsor.yml` | GitHub | issues opened/labeled with `sponsorship` | CF |
| `blt-hackathons--update-stats.yml` | GitHub `update-stats.yml` + GitLab `update-future-hackathons` | `37 */6 * * *` (every 6 h), push under `blt-hackathons/`; reads git.owaspblt.org incrementally within a 15-minute budget and writes changed stats and its state to KV (`scripts/refresh-kv.sh`), no commit | CF (with KV read/write); optional `GH_API_TOKEN`, `GITLAB_TOKEN` (third-party GitLab events only), `SLACK_TOKEN_OWASP`, `SLACK_TOKEN_BLT` |
| `blt-jobs--expire-jobs.yml` | GitLab `expire_jobs` | dispatch only (optional cleanup of expired `jobs/*.md`; the Worker already hides expired jobs) | CF |
| `blt-jobs--process-submissions.yml` | GitLab `process_submissions` | issues opened/edited/labeled that look like job, seeker or flag submissions; dispatch input `issue` | CF |
| `blt-ossh--update-catalog.yml` | GitHub | `0 6 * * *`; seeds from KV, writes `data/ossh_catalog.json` to KV when changed (`blt-ossh/scripts/refresh-kv.sh`), no commit | `DISCORD_BOT_TOKEN` (optional), CF (with KV read/write) |
| `blt-ossh--update-profiles.yml` | GitHub | `13 4 * * *` (safety net), issue events on `profile` issues; dispatch input `issues` to import issues | CF |
| `blt-owasp-bumper--generate-repo-list.yml` | GitHub + GitLab `pages` | `0 0 * * *`, push of `generate_repo_list.py` or `scripts/refresh-kv.sh`; writes `index.html` to KV (`blt-owasp-bumper/scripts/refresh-kv.sh`), no commit | `GH_API_TOKEN`, CF (with KV write) |
| `blt-owasp-metadata--scraper.yml` | GitHub | `0 3 * * 1`; writes `data/metadata*.{json,csv,md}` to KV (`blt-owasp-metadata/scripts/refresh-kv.sh`), no commit | `GH_API_TOKEN`, CF (with KV write) |
| `blt-owasp-projects--refresh-data.yml` | GitLab `refresh_data` | `23 4 * * *`; seeds from the live site, writes changed data files to KV (`blt-owasp-projects/scripts/refresh-kv.sh`), no commit | `GH_API_TOKEN`, CF (with KV write) |
| `blt-owasp-projects--sweep-repos.yml` | GitLab `sweep_repos` (manual) | dispatch only | `GH_API_TOKEN`, `SLACK_WEBHOOK_URL_SWEEP` |
| `blt-pages--update-leaderboard.yml` | GitLab `update_leaderboard` | issue events on blt-pages or `[NOMINATION]` issues, `11 5 * * *` (safety net), push under `blt-pages/scripts/` or of the two pre-rendered pages or `public/data/leaders.json`; reads git.owaspblt.org and writes to KV (`blt-pages/scripts/refresh-kv.sh`), no commit | CF (with KV write) |
| `blt-panini--update_slack_apps.yml` | GitHub | `0 0 * * 0`; seeds from KV with the committed entries over it, writes `slack_apps.json` to KV when changed (`blt-panini/scripts/refresh-kv.sh`), no commit | CF (with KV read/write) |
| `blt-profiles--add-profile.yml` | GitLab issue webhook in the blt-profiles Worker | issues opened/edited/labeled that look like Add-profile submissions (labels `profile`/`add-profile`/`profile-submission`, a `[blt-profiles]` title, or the template headings); dispatch input `issue`. Commits `public/profiles/<user>.json` and `index.json`, deploys, comments and closes | CF |
| `blt-tomato--scrape_funding.yml` | GitHub | `0 18 * * 5`, push under `blt-tomato/.github/scripts/` or `scripts/refresh-kv.sh`; writes `index.html` and `project_repos_links.json` to KV (`blt-tomato/scripts/refresh-kv.sh`), no commit | `GH_API_TOKEN`, CF (with KV write) |
| `blt-university--course-submission.yml` | GitHub | issue opened with `course-submission` or `[COURSE]` title, or that label added | none |
| `blt-university--enrollment.yml` | GitHub | issue opened with `enrollment` or `[ENROLLMENT]` title, or that label added | none |
| `blt-waypoint--build-site.yml` | GitLab `build_site` | `29 6 * * *`, push of `blt-waypoint/scripts/generate_forge_data.py`, `forge_urls.py` or `scripts/routing/projects.tsv`; reads git.owaspblt.org and writes `forge_data.json` to KV, no commit | CF (with KV write) |

### Schedules chosen for the GitLab jobs

GitLab pipeline schedules were set in the GitLab UI, so their times were not in the repository. The schedules above came from:

- `blt-gsoc` update-progress: `7 23 * * *`. The `.gitlab-ci.yml` comment gives `0 23 * * *`, and the job fills in the current day.
  It ran in the Worker (blt-cron, 23:07-23:11) until 2026-10-18, when the job was turned off because GSoC 2026
  coding ended on 17 Aug. The `progress` task and its KV data stay, so the page shows the final state.
- `blt-hackathons` future hackathons: was `37 0 * * *` (the README said daily). Since the data moved to KV
  there is one job (every 6 hours) for every hackathon that has not ended.
- `blt-jobs` expire: no schedule (see "Fewer bot commits" below). Submissions are driven by issue events instead of polling.
- `blt-owasp-projects` refresh: `23 4 * * *`, daily. This is OWASP repository metadata.
- `blt-pages` leaderboard: `11 5 * * *`, daily, plus issue events. It writes KV, not git, since 2026-10-18.
- `blt-waypoint` data: `29 6 * * *`, daily (KV, no commits).
- `blt-design-contest` showcase: issue events on contest issues plus a daily `47 7 * * *` run for votes; the pages go to KV, not git.

### Fewer bot commits

Every data commit a workflow pushes lands on `main`, so schedules are chosen to commit only when something changed:

- `readme.yml` used to run hourly and committed every time because both "Last updated" lines carried
  the run time. It now runs on each push to main (ForkMesh has no `paths-ignore`, but pushes made by
  workflows, including its own commit, do not trigger push workflows) and once a day for the external
  Blog Posts section. `scripts/readme/update_readme.py` keeps a section's old text, timestamp
  included, when nothing else in it changed, so a run with no news commits nothing.
- `blt-jobs` expired listings are hidden at read time: the Worker serves `/data/jobs.json`
  (`run_worker_first`) from the static asset and drops jobs whose `effective_expires_at` (written by
  `npm run build:jobs`: `expires_at`, else posted/created + 60 days) has passed, fixing `count`, with
  `Cache-Control: max-age=300`. The daily delete-commit-redeploy is gone; the expired Markdown files
  stay in the repository until someone runs the workflow by hand. `seekers.json` has no expiry rule
  and is still served as a plain asset.
- `blt-ossh` profiles are updated by issue events; the poll went from every 6 hours to once a day.
- Hackathon statistics, GSoC stats and progress, and the my-gsoc-tool dashboard data and forks list
  are kept in Workers KV (next section). Their six workflows (up to 28 commits a day, 24 of them the
  hourly hackathon stats, whose `stats.json` timestamp changed every run) are gone or no
  longer commit.

### Data in Workers KV

Data that a schedule refreshes now lives in each project's Workers KV namespace, not in git: no data
commits and no redeploys. Each Worker serves the data at the same path the pages already load, from KV,
and falls back to the copy committed under its static assets while KV has none (the first deploy).
Responses carry `Cache-Control: public, max-age=60, stale-while-revalidate=600`, `X-Data-Source: kv` or
`static`, and `X-Data-Updated-At`.

| Project | Paths served from KV | Refreshed by | Secrets on the Worker |
| --- | --- | --- | --- |
| `blt-hackathons` | `/stats.json`, `/hackathon-data/*.json` (and the unserved refresh state `state/fetch-state.json`) | `blt-hackathons--update-stats.yml`, every 6 hours, through the Cloudflare KV API (`scripts/worker-data/kv-get.sh`, `kv-put.sh`) | none |
| `blt-gsoc` | `/js/gsoc2026_stats.generated.js`, `/data/progress.json` | no longer scheduled: GSoC 2026 ended, and `gsoc2026-stats` counted the frozen OWASP-BLT/* GitHub copies; both keep serving their final data from KV (run `POST /__scheduled` with a task by hand if needed) | `CRON_SECRET`, `GH_API_TOKEN`, `GITLAB_TOKEN` (optional), `SLACK_TOKEN_OWASP`, `SLACK_TOKEN_BLT` |
| `my-gsoc-tool` | `/data/github-contributions.json`, `/data/forks.json` | the Worker, from blt-cron at 00:03 | `CRON_SECRET`, `GH_API_TOKEN` |
| `blt-pages` | `/`, `/index.html`, `/leaderboard`, `/leaderboard.html` (pre-rendered), `/data/leaderboard.json`, `/data/leaders.json` | `blt-pages--update-leaderboard.yml` (issue events, daily, pushes of the pages) through the Cloudflare KV API | none |
| `blt-design-contest` | `/`, `/index.html`, `/show-all-entries.html`, `/<contest>.html` and the extensionless forms | `blt-design-contest--build-showcase.yml` (issue events, daily), only pages whose content changed | none |
| `blt-waypoint` | `/forge_data.json` (also at the old `/gitlab_data.json`) | `blt-waypoint--build-site.yml`, daily: per-folder `history?path`, the issue and pull ledgers (about 200 anonymous requests, `FORGE_BUDGET_SECONDS` 420) | none |
| `blt-owasp-projects` | `/www_project_repos.json`, `/repo_status.json`, `/issues.json`, `/known_issue_ids.json`, `/project_repos_links.json` | `blt-owasp-projects--refresh-data.yml`, daily (seeded from the live site) | none |
| `blt-owasp-bumper` | `/` and `/index.html` (key `index.html`) | `blt-owasp-bumper--generate-repo-list.yml`, daily | none |
| `blt-ossh` | `/data/ossh_catalog.json` | `blt-ossh--update-catalog.yml`, daily (`kv-get.sh`, `kv-put.sh`) | none |
| `blt-owasp-metadata` | `/data/metadata.json`, `/data/metadata_matrix.json`, `/data/metadata.csv`, `/data/metadata_matrix.csv`, `/data/metadata_summary.md` | `blt-owasp-metadata--scraper.yml`, weekly | none |
| `blt-tomato` | `/`, `/index.html` (key `index.html`), `/project_repos_links.json` | `blt-tomato--scrape_funding.yml`, weekly | none |
| `blt-panini` | `/slack_apps.json` | `blt-panini--update_slack_apps.yml`, weekly (`kv-get.sh`, `kv-put.sh`) | none |

Shared code is in [`scripts/worker-data/`](../scripts/worker-data/):

- `kv-data.js`: `serveData()` (KV, else the static file), `putData()` (stores `updatedAt` as KV
  metadata), `handleCronDispatch()` (the `POST /__scheduled` endpoint, checked against
  `CRON_SECRET`) and `runChunked()`. The Workers import it and wrangler bundles it, so a change
  here needs a redeploy of every project in the KV table above (`deploy.sh --changed` only looks at
  project folders).
- `kv-put.sh`: writes files to a project's namespace through the Cloudflare API. It reads the
  namespace id from the project's `wrangler.toml` and needs `CLOUDFLARE_API_TOKEN` with
  Workers KV Storage: Edit.
- `kv-get.sh`: reads one key back the same way (exit 3 when the key is missing); blt-hackathons
  keeps its refresh state with it.
- `create-kv.sh`: creates the namespaces (`<project>-data` for each project in the KV table above,
  all bound as `DATA`) and writes their ids into the `wrangler.toml` files, replacing the
  `REPLACE_WITH_KV_ID_<title>` placeholders.
- `testing.mjs`: an in-memory KV, a static `ASSETS` stub and a fetch stub for the projects' tests.
- `kvSiteWorker(patterns, {aliases})` in `kv-data.js`: a whole Worker for a static site whose
  refreshed files live in KV. Paths matching `patterns` are served by `serveData()`, the rest by
  `ASSETS`. The project's `wrangler.toml` lists the same paths in `[assets] run_worker_first`.

Generators that read git.owaspblt.org use [`scripts/forkmesh/ledger.py`](../scripts/forkmesh/ledger.py):
full issue records from `.forkmesh/issues` (labels, comments, votes, an oid cache), pull front
matter from the `forkmesh/pulls` ledger, and `history?path=<folder>` paged by `ref`. It builds on
`blt-hackathons/forkmesh_source.py` and its project attribution rules.

Free plan limits shaped each refresh. A Worker invocation may make 50 subrequests and use 10 ms of CPU:

- **blt-hackathons** stays in Actions. The first sync of a hackathon reads every pull request and
  issue folder of the monorepo on git.owaspblt.org (GitHub events: every pull request and review of
  each repository), hundreds of requests, over one invocation's subrequests and CPU. Later runs
  are incremental: the refresh state in KV (`state/fetch-state.json`) keeps each pull and issue
  folder's git oid, so a run lists the folders (3 requests) and re-reads only the changed ones.
  `FETCH_BUDGET_SECONDS` (900) stops a run early and saves its progress for the next one, so the
  single runner is never held for the whole 30-minute timeout. Slack counts (`trackSlack`) are
  spaced for Slack's 20-a-minute search limit, at most 40 per run. The job seeds the incremental
  review merge from the live files (KV holds the latest data, not git), runs `fetch_stats.py`, and
  writes only the files it rewrote. `stats.json` is written only when something other than
  `lastUpdated` changed. The Worker only streams KV values, so serving costs almost no CPU.
- **blt-gsoc `gsoc2026-stats`** is about 90 GitHub requests, 78 of them searches (30 per minute
  allowed). `runChunked()` does about 3 projects (at most 24 requests) per call, keeping its cursor
  at `state:gsoc2026-stats`; a count that fails keeps the previous day's value.
- **blt-gsoc `progress`** (not scheduled since 2026-10-18; run by hand only) is about 40 requests (GitLab commits per repository, two Slack searches
  per contributor), done in 2 calls of at most 30.
- **my-gsoc-tool** needs 2 requests.

To refresh by hand, call the Worker with the cron secret (`reset` redoes a run that already finished;
repeat chunked tasks until the answer says `"done": true`; `progress` also takes `"day": "YYYY-MM-DD"`):

```bash
curl -X POST https://gsoc.owaspblt.org/__scheduled -H "X-BLT-Cron-Secret: $CRON_SECRET" \
  -d '{"task": "progress", "reset": true}'
```

For blt-hackathons, run the workflow by hand.

## Behaviour changes

- **Issue scripts**: the logic from github-script steps moved into these files:
  - `blt-hackathons/scripts/actions/create-hackathon.mjs`
  - `blt-hackathons/scripts/actions/process-sponsor.mjs`
  - `blt-university/scripts/actions/welcome.mjs`
  - `blt-ossh/scripts/actions/update-profiles.mjs`
  - `blt-jobs/scripts/actions/process-submission.mjs`
  - `blt-profiles/scripts/actions/add-profile.mjs`

  Validation, comments, labels, commits to main and closing the issue all work as before.
  The "eyes" reaction is gone because the job API has no reactions endpoint. Issue links point at
  `<instance>/<owner>/<repo>/issues/<n>`.
- **create-hackathon**: a banner image used to produce invalid JavaScript (a missing comma).
  That is fixed.
- **blt-university**: the old workflows re-ran on every label change. They now run when the issue is
  opened, or when their own label is added.
- **blt-ossh profiles**: the job API cannot list issues. Each issue event adds, updates or removes
  that one issue's profile. The schedule re-reads the issues already in `profiles.json` and drops any
  that were closed or unlabelled. To import older profile issues, run the workflow by hand with
  their numbers.
- **blt-jobs submissions**: the old job polled every open GitLab issue. Now each issue is processed
  when it is opened, edited or labelled, through `createFromIssue()` in `blt-jobs/scripts/submissions.js`
  (the GitLab polling script is gone). The forge has no issue templates, so the job board links to
  the bodies in `blt-jobs/issue-templates/`.
- **README contributor wall** (`readme.yml`): the list used to show only commit authors with a
  known GitHub login. `scripts/readme/contributors.py` now lists every person with a commit in any
  project, as author or co-author, and leaves out bots. It merges each person's emails and names, and
  matches them to a GitHub or git.owaspblt.org account (pull and issue authors from the forge ledgers; GitLab noreply emails and `gitlab:` overrides are still parsed, but nobody links to gitlab.com). Matching uses noreply emails,
  `scripts/readme/contributor-logins.tsv`, the GSoC contributor data, and a few GitHub commit
  searches per run. People without an account are listed by name with an identicon. The job writes
  the following into `.forkmesh/contributors/`, and the README shows the local images:
  - a 64x64 PNG avatar per person (`<slug>.png`)
  - `contributors.json`
  - `lookups.json`, a cache of the network lookups

  Avatars are downloaded again after 30 days, at most 60 per run. A failed download keeps the old
  image or an identicon, and never fails the job. The job needs Pillow and runs with `GH_API_TOKEN`
  for higher GitHub limits.
- **Small fixes**:
  - `blt-tomato` scrapes into the runner checkout (`OUTPUT_DIR`), then KV. It sends `GITHUB_TOKEN` when one is set.
  - `blt-owasp-bumper` writes `public/index.html` in the runner checkout, then KV.
  - `my-gsoc-tool`'s two workflows became Worker tasks (`my-gsoc-tool/worker/refresh.js`). The forks
    list (GitHub repository OWASP-BLT/MY-GSOC-TOOL) is served at `/data/forks.json` instead of being
    written into the README.
- **Scripts**:
  - `scripts/ci/test.sh --changed` tests nothing when the base is empty, all zeros (a new branch)
    or unknown.
  - `scripts/deploy.sh --changed <base>` deploys projects whose `projects.tsv` folder changed.
  - `scripts/ci/tests.tsv` has new rows:
    - `blt-hackathons`, `blt-hackerhouse`, `blt-next` and `blt-owasp-projects`, from their GitLab test jobs
    - `blt-ossh` and `scripts`, for the action scripts

## CI on this runner

`ci.yml` runs the same `scripts/ci/tests.tsv` commands as before, but some projects cannot run on
this server:

- Flutter projects (`blt-flutter`, `blt-netguardian-client`, `blt-timer-flutter`, `blt-vanish-flutter`)
  and `blt-cli` (Rust) are reported as skipped.
- `blt-mcp` requires Python 3.12; its `tests.tsv` row installs with `--ignore-requires-python`, so it runs on the server's 3.13 (the OAuth and SSE tests need loopback connections).
- `blt-core` passes only if xvfb, Chromium and libmemcached are installed, and that needs sudo.
- `blt-safecloak` runs `playwright install --with-deps`, which needs sudo.

Run these on a machine with the toolchain: `scripts/ci/test.sh <project>`.

## Not ported

| What | Why |
| --- | --- |
| `blt-extension` create-release (GitHub release with the zip) | There is no release-upload API yet, and tag pushes do not trigger workflows. `scripts/release-chrome.sh --package-only` builds the zip locally. |
| `blt-vanish` release (Flutter APK/desktop builds + GitHub release) | No Flutter or Java on the runner, and no release API. |
| `blt-waypoint` screenshot-repos (Playwright) | No Chromium, and no sudo for `--with-deps`. |
| `blt-mcp` Rust build, nightly and tagged release uploads (GitLab packages) | The jobs built `blt-cli/`, now a separate project. There is no Rust and no package registry. `blt-mcp/.gitlab-ci.yml` is deleted; run the golden-snapshot test locally with `BLT_VERIFY_SNAPSHOTS=true pytest`. |
| `blt-university` validate-labs, validate-vulnerability-intel, Jekyll build + commit of `public/`, Playwright e2e | Jekyll needs Ruby and e2e needs Chromium. The commands are in `blt-university/README.md` ("Continuous integration and deployment"); `.gitlab-ci.yml` is deleted. Build `public/` locally and commit it. |
| `blt-hackerhouse` D1 migrations and staging deploy | `deploy.yml` deploys production with pywrangler but does not apply migrations. Run `npx wrangler d1 migrations apply hackerhouse --remote` by hand (`blt-hackerhouse/README.md`, Deploy). `.gitlab-ci.yml` is deleted. |
| `blt-toasty` lint (black/ruff/bandit) and staging/production environments | Lint runs from `.pre-commit-config.yaml`; `blt-toasty/.gitlab-ci.yml` is deleted. Tests run in CI, and `deploy.sh` deploys the default environment. |
| `blt-pages` Playwright tests, `blt-netguardian` Flutter client tests | No Chromium or Flutter on the runner. Run them locally: `npm ci && npm test` in blt-pages, `flutter test` in blt-netguardian/client (`blt-netguardian-client` in `scripts/ci/tests.tsv` runs where Flutter exists). Both `.gitlab-ci.yml` files are deleted. |
| `blt-safecloak` desktop client builds | Already disabled in GitLab, and `.gitlab-ci.yml` is deleted. `public/install.sh` builds the client from a sparse clone of `blt-safecloak/client`; there are no prebuilt downloads. |
| GitLab Pages / Cloudflare deploy jobs (`blt-gsoc`, `blt-university`, `blt-design-contest`, `blt-toasty`, `blt-hackerhouse`) | Replaced by `scripts/deploy.sh` and `deploy.yml`. |
