// blt-waypoint Worker: the static dashboard (./public) plus /forge_data.json, the per-folder
// project data that .forkmesh/blt-waypoint--build-site.yml generates daily from git.owaspblt.org
// and writes straight into KV (scripts/worker-data/kv-put.sh). Nothing is committed for it.
// KV answers first; until it has a copy the committed public/forge_data.json is served.
// /gitlab_data.json (the retired GitLab reader's file) is served as the same data.
// /screenshots/<folder>.jpg and /screenshots/index.json are the daily captures of each live site
// (scripts/capture_screenshots.py, same workflow); they exist only in KV, so before the first
// capture they answer 404 and the pages show a placeholder.
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

export const DATA_PATHS = ["/forge_data.json", /^\/screenshots\/(?:index\.json|[a-z0-9][\w.-]*\.jpg)$/];
export const LEGACY_PATHS = { "/gitlab_data.json": "/forge_data.json" };

const site = kvSiteWorker(DATA_PATHS);

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const target = LEGACY_PATHS[url.pathname];
    if (target) {
      url.pathname = target;
      return site.fetch(new Request(url, request), env, ctx);
    }
    return site.fetch(request, env, ctx);
  },
};
