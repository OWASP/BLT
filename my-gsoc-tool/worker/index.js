// my-gsoc-tool Worker: the static dashboard (./public) plus two data files kept in KV.
// blt-cron calls POST /__scheduled once a day; see README.md.
import { handleCronDispatch, serveData } from "../../scripts/worker-data/kv-data.js";
import { CONTRIBUTIONS_KEY, FORKS_KEY, refreshContributions, refreshForks } from "./refresh.js";

export const TASKS = { contributions: refreshContributions, forks: refreshForks };
const DATA_PATHS = new Set([`/${CONTRIBUTIONS_KEY}`, `/${FORKS_KEY}`]);

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);
    if (pathname === "/__scheduled") return handleCronDispatch(request, env, TASKS);
    if (DATA_PATHS.has(pathname)) return serveData(request, env, ctx, { key: pathname.slice(1) });
    return env.ASSETS.fetch(request);
  },

  // Unused here (this account's only cron trigger is blt-cron); a fork of the template can add
  // `[triggers] crons = ["3 0 * * *"]` to wrangler.toml instead.
  async scheduled(controller, env, ctx) {
    const run = async (task) => {
      try {
        await task(env, { scheduledTime: controller.scheduledTime });
      } catch (error) {
        console.error(error && error.message);
      }
    };
    ctx.waitUntil(Promise.all(Object.values(TASKS).map(run)));
  },
};
