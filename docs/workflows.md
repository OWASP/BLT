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
| `readme.yml` | GitHub `readme.yml` | `17 * * * *` | none |
| `blt-cve--build-index.yml` | GitHub | push to main under `blt-cve/public/cves`, `public/schema`, `scripts/build_index.py` | CF |
| `blt-design-contest--build-showcase.yml` | GitLab `build_showcase` | `47 7 * * *`, push under `blt-design-contest/scripts/` | `GITLAB_TOKEN` (optional), CF |
| `blt-extension--release.yml` | GitHub `release.yml` + packaging from `create-release.yml` | dispatch only (input `publish`) | `CHROME_CLIENT_ID`, `CHROME_CLIENT_SECRET`, `CHROME_REFRESH_TOKEN` |
| `blt-gsoc--update-gsoc2026-stats.yml` | GitHub | `17 2 * * *` | `GH_API_TOKEN`, CF |
| `blt-gsoc--update-progress.yml` | GitLab `update-progress` | `7 23 * * *` | `GITLAB_TOKEN` (optional), `SLACK_TOKEN_OWASP`, `SLACK_TOKEN_BLT`, CF |
| `blt-hackathons--create-hackathon.yml` | GitHub | issues opened/labeled with `hackathon-creation` | CF |
| `blt-hackathons--process-sponsor.yml` | GitHub | issues opened/labeled with `sponsorship` | CF |
| `blt-hackathons--update-stats.yml` | GitHub | `0 * * * *`, push under `blt-hackathons/` (hackathons starting through 2026-05-31) | `GH_API_TOKEN`, `GITLAB_TOKEN`, CF |
| `blt-hackathons--update-future-hackathons.yml` | GitLab `update-future-hackathons` | `37 0 * * *` (hackathons starting after 2026-05-31) | `GH_API_TOKEN`, `GITLAB_TOKEN`, CF |
| `blt-jobs--expire-jobs.yml` | GitLab `expire_jobs` | `41 1 * * *` | CF |
| `blt-jobs--process-submissions.yml` | GitLab `process_submissions` | issues opened/edited/labeled that look like job, seeker or flag submissions; dispatch input `issue` | CF |
| `blt-ossh--update-catalog.yml` | GitHub | `0 6 * * *` | `DISCORD_BOT_TOKEN` (optional), CF |
| `blt-ossh--update-profiles.yml` | GitHub | `0 */6 * * *`, issue events on `profile` issues; dispatch input `issues` to import issues | CF |
| `blt-owasp-bumper--generate-repo-list.yml` | GitHub + GitLab `pages` | `0 0 * * *`, push of `generate_repo_list.py` | `GH_API_TOKEN`, CF |
| `blt-owasp-metadata--scraper.yml` | GitHub | `0 3 * * 1` | `GH_API_TOKEN`, CF |
| `blt-owasp-projects--refresh-data.yml` | GitLab `refresh_data` | `23 4 * * *` | `GH_API_TOKEN` (required by `main.py`), CF |
| `blt-owasp-projects--sweep-repos.yml` | GitLab `sweep_repos` (manual) | dispatch only | `GH_API_TOKEN`, `SLACK_WEBHOOK_URL_SWEEP` |
| `blt-pages--update-leaderboard.yml` | GitLab `update_leaderboard` | `11 5 * * *`, push under `blt-pages/scripts/` | `GITLAB_TOKEN` (optional), CF |
| `blt-panini--update_slack_apps.yml` | GitHub | `0 0 * * 0` | CF |
| `blt-tomato--scrape_funding.yml` | GitHub | `0 18 * * 5`, push under `blt-tomato/.github/scripts/` | `GH_API_TOKEN`, CF |
| `blt-university--course-submission.yml` | GitHub | issue opened with `course-submission` or `[COURSE]` title, or that label added | none |
| `blt-university--enrollment.yml` | GitHub | issue opened with `enrollment` or `[ENROLLMENT]` title, or that label added | none |
| `blt-waypoint--build-site.yml` | GitLab `build_site` | `29 6 * * *`, push under `blt-waypoint/scripts/` or of `public/github_data.json` | `GITLAB_TOKEN` (optional), CF |
| `my-gsoc-tool--update-dashboard.yml` | GitHub | `0 0 * * *`, push of `public/config.json` / `public/data/` | `GH_API_TOKEN`, CF |
| `my-gsoc-tool--update-forks.yml` | GitHub | `0 0 * * *`, push under `my-gsoc-tool/` | `GH_API_TOKEN` |

### Schedules chosen for the GitLab jobs

