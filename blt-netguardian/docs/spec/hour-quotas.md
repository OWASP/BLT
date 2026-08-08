# Hour quotas / back-pressure (W8)

Org ingest is capped on two windows, both stored in `ng_metrics` (the `day` column holds the bucket key):

| Gate | Env | Default | Bucket key | `Retry-After` |
|------|-----|---------|------------|---------------|
| Per-minute RPM | `NG_INGEST_RPM` | 60 | `YYYY-MM-DDTHH:MM` (UTC) | `60` |
| Per-hour RPH | `NG_INGEST_RPH` | 1000 | `YYYY-MM-DDTHH` (UTC) | seconds until next UTC hour |

Both return HTTP **429** with `error: rate_limited` and a `scope` of `minute` or `hour`.

Set a limit to `0` to disable that gate. Duplicate-nonce replays do **not** consume quota (checked before rate gates).

## Why both

Minute RPM stops burst abuse. Hour RPH stops sustained flood that stays under the per-minute ceiling (e.g. 59/min × 60 ≈ 3540/hour without an hour cap).
