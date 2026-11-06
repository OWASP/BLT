// blt-owasp-projects Worker: the static dashboard (./public) plus its data files, which live in KV
// instead of git. The workflow .forkmesh/blt-owasp-projects--refresh-data.yml (daily) runs the
// generators (thousands of GitHub requests, far over a free-plan Worker invocation's 50) and writes
// the changed files into KV (scripts/refresh-kv.sh). This Worker serves them from KV, falling back
// to the copies committed under public/ while KV has none. blt-cron calls POST /__scheduled with
// {task: "new-projects"} hourly to post new www-project repositories to Slack (new-projects.js).
import { handleCronDispatch, kvSiteWorker } from "../../scripts/worker-data/kv-data.js";
import { checkNewProjects } from "./new-projects.js";

export const DATA_PATHS = [
  "/www_project_repos.json",
  "/repo_status.json",
  "/issues.json",
  "/known_issue_ids.json",
  "/project_repos_links.json",
];

export const TASKS = { "new-projects": checkNewProjects };

const site = kvSiteWorker(DATA_PATHS);

export default {
  async fetch(request, env, ctx) {
    if (new URL(request.url).pathname === "/__scheduled") return handleCronDispatch(request, env, TASKS);
    return site.fetch(request, env, ctx);
  },
};
