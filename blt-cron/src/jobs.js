// Scheduled jobs for BLT Workers. Each job calls POST /__scheduled on its
// Worker through a service binding when its cron expression matches (UTC).
// An optional `task` is sent in the body so one Worker can run several jobs.
// A cron over a minute range (e.g. "17-31 2 * * *") calls the Worker once a minute:
// those Workers refresh their data in chunks to stay under the free plan's
// 50 subrequests per invocation and stop once the day's refresh is done.
export const JOBS = [
  { name: "blt-pool", binding: "POOL", cron: "0 */2 * * *" },
  { name: "blt-leaf", binding: "LEAF", cron: "0 * * * *" },
  { name: "blt-lettuce", binding: "LETTUCE", cron: "* * * * *" },
  { name: "blt-monitor", binding: "MONITOR", cron: "*/5 * * * *" },
  { name: "blt-sizzle", binding: "SIZZLE", cron: "0 * * * *" },
  { name: "blt-netguardian", binding: "NETGUARDIAN", cron: "*/5 * * * *" },
  { name: "blt-toasty", binding: "TOASTY", cron: "0 * * * *" },
  { name: "blt-gsoc-stats", binding: "GSOC", cron: "17-31 2 * * *", task: "gsoc2026-stats" },
  { name: "blt-gsoc-progress", binding: "GSOC", cron: "7-11 23 * * *", task: "progress" },
  { name: "my-gsoc-tool", binding: "GSOC_TOOL", cron: "3 0 * * *" },
];
