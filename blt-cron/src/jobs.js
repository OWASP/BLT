// Scheduled jobs for BLT Workers. Each job calls POST /__scheduled on its
// Worker through a service binding when its cron expression matches (UTC).
// An optional `task` is sent in the body so one Worker can run several jobs.
// A cron over a minute range (e.g. "17-31 2 * * *") calls the Worker once a minute:
// those Workers refresh their data in chunks to stay under the free plan's
// 50 subrequests per invocation and stop once the day's refresh is done.
export const JOBS = [
  { name: "blt-pool", binding: "POOL", cron: "0 */2 * * *" },
  { name: "blt-leaf", binding: "LEAF", cron: "0 * * * *" },
  { name: "blt-lettuce", binding: "LETTUCE", cron: "0,30 * * * *" },
  { name: "blt-monitor", binding: "MONITOR", cron: "*/5 * * * *" },
  { name: "blt-sizzle", binding: "SIZZLE", cron: "0 * * * *" },
  { name: "blt-netguardian", binding: "NETGUARDIAN", cron: "*/5 * * * *" },
  { name: "my-gsoc-tool", binding: "GSOC_TOOL", cron: "3 0 * * *" },
  { name: "hackerhouse", binding: "HACKERHOUSE", cron: "2-59/5 * * * *" },
  { name: "blt-sammich", binding: "SAMMICH", cron: "4-59/5 * * * *" },
];
// blt-gsoc-progress (task "progress", 23:07-23:11) was removed on 2026-10-18: GSoC 2026 coding
// ended on 17 Aug. The task code and its KV data stay, so /data/progress.json keeps the final state.
// blt-toasty (hourly) was removed the same day: its GitLab shadow mode is gone and its scheduled
// handler is a no-op.
// blt-gsoc-stats (task "gsoc2026-stats", 02:17-02:31) was removed the same day: it counted activity on
// the old OWASP-BLT/* GitHub repos, which are frozen copies now, so its numbers could not change.
// /js/gsoc2026_stats.generated.js keeps serving the last stored data.
