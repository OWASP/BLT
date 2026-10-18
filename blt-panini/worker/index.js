// blt-panini Worker: the static site (./public) plus the Slack apps list, which lives in KV instead
// of git. The workflow .forkmesh/blt-panini--update_slack_apps.yml (weekly) runs
// update_slack_apps.py (dozens of slow, rate-limited page scrapes, too many for one free-plan
// Worker invocation) and writes slack_apps.json into KV (scripts/refresh-kv.sh). This Worker serves
// /slack_apps.json from KV, falling back to the copy committed under public/ while KV has none.
// banned_apps.json is curated in git and stays a static file.
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

export default kvSiteWorker(["/slack_apps.json"]);
