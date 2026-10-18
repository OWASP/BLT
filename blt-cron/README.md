# BLT Cron

One Cloudflare Worker holds the account's only cron trigger (`* * * * *`) and runs every BLT Worker's scheduled job on that job's own schedule. Cloudflare's free plan allows 5 cron triggers per account; this keeps all of them in one.

Each minute, `blt-cron` checks the jobs in `src/jobs.js` and, for each one whose cron expression (UTC) matches, sends `POST /__scheduled` with `{cron, scheduledTime}` to that Worker through a service binding. The Worker runs the same code its cron trigger used to run.

## Add a job

1. In the target Worker, handle `POST /__scheduled` (check the `X-BLT-Cron-Secret` header against its `CRON_SECRET` secret) and remove its `[triggers] crons`.
2. Add a `[[services]]` binding in `wrangler.toml` and a row in `src/jobs.js`.
3. Set the same `CRON_SECRET` on both Workers: `npx wrangler secret put CRON_SECRET`.

## Develop

```bash
npm test
scripts/deploy.sh blt-cron
```
