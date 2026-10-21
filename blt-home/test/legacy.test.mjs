// The legacy allowlist in src/legacy.js must cover every route in the legacy
// Django app's urls.py (blt-core, or blt-legacy after a rename).
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { LEGACY_API_SEGMENTS, LEGACY_EXCLUDED, LEGACY_SEGMENTS } from "../src/legacy.js";

const repo = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const urlsPy = ["blt-legacy", "blt-core"].map((d) => join(repo, d, "blt", "urls.py")).find((p) => existsSync(p));

function routes(text) {
  const out = [];
  for (const m of text.matchAll(/\b(?:re_path|path)\(\s*r?["']([^"']*)["']/g)) out.push(m[1].replace(/^\^/, ""));
  return out;
}
const firstSegment = (p) => p.split(/[/<(\\$?]/)[0];

test("every urls.py route segment is listed or deliberately excluded", { skip: !urlsPy && "legacy app not in this checkout" }, () => {
  const text = readFileSync(urlsPy, "utf8");
  const missing = new Set();
  const missingApi = new Set();
  for (const r of routes(text)) {
    const seg = firstSegment(r);
    if (seg === "api") {
      const sub = firstSegment(r.slice(4));
      if (sub && !LEGACY_API_SEGMENTS.has(sub)) missingApi.add(sub);
    } else if (!LEGACY_SEGMENTS.has(seg) && !LEGACY_EXCLUDED.has(seg)) {
      missing.add(seg);
    }
  }
  assert.deepEqual([...missing], [], "add these to LEGACY_SEGMENTS (or LEGACY_EXCLUDED)");
  assert.deepEqual([...missingApi], [], "add these to LEGACY_API_SEGMENTS");
});

test("no listed segment shadows a blt-next or blt-home path", () => {
  for (const seg of ["pages", "assets", "_home", "api", "index.html", "favicon.ico", ""]) {
    assert.ok(!LEGACY_SEGMENTS.has(seg), seg);
  }
  for (const sub of ["stats", "auth", "bugs", "leaderboard", "projects", "home-stats"]) {
    assert.ok(!LEGACY_API_SEGMENTS.has(sub), "api/" + sub);
  }
});
