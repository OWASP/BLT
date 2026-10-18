// blt-owasp-metadata Worker: the static site (./public) plus the generated dataset, which lives in
// KV instead of git. The workflow .forkmesh/blt-owasp-metadata--scraper.yml (weekly) runs
// scrape_metadata.py (thousands of GitHub requests, far over a free-plan Worker invocation's 50)
// and writes the files into KV (scripts/refresh-kv.sh). This Worker serves them from KV, falling
// back to the copies committed under public/data/ while KV has none.
import { serveData } from "../../scripts/worker-data/kv-data.js";

export const DATA_FILES = {
  "/data/metadata.json": undefined,
  "/data/metadata_matrix.json": undefined,
  "/data/metadata.csv": undefined,
  "/data/metadata_matrix.csv": undefined,
  "/data/metadata_summary.md": "text/markdown; charset=utf-8",
};

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);
    if (Object.prototype.hasOwnProperty.call(DATA_FILES, pathname)) {
      return serveData(request, env, ctx, { key: pathname.slice(1), contentType: DATA_FILES[pathname] });
    }
    return env.ASSETS.fetch(request);
  },
};
