# BLT Cron

One Cloudflare Worker holds the account's only cron trigger (`* * * * *`) and runs every BLT Worker's scheduled job on that job's own schedule. Cloudflare's free plan allows 5 cron triggers per account; this keeps all of them in one.

Each minute, `blt-cron` checks the jobs in `src/jobs.js` and, for each one whose cron expression (UTC) matches, sends `POST /__scheduled` with `{cron, scheduledTime}` (plus `task` when the row has one) to that Worker through a service binding. The Worker runs the same code its cron trigger used to run.

Some Workers refresh data into Workers KV instead of having a workflow commit it to git (see [`docs/workflows.md`](../docs/workflows.md#data-in-workers-kv)). A refresh too large for one invocation (the free plan allows 50 subrequests) uses a minute range such as `17-31 2 * * *`: the Worker does a chunk per call, keeps its cursor in KV and does nothing once the day's refresh is done.

| Job | Worker | Schedule (UTC) | Task |
| --- | --- | --- | --- |
| blt-gsoc-stats | blt-gsoc | 02:17-02:31, once a minute | `gsoc2026-stats` |
| blt-gsoc-progress | blt-gsoc | 23:07-23:11, once a minute | `progress` |
| my-gsoc-tool | my-gsoc-tool | 00:03 | all (`contributions`, `forks`) |

The other rows of `src/jobs.js` replace the cron triggers of blt-github-app (pool), blt-leaf, blt-lettuce, blt-monitor, blt-sizzle, blt-netguardian and blt-toasty.

## Add a job

1. In the target Worker, handle `POST /__scheduled` (check the `X-BLT-Cron-Secret` header against its `CRON_SECRET` secret) and remove its `[triggers] crons`. JavaScript Workers can use `handleCronDispatch()` from [`scripts/worker-data/kv-data.js`](../scripts/worker-data/kv-data.js).
2. Add a `[[services]]` binding in `wrangler.toml` and a row in `src/jobs.js`.
3. Set the same `CRON_SECRET` on both Workers: `npx wrangler secret put CRON_SECRET`.

## Develop

```bash
npm test
scripts/deploy.sh blt-cron
```
