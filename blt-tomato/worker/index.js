// blt-tomato Worker: the funding page and its JSON, which live in KV instead of git. The workflow
// .forkmesh/blt-tomato--scrape_funding.yml (weekly) runs the funding scraper (over a thousand
// requests, far over a free-plan Worker invocation's 50) and writes both files into KV
// (scripts/refresh-kv.sh). This Worker serves /, /index.html and /project_repos_links.json from
// KV, falling back to the copies committed under public/ while KV has none.
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

export default kvSiteWorker(["/index.html", "/project_repos_links.json"], { aliases: { "/": "index.html" } });