GitLab pipeline schedules were set in the GitLab UI, so their times were not in the repository. The schedules above came from:

- `blt-gsoc` update-progress: `7 23 * * *`. The `.gitlab-ci.yml` comment gives `0 23 * * *`, and the job fills in the current day.
- `blt-hackathons` future hackathons: `37 0 * * *`. The README says the schedule is daily.
- `blt-jobs` expire: `41 1 * * *`, daily. Submissions are now driven by issue events instead of polling.
- `blt-owasp-projects` refresh: `23 4 * * *`, daily. This is OWASP repository metadata.
- `blt-pages` leaderboard: `11 5 * * *`, daily. The page carries a timestamp, so an hourly run would commit every hour.
- `blt-waypoint` data: `29 6 * * *`, daily.
- `blt-design-contest` showcase: `47 7 * * *`, daily. The old setup only rebuilt on push, but submissions are GitLab issues that change independently of pushes.

## Behaviour changes

- **Issue scripts**: the logic from github-script steps moved into these files:
  - `blt-hackathons/scripts/actions/create-hackathon.mjs`
  - `blt-hackathons/scripts/actions/process-sponsor.mjs`
  - `blt-university/scripts/actions/welcome.mjs`
  - `blt-ossh/scripts/actions/update-profiles.mjs`
  - `blt-jobs/scripts/actions/process-submission.mjs`

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
  when it is opened, edited or labelled, through the existing `createFromIssue()` in
  `process-gitlab-submissions.js`. GitLab-only scripts that remain:
  - `process-gitlab-submissions.js`, for issues still on gitlab.com
  - `blt-design-contest`, `blt-pages` and `blt-waypoint`, which read data from gitlab.com
- **Small fixes**:
  - `blt-tomato` scrapes into `public/`, where the site lives. It sends `GITHUB_TOKEN` when one is set.
  - `blt-owasp-bumper` writes `public/index.html`.
  - `my-gsoc-tool` scripts are real files (`my-gsoc-tool/scripts/`) instead of being generated at
    run time. Its forks list reads the GitHub repository OWASP-BLT/MY-GSOC-TOOL.
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
- `blt-mcp` requires Python 3.12, so it fails on the server's 3.13.
- `blt-core` passes only if xvfb, Chromium and libmemcached are installed, and that needs sudo.
- `blt-safecloak` runs `playwright install --with-deps`, which needs sudo.

Run these on a machine with the toolchain: `scripts/ci/test.sh <project>`.

## Not ported

| What | Why |
| --- | --- |
| `blt-extension` create-release (GitHub release with the zip) | There is no release-upload API yet, and tag pushes do not trigger workflows. `scripts/release-chrome.sh --package-only` builds the zip locally. |
| `blt-vanish` release (Flutter APK/desktop builds + GitHub release) | No Flutter or Java on the runner, and no release API. |
| `blt-waypoint` screenshot-repos (Playwright) | No Chromium, and no sudo for `--with-deps`. |
| `blt-mcp` Rust build, nightly and tagged release uploads (GitLab packages) | The jobs built `blt-cli/`, now a separate project. There is no Rust and no package registry. The golden-snapshot test stays in `blt-mcp/.gitlab-ci.yml` for reference. |
| `blt-university` validate-labs, validate-vulnerability-intel, Jekyll build + commit of `public/`, Playwright e2e | Jekyll needs Ruby and e2e needs Chromium. They stay in `blt-university/.gitlab-ci.yml`. Build `public/` locally (`bundle exec jekyll build -d public`) and commit it. |
| `blt-hackerhouse` D1 migrations and staging deploy | `deploy.yml` deploys production with pywrangler but does not apply migrations. Run `npx wrangler d1 migrations apply hackerhouse --remote` by hand. Kept in `blt-hackerhouse/.gitlab-ci.yml`. |
| `blt-toasty` lint (black/ruff/bandit) and staging/production environments | Kept in `blt-toasty/.gitlab-ci.yml`. Tests run in CI, and `deploy.sh` deploys the default environment. |
| `blt-pages` Playwright tests, `blt-netguardian` Flutter client tests | No Chromium or Flutter on the runner. Kept in their `.gitlab-ci.yml`. |
| `blt-safecloak` desktop client builds | Already disabled in GitLab. The commented jobs stay in `blt-safecloak/.gitlab-ci.yml` because a test reads them. |
| GitLab Pages / Cloudflare deploy jobs (`blt-gsoc`, `blt-university`, `blt-design-contest`, `blt-toasty`, `blt-hackerhouse`) | Replaced by `scripts/deploy.sh` and `deploy.yml`. |
