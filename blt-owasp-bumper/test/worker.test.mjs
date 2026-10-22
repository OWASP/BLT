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
  ASSETS: staticAssets({ "/data/repos.json": '{"total":1}', "/index.html": "<p>page</p>" }),
});
const get = (path) => new Request(`https://bumper.test${path}`);

test("data/repos.json comes from KV, falling back to the committed file; the page is static", async () => {
  const e = env();
  let res = await worker.fetch(get("/data/repos.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.equal(await res.text(), '{"total":1}');
  await e.DATA.put("data/repos.json", '{"total":2}', { metadata: { updatedAt: "2026-10-22T00:10:00Z" } });
  res = await worker.fetch(get("/data/repos.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "kv");
  assert.equal(res.headers.get("content-type"), "application/json; charset=utf-8");
  assert.equal(await res.text(), '{"total":2}');
  assert.equal(await (await worker.fetch(get("/index.html"), e, {})).text(), "<p>page</p>");
});

test("wrangler.toml runs the Worker first for the page", () => {
  const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
  assert.match(toml, /^run_worker_first = \["\/data\/repos\.json"\]$/m);
  assert.match(toml, /binding = "DATA"\nid = "[0-9a-f]{32}"/);
});

test("refresh-kv.sh writes the data only when it lists enough repositories", () => {
  const dir = mkdtempSync(join(tmpdir(), "bumper-kv-"));
  try {
    const pub = join(dir, "pub");
    mkdirSync(pub);
    mkdirSync(join(pub, "data"));
    writeFileSync(join(pub, "data", "repos.json"), '{"total":1000}');
    const fakepy = join(dir, "fakepy");
    writeFileSync(fakepy, `#!/bin/bash\necho "{\\"total\\":$N}" > "$OUTPUT_FILE"\n`);
    chmodSync(fakepy, 0o755);
    const opts = (n) => ({
      cwd: new URL("..", import.meta.url).pathname,
      encoding: "utf8",
      env: {
        ...process.env, N: n, PYTHON: fakepy, PUBLIC_DIR: pub,
        KV_PUT_DRY_RUN: "1", KV_NAMESPACE_ID: "0123456789abcdef0123456789abcdef",
      },
    });
    const bad = spawnSync("bash", ["scripts/refresh-kv.sh"], opts("12"));
    assert.equal(bad.status, 1);
    assert.match(bad.stderr, /not writing data\/repos\.json: 12 repositories \(was 1000\)/);
    writeFileSync(join(pub, "data", "repos.json"), '{"total":1000}');
    assert.match(execFileSync("bash", ["scripts/refresh-kv.sh"], opts("990")), /would write data\/repos\.json/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
