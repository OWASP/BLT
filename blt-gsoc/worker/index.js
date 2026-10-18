// blt-gsoc Worker: static site (./public) plus two data files kept in KV instead of git.
// blt-cron calls POST /__scheduled with {task: "gsoc2026-stats" | "progress"}; see README.md.
import { handleCronDispatch, serveData } from "../../scripts/worker-data/kv-data.js";
import { KEY as STATS_KEY, refreshGsoc2026Stats } from "./gsoc2026-stats.js";
import { KEY as PROGRESS_KEY, refreshProgress } from "./progress.js";

export const TASKS = {
  "gsoc2026-stats": refreshGsoc2026Stats,
  progress: refreshProgress,
};

const DATA_PATHS = new Set([`/${STATS_KEY}`, `/${PROGRESS_KEY}`]);

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);
    if (pathname === "/__scheduled") return handleCronDispatch(request, env, TASKS);
    if (DATA_PATHS.has(pathname)) return serveData(request, env, ctx, { key: pathname.slice(1) });
    return env.ASSETS.fetch(request);
  },
};
