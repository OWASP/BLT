import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import worker, { DATA_FILES } from "../worker/index.js";
import { MemoryKV, staticAssets } from "../../scripts/worker-data/testing.mjs";

const env = () => ({
  DATA: new MemoryKV(),
  ASSETS: staticAssets({
    "/data/metadata.json": "[\"static\"]",
    "/data/metadata_checklist.csv": "a,b",
    "/index.html": "<html>",
  }),
});
const get = (path) => new Request(`https://metadata.test${path}`);

test("the dataset comes from KV, falling back to the committed files", async () => {
  const e = env();
  let res = await worker.fetch(get("/data/metadata.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.deepEqual(await res.json(), ["static"]);
  await e.DATA.put("data/metadata.json", "[1]", { metadata: { updatedAt: "2026-10-19T03:20:00Z" } });
  await e.DATA.put("data/metadata.csv", "repo\nx\n");
  await e.DATA.put("data/metadata_summary.md", "# Metadata Summary\n");
  res = await worker.fetch(get("/data/metadata.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "kv");
  assert.equal(res.headers.get("x-data-updated-at"), "2026-10-19T03:20:00Z");
  assert.deepEqual(await res.json(), [1]);
  res = await worker.fetch(get("/data/metadata.csv"), e, {});
  assert.equal(res.headers.get("content-type"), "text/csv; charset=utf-8");
  res = await worker.fetch(get("/data/metadata_summary.md"), e, {});
  assert.equal(res.headers.get("content-type"), "text/markdown; charset=utf-8");
});

test("other files are plain static assets", async () => {
  const e = env();
  assert.equal(await (await worker.fetch(get("/data/metadata_checklist.csv"), e, {})).text(), "a,b");
  assert.equal(await (await worker.fetch(get("/index.html"), e, {})).text(), "<html>");
});

test("wrangler.toml runs the Worker first for exactly the data files", () => {
  const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
  const listed = [...toml.match(/run_worker_first = \[([^\]]*)\]/)[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(listed, Object.keys(DATA_FILES));
  assert.match(toml, /binding = "DATA"\nid = "REPLACE_WITH_KV_ID_blt-owasp-metadata-data"/);
});

test("refresh-kv.sh writes the dataset only when it is not much smaller", () => {
  const dir = mkdtempSync(join(tmpdir(), "metadata-kv-"));
  try {
    const data = join(dir, "pub", "data");
    mkdirSync(data, { recursive: true });
    const fakepy = join(dir, "fakepy");
    writeFileSync(fakepy, `#!/bin/bash
cd "$METADATA_DATA_DIR"
jq -n --argjson n "$N" '[range($n)]' | tee metadata.json > metadata_matrix.json
touch metadata.csv metadata_matrix.csv metadata_summary.md
`);
    chmodSync(fakepy, 0o755);
    const opts = (n) => ({
      cwd: new URL("..", import.meta.url).pathname,
      encoding: "utf8",
      env: {
        ...process.env, N: n, PYTHON: fakepy, PUBLIC_DIR: join(dir, "pub"),
        KV_PUT_DRY_RUN: "1", KV_NAMESPACE_ID: "0123456789abcdef0123456789abcdef",
      },
    });
    const out = execFileSync("bash", ["scripts/refresh-kv.sh"], opts("10"));
    for (const f of Object.keys(DATA_FILES)) assert.match(out, new RegExp(`would write ${f.slice(1).replace(".", "\\.")}`));
    const bad = spawnSync("bash", ["scripts/refresh-kv.sh"], opts("0"));
    assert.equal(bad.status, 1);
    assert.match(bad.stderr, /not writing the dataset: metadata\.json lists 0 repositories \(was 10\)/);
    writeFileSync(join(data, "metadata.json"), "[1,2,3,4,5,6,7,8,9,10]");
    assert.equal(spawnSync("bash", ["scripts/refresh-kv.sh"], opts("4")).status, 1);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
