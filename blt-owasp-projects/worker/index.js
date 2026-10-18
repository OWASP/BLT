// blt-owasp-projects Worker: the static dashboard (./public) plus its data files, which live in KV
// instead of git. The workflow .forkmesh/blt-owasp-projects--refresh-data.yml (daily) runs the
// generators (thousands of GitHub requests, far over a free-plan Worker invocation's 50) and writes
// the changed files into KV (scripts/refresh-kv.sh). This Worker serves them from KV, falling back
// to the copies committed under public/ while KV has none.
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

export const DATA_PATHS = [
  "/www_project_repos.json",
  "/repo_status.json",
  "/issues.json",
  "/known_issue_ids.json",
  "/project_repos_links.json",
];

export default kvSiteWorker(DATA_PATHS);
