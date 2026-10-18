// blt-waypoint Worker: the static dashboard (./public) plus /forge_data.json, the per-folder
// project data that .forkmesh/blt-waypoint--build-site.yml generates daily from git.owaspblt.org
// and writes straight into KV (scripts/worker-data/kv-put.sh). Nothing is committed for it.
// KV answers first; until it has a copy the committed public/forge_data.json is served.
// /gitlab_data.json (the retired GitLab reader's file) is served as the same data.
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

export const DATA_PATHS = ["/forge_data.json"];
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
