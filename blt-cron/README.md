# BLT Cron

<p align="center"><img src="logo.svg" alt="blt-cron logo" width="160" height="160"></p>

One Cloudflare Worker holds the account's only cron trigger (`* * * * *`) and runs every BLT Worker's scheduled job on that job's own schedule. Cloudflare's free plan allows 5 cron triggers per account; this keeps all of them in one.

Each minute, `blt-cron` checks the jobs in `src/jobs.js` and, for each one whose cron expression (UTC) matches, sends `POST /__scheduled` with `{cron, scheduledTime}` (plus `task` when the row has one) to that Worker through a service binding. The Worker runs the same code its cron trigger used to run.

Some Workers refresh data into Workers KV instead of having a workflow commit it to git (see [`docs/workflows.md`](../docs/workflows.md#data-in-workers-kv)). A refresh too large for one invocation (the free plan allows 50 subrequests) uses a minute range such as `17-31 2 * * *`: the Worker does a chunk per call, keeps its cursor in KV and does nothing once the day's refresh is done.

| Job | Worker | Schedule (UTC) | Task |
| --- | --- | --- | --- |
| my-gsoc-tool | my-gsoc-tool | 00:03 | all (`contributions`, `forks`) |
| hackerhouse | hackerhouse | every 5 minutes (:02, :07, ...) | forge poll (git.owaspblt.org commits, issues, pulls) |
| blt-sammich | blt-sammich | every 5 minutes (:04, :09, ...) | send due `/setreminder` reminders |
| blt-pool-leaderboard | blt-github-app (pool) | every 20 minutes (:06, :26, :46) | `forge-leaderboard`: git.owaspblt.org pulls ledger into the PR leaderboard |

The GSoC 2026 progress job (`blt-gsoc-progress`, task `progress`) was turned off on 2026-10-18 because GSoC 2026 coding ended on 17 Aug. blt-gsoc still has the `progress` task and its KV data, so the progress page shows the final state; it can be run by hand (see `docs/workflows.md`).

The other rows of `src/jobs.js` replace the cron triggers of blt-leaf, blt-lettuce, blt-monitor, blt-sizzle, and blt-netguardian. blt-toasty's hourly call was dropped on 2026-10-18 (its scheduled handler is a no-op). blt-github-app's (pool) 2-hourly stale-assignment sweep was dropped on 2026-10-20 (issue #38): it polled the frozen OWASP-BLT/* GitHub repositories, and BLT-Action now releases stale `/assign` claims on git.owaspblt.org.

## Add a job

1. In the target Worker, handle `POST /__scheduled` (check the `X-BLT-Cron-Secret` header against its `CRON_SECRET` secret) and remove its `[triggers] crons`. JavaScript Workers can use `handleCronDispatch()` from [`scripts/worker-data/kv-data.js`](../scripts/worker-data/kv-data.js).
2. Add a `[[services]]` binding in `wrangler.toml` and a row in `src/jobs.js`.
3. Set the same `CRON_SECRET` on both Workers: `npx wrangler secret put CRON_SECRET`.

## Develop

```bash
npm test
scripts/deploy.sh blt-cron
```
