import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import worker from "../worker/index.js";
import { MemoryKV, staticAssets } from "../../scripts/worker-data/testing.mjs";

const env = () => ({
  DATA: new MemoryKV(),
  ASSETS: staticAssets({ "/": "<p>static</p>", "/project_repos_links.json": "[\"static\"]" }),
});
const get = (path) => new Request(`https://tomato.test${path}`);

test("the page and its JSON come from KV, falling back to the committed files", async () => {
  const e = env();
  let res = await worker.fetch(get("/"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.equal(await res.text(), "<p>static</p>");
  await e.DATA.put("index.html", "<p>fresh</p>", { metadata: { updatedAt: "2026-10-23T18:20:00Z" } });
  await e.DATA.put("project_repos_links.json", "[1]");
  for (const path of ["/", "/index.html"]) {
    res = await worker.fetch(get(path), e, {});
    assert.equal(res.headers.get("x-data-source"), "kv");
    assert.equal(await res.text(), "<p>fresh</p>");
  }
  res = await worker.fetch(get("/project_repos_links.json"), e, {});
  assert.deepEqual(await res.json(), [1]);
});

test("wrangler.toml runs the Worker first for the page and its JSON", () => {
  const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
  assert.match(toml, /^run_worker_first = \["\/", "\/index\.html", "\/project_repos_links\.json"\]$/m);
  assert.match(toml, /binding = "DATA"\nid = "[0-9a-f]{32}"/);
});

test("refresh-kv.sh writes both files only when the list is not much shorter", () => {
  const dir = mkdtempSync(join(tmpdir(), "tomato-kv-"));
  try {
    const pub = join(dir, "pub");
    mkdirSync(pub);
    writeFileSync(join(pub, "project_repos_links.json"), "[1,2,3,4]");
    const fakepy = join(dir, "fakepy");
    writeFileSync(fakepy, `#!/bin/bash
jq -n --argjson n "$N" '[range($n)]' > "$OUTPUT_DIR/project_repos_links.json"
echo "<html>" > "$OUTPUT_DIR/index.html"
`);
    chmodSync(fakepy, 0o755);
    const opts = (n) => ({
      cwd: new URL("..", import.meta.url).pathname,
      encoding: "utf8",
      env: {
        ...process.env, N: n, PYTHON: fakepy, PUBLIC_DIR: pub,
        KV_PUT_DRY_RUN: "1", KV_NAMESPACE_ID: "0123456789abcdef0123456789abcdef",
      },
    });
    const bad = spawnSync("bash", ["scripts/refresh-kv.sh"], opts("1"));
    assert.equal(bad.status, 1);
    assert.match(bad.stderr, /not writing the funding list: 1 projects \(was 4\)/);
    const out = execFileSync("bash", ["scripts/refresh-kv.sh"], opts("3"));
    assert.match(out, /would write project_repos_links\.json/);
    assert.match(out, /would write index\.html/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
