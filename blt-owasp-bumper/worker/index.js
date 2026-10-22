// blt-owasp-bumper Worker: the page (public/index.html, app.js) is static; its data,
// data/repos.json, lives in KV. The workflow .forkmesh/blt-owasp-bumper--generate-repo-list.yml
// (daily) runs generate_repo_list.py (thousands of GitHub requests, far over a free-plan Worker
// invocation's 50) and writes the file into KV (scripts/refresh-kv.sh). This Worker serves it from
// KV, falling back to the copy committed under public/data/ while KV has none.
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

export default kvSiteWorker(["/data/repos.json"]);
