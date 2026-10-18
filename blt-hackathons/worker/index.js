// blt-hackathons Worker: the static site (./public) plus the hackathon statistics, which live in
// KV instead of git. The workflow .forkmesh/blt-hackathons--update-stats.yml (every 6 hours) runs
// fetch_stats.py (a first sync is hundreds of requests, too many for one Worker invocation on the
// free plan) and writes the files it changed straight into KV (scripts/worker-data/kv-put.sh).
// This Worker serves /stats.json and /hackathon-data/*.json from KV, falling back to the files
// committed under public/ when KV has no copy yet. The refresh state (state/fetch-state.json) is
// in the same namespace but not served.
import { serveData } from "../../scripts/worker-data/kv-data.js";

export const DATA_PATH = /^\/(stats\.json|hackathon-data\/[A-Za-z0-9_.-]+\.json)$/;

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);
    const match = DATA_PATH.exec(pathname);
    if (match && !pathname.includes("..")) return serveData(request, env, ctx, { key: match[1] });
    return env.ASSETS.fetch(request);
  },
};
