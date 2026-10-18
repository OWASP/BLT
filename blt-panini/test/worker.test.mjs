import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import worker from "../worker/index.js";
import { MemoryKV, staticAssets } from "../../scripts/worker-data/testing.mjs";

const env = () => ({
  DATA: new MemoryKV(),
  ASSETS: staticAssets({ "/slack_apps.json": "[\"static\"]", "/banned_apps.json": "{\"banned\":1}" }),
});
const get = (path) => new Request(`https://panini.test${path}`);

test("slack_apps.json comes from KV, falling back to the committed file", async () => {
  const e = env();
  let res = await worker.fetch(get("/slack_apps.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.deepEqual(await res.json(), ["static"]);
  await e.DATA.put("slack_apps.json", "[1]", { metadata: { updatedAt: "2026-10-18T00:30:00Z" } });
  res = await worker.fetch(get("/slack_apps.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "kv");
  assert.deepEqual(await res.json(), [1]);
  assert.deepEqual(await (await worker.fetch(get("/banned_apps.json"), e, {})).json(), { banned: 1 });
});

test("wrangler.toml runs the Worker first for slack_apps.json only", () => {
  const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
  assert.match(toml, /^run_worker_first = \["\/slack_apps\.json"\]$/m);
  assert.match(toml, /binding = "DATA"\nid = "[0-9a-f]{32}"/);
});

test("refresh-kv.sh keeps apps from KV, lets git curation win and writes changes only", () => {
  const dir = mkdtempSync(join(tmpdir(), "panini-kv-"));
  try {
    const pub = join(dir, "pub");
    mkdirSync(pub);
    const committed = JSON.stringify([{ app_name: "Zoom", security_rating: "A" }]);
    writeFileSync(join(dir, "kv.json"), JSON.stringify([
      { app_name: "zoom", security_rating: "" },
      { app_name: "Found Earlier", security_rating: "" },
    ]));
    const fakepy = join(dir, "fakepy");
    // Stands in for update_slack_apps.py: records the base, may add an app.
    writeFileSync(fakepy, `#!/bin/bash
cp "$SLACK_APPS_PATH" "${dir}/base.json"
[[ -n "\${NEW_APP:-}" ]] && jq --arg n "$NEW_APP" '. + [{app_name: $n}]' "$SLACK_APPS_PATH" > "${dir}/t" && mv "${dir}/t" "$SLACK_APPS_PATH"
[[ -n "\${FAIL:-}" ]] && exit 1
exit 0
`);
    chmodSync(fakepy, 0o755);
    const run = (extra = {}) => {
      writeFileSync(join(pub, "slack_apps.json"), committed);
      return execFileSync("bash", ["scripts/refresh-kv.sh"], {
        cwd: new URL("..", import.meta.url).pathname,
        encoding: "utf8",
        env: {
          ...process.env, ...extra,
          PYTHON: fakepy,
          PUBLIC_DIR: pub,
          KV_GET_FROM: extra.KV_GET_FROM || join(dir, "kv.json"),
          KV_PUT_DRY_RUN: "1",
          KV_NAMESPACE_ID: "0123456789abcdef0123456789abcdef",
        },
      });
    };
    let out = run({ FAIL: "1" });
    assert.deepEqual(JSON.parse(readFileSync(join(dir, "base.json"), "utf8")), [
      { app_name: "Zoom", security_rating: "A" },
      { app_name: "Found Earlier", security_rating: "" },
    ]);
    assert.match(out, /update_slack_apps\.py failed/);
    assert.match(out, /would write slack_apps\.json/); // the git curation changed the KV copy
    writeFileSync(join(dir, "kv.json"), readFileSync(join(dir, "base.json")));
    out = run();
    assert.match(out, /slack_apps\.json unchanged/);
    out = run({ NEW_APP: "Brand New" });
    assert.match(out, /would write slack_apps\.json/);
    out = run({ KV_GET_FROM: join(dir, "missing.json") });
    assert.match(out, /no slack_apps\.json in KV yet/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
