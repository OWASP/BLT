// blt-design-contest Worker: the static site (./public) plus the showcase pages, which live in KV
// instead of git. .forkmesh/blt-design-contest--build-showcase.yml (issue events on contest
// issues, a daily run and pushes to scripts/) runs scripts/build_showcase.py and writes the pages
// that changed into KV (scripts/refresh-kv.sh). This Worker serves those pages from KV under their
// usual URLs, falling back to the copies committed under public/ when KV has none yet.
import { kvSiteWorker } from "../../scripts/worker-data/kv-data.js";

// index.html, show-all-entries.html and one page per contest (CONTESTS ids in build_showcase.py).
export const PAGES = [
  "index",
  "show-all-entries",
  "blt-tshirt",
  "blt-logo",
  "blt-homepage",
  "blt-video-meme",
  "blt-welcome-video",
  "appsecil-tshirt",
];

const aliases = { "/": "index.html" };
for (const page of PAGES) aliases[`/${page}`] = `${page}.html`;

export default kvSiteWorker(PAGES.map((page) => `/${page}.html`), { aliases });
