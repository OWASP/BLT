// blt-owasp-bumper Worker: the dashboard page, which lives in KV instead of git. The workflow
// .forkmesh/blt-owasp-bumper--generate-repo-list.yml (daily) runs generate_repo_list.py (several
// thousand GitHub requests, far over a free-plan Worker invocation's 50) and writes the page into
// KV as index.html (scripts/refresh-kv.sh). This Worker serves / and /index.html from KV, falling
// back to the page committed under public/ while KV has none.
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

export default kvSiteWorker(["/index.html"], { aliases: { "/": "index.html" } });
