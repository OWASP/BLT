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
  ASSETS: staticAssets({ "/": "<p>static</p>", "/index.html": "<p>static</p>", "/logo.png": "png" }),
});
const get = (path) => new Request(`https://bumper.test${path}`);

test("/ and /index.html come from KV, falling back to the committed page", async () => {
  const e = env();
  let res = await worker.fetch(get("/"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.equal(await res.text(), "<p>static</p>");
  await e.DATA.put("index.html", "<p>fresh</p>", { metadata: { updatedAt: "2026-10-18T00:10:00Z" } });
  for (const path of ["/", "/index.html"]) {
    res = await worker.fetch(get(path), e, {});
    assert.equal(res.headers.get("x-data-source"), "kv");
    assert.equal(res.headers.get("content-type"), "text/html; charset=utf-8");
    assert.equal(await res.text(), "<p>fresh</p>");
  }
  assert.equal(await (await worker.fetch(get("/logo.png"), e, {})).text(), "png");
});

test("wrangler.toml runs the Worker first for the page", () => {
  const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
  assert.match(toml, /^run_worker_first = \["\/", "\/index\.html"\]$/m);
  assert.match(toml, /binding = "DATA"\nid = "REPLACE_WITH_KV_ID_blt-owasp-bumper-data"/);
});

test("refresh-kv.sh writes the page only when it lists enough repositories", () => {
  const dir = mkdtempSync(join(tmpdir(), "bumper-kv-"));
  try {
    const pub = join(dir, "pub");
    mkdirSync(pub);
    writeFileSync(join(pub, "index.html"), "Total: 1000 repositories");
    const fakepy = join(dir, "fakepy");
    writeFileSync(fakepy, `#!/bin/bash\necho "Total: $N repositories" > "$OUTPUT_FILE"\n`);
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
    assert.match(bad.stderr, /not writing index\.html: 12 repositories \(was 1000\)/);
    writeFileSync(join(pub, "index.html"), "Total: 1000 repositories");
    assert.match(execFileSync("bash", ["scripts/refresh-kv.sh"], opts("990")), /would write index\.html/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
