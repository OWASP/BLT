// blt-pages Worker: the static site (./public) plus the leaderboard data, which lives in KV instead
// of git. .forkmesh/blt-pages--update-leaderboard.yml (daily, on blt-pages issue events and on pushes
// of the generator or the two pre-rendered pages) runs scripts/generate_leaderboard.py and writes
// data/leaderboard.json, data/leaders.json and the pre-rendered index.html and leaderboard.html to KV
// (scripts/refresh-kv.sh). Those paths are served from KV, falling back to the committed files.
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

export const KV_PATHS = ["/index.html", "/leaderboard.html", "/data/leaderboard.json", "/data/leaders.json"];

export default kvSiteWorker(KV_PATHS, { aliases: { "/": "index.html", "/leaderboard": "leaderboard.html" } });
