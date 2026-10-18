import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import worker, { DATA_PATHS } from "../worker/index.js";
import { MemoryKV, staticAssets } from "../../scripts/worker-data/testing.mjs";

const env = () => ({
  DATA: new MemoryKV(),
  ASSETS: staticAssets({ "/repo_status.json": "[\"static\"]", "/index.html": "<html>" }),
});
const get = (path) => new Request(`https://projects.test${path}`);

test("data files come from KV, falling back to the committed files", async () => {
  const e = env();
  let res = await worker.fetch(get("/repo_status.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.deepEqual(await res.json(), ["static"]);
  await e.DATA.put("repo_status.json", "[1]", { metadata: { updatedAt: "2026-10-18T04:30:00Z" } });
  res = await worker.fetch(get("/repo_status.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "kv");
  assert.equal(res.headers.get("x-data-updated-at"), "2026-10-18T04:30:00Z");
  assert.equal(res.headers.get("content-type"), "application/json; charset=utf-8");
  assert.deepEqual(await res.json(), [1]);
});

test("pages are plain static assets", async () => {
  const e = env();
  assert.equal(await (await worker.fetch(get("/index.html"), e, {})).text(), "<html>");
  assert.equal((await worker.fetch(get("/other.json"), e, {})).headers.get("x-data-source"), null);
});

test("wrangler.toml runs the Worker first for exactly the data paths", () => {
  const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
  const listed = [...toml.match(/run_worker_first = \[([^\]]*)\]/)[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(listed, DATA_PATHS);
  assert.match(toml, /^main = "worker\/index\.js"$/m);
  assert.match(toml, /binding = "DATA"\nid = "REPLACE_WITH_KV_ID_blt-owasp-projects-data"/);
});

test("refresh-kv.sh seeds live data and writes only good, changed files", () => {
  const dir = mkdtempSync(join(tmpdir(), "owasp-projects-kv-"));
  try {
    const bin = join(dir, "bin");
    const pub = join(dir, "pub");
    mkdirSync(bin);
    mkdirSync(pub);
    writeFileSync(join(pub, "issues.json"), "[1,2,3,4]");
    writeFileSync(join(bin, "curl"), `#!/bin/bash
out=""; url=""
while [[ $# -gt 0 ]]; do case "$1" in -o) out="$2"; shift 2 ;; http*) url="$1"; shift ;; *) shift ;; esac; done
case "$url" in
  */www_project_repos.json) echo '[{"id":1}]' > "$out" ;;
  */known_issue_ids.json) echo '[7]' > "$out" ;;
  *) exit 22 ;;
esac
`);
    // python: stands in for the four generators.
    writeFileSync(join(bin, "fakepy"), `#!/bin/bash
case "$1" in
  scripts/main.py) cp "$OUTPUT_DIR/www_project_repos.json" "${dir}/seen-repos"; echo '[{"id":1}]' > "$OUTPUT_DIR/www_project_repos.json" ;;
  scripts/fetch_repo_status.py) echo "[{\\"github_status\\":\\"\${STATUS:-success}\\"}]" > "$OUTPUT_DIR/repo_status.json" ;;
  scripts/fetch_issues.py) echo '[9]' > "$OUTPUT_DIR/issues.json"; echo '[7,9]' > "$OUTPUT_DIR/known_issue_ids.json" ;;
  scripts/scrape_github_links.py) exit 1 ;;
esac
`);
    chmodSync(join(bin, "curl"), 0o755);
    chmodSync(join(bin, "fakepy"), 0o755);
    const run = (extra = {}) => execFileSync("bash", ["scripts/refresh-kv.sh"], {
      cwd: new URL("..", import.meta.url).pathname,
      encoding: "utf8",
      env: {
        ...process.env, ...extra,
        PATH: `${bin}:${process.env.PATH}`,
        PYTHON: join(bin, "fakepy"),
        PUBLIC_DIR: pub,
        KV_PUT_DRY_RUN: "1",
        KV_NAMESPACE_ID: "0123456789abcdef0123456789abcdef",
      },
    });
    let out = run();
    assert.equal(readFileSync(join(dir, "seen-repos"), "utf8").trim(), '[{"id":1}]');
    assert.match(out, /www_project_repos\.json unchanged/);
    assert.match(out, /would write repo_status\.json/);
    assert.match(out, /would write known_issue_ids\.json/);
    // 1 issue where there were 4: a failed fetch, not written.
    assert.match(out, /skipping issues\.json/);
    assert.doesNotMatch(out, /would write issues\.json/);
    assert.match(out, /scrape_github_links\.py failed/);
    assert.doesNotMatch(out, /would write project_repos_links\.json/);
    out = run({ STATUS: "Bad credentials" });
    assert.match(out, /skipping repo_status\.json: no repository was read successfully/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
