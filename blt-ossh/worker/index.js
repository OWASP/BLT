// blt-ossh Worker: the static site (./public) plus the community catalog, which lives in KV instead
// of git. The workflow .forkmesh/blt-ossh--update-catalog.yml (daily) runs the DEV.to, Discord and
// Reddit fetchers (over 50 requests and a 1.3 MB JSON rewrite, too much for one free-plan Worker
// invocation) and writes the catalog into KV (scripts/refresh-kv.sh). This Worker serves
// /data/ossh_catalog.json from KV, falling back to the copy committed under public/ while KV has
// none. data/profiles.json stays a committed file (blt-ossh--update-profiles.yml).
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

export default kvSiteWorker(["/data/ossh_catalog.json"]);
