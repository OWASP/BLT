// Scheduled jobs for BLT Workers. Each job calls POST /__scheduled on its
// Worker through a service binding when its cron expression matches (UTC).
export const JOBS = [
  { name: "blt-pool", binding: "POOL", cron: "0 */2 * * *" },
  { name: "blt-leaf", binding: "LEAF", cron: "0 * * * *" },
  { name: "blt-lettuce", binding: "LETTUCE", cron: "* * * * *" },
  { name: "blt-monitor", binding: "MONITOR", cron: "*/5 * * * *" },
  { name: "blt-sizzle", binding: "SIZZLE", cron: "0 * * * *" },
  { name: "blt-netguardian", binding: "NETGUARDIAN", cron: "*/5 * * * *" },
  { name: "blt-toasty", binding: "TOASTY", cron: "0 * * * *" },
];
