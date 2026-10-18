import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { chmodSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import worker from "../worker/index.js";
import { MemoryKV, staticAssets } from "../../scripts/worker-data/testing.mjs";

const committed = readFileSync(new URL("../public/hackathon-data/gsoc-2027-warmup-summary.json", import.meta.url), "utf8");
const env = () => ({
  DATA: new MemoryKV(),
  ASSETS: staticAssets({
    "/hackathon-data/gsoc-2027-warmup-summary.json": committed,
    "/stats.json": "{\"static\":true}",
    "/index.html": "<html>",
  }),
});
const get = (path) => new Request(`https://hackathons.test${path}`);

test("data paths come from KV, falling back to the committed files", async () => {
  const e = env();
  let res = await worker.fetch(get("/hackathon-data/gsoc-2027-warmup-summary.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.equal(await res.text(), committed);
  await e.DATA.put("hackathon-data/gsoc-2027-warmup-summary.json", "{\"fresh\":1}", { metadata: { updatedAt: "2026-10-18T10:00:00Z" } });
  res = await worker.fetch(get("/hackathon-data/gsoc-2027-warmup-summary.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "kv");
  assert.equal(res.headers.get("x-data-updated-at"), "2026-10-18T10:00:00Z");
  assert.equal(res.headers.get("cache-control"), "public, max-age=60, stale-while-revalidate=600");
  assert.deepEqual(await res.json(), { fresh: 1 });
  res = await worker.fetch(get("/stats.json"), e, {});
  assert.deepEqual(await res.json(), { static: true });
});

test("other paths are plain static assets", async () => {
  const e = env();
  assert.equal(await (await worker.fetch(get("/index.html"), e, {})).text(), "<html>");
  // Not a data path: no KV lookup.
  await worker.fetch(get("/hackathon-data/../index.html"), e, {});
  await worker.fetch(get("/hackathon-data/x.txt"), e, {});
  assert.deepEqual(e.DATA.puts, []);
});

test("refresh-kv.sh seeds live data, runs the fetch and writes only changed files", () => {
  const dir = mkdtempSync(join(tmpdir(), "hackathons-kv-"));
  try {
    const bin = join(dir, "bin");
    execFileSync("mkdir", ["-p", bin, join(dir, "pub")]);
    // curl: the live site has the summary and stats.json, not the full file.
    writeFileSync(join(bin, "curl"), `#!/bin/bash
out=""; url=""
while [[ $# -gt 0 ]]; do case "$1" in -o) out="$2"; shift 2 ;; http*) url="$1"; shift ;; *) shift ;; esac; done
echo "$url" >> "${dir}/curl.log"
case "$url" in
  */gsoc-2027-warmup-summary.json) echo '{"seeded":true}' > "$out" ;;
  */stats.json) echo '{"lastUpdated":"old","hackathons":[1]}' > "$out" ;;
  *) exit 22 ;;
esac
`);
    // python: stands in for fetch_stats.py and records what it saw.
    writeFileSync(join(bin, "fakepy"), `#!/bin/bash
cat "$PUBLIC_DIR/hackathon-data/gsoc-2027-warmup-summary.json" > "${dir}/seen-summary"
echo '{"lastUpdated":"new","stats":{}}' > "$PUBLIC_DIR/hackathon-data/gsoc-2027-warmup.json"
echo "{\\"lastUpdated\\":\\"new\\",\\"hackathons\\":[\${STATS_N:-1}]}" > "$PUBLIC_DIR/stats.json"
echo "$FETCH_STATE_PATH $FETCH_BUDGET_SECONDS" > "${dir}/seen-state-path"
[[ -f "$FETCH_STATE_PATH" ]] && cp "$FETCH_STATE_PATH" "${dir}/seen-state"
[[ -n "\${STATE_OUT:-}" ]] && echo "$STATE_OUT" > "$FETCH_STATE_PATH"
exit 0
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
        PUBLIC_DIR: join(dir, "pub"),
        NOW: "2026-11-15T00:00:00Z",
        KV_PUT_DRY_RUN: "1",
        KV_NAMESPACE_ID: "0123456789abcdef0123456789abcdef",
      },
    });
    let out = run();
    assert.match(out, /would write hackathon-data\/gsoc-2027-warmup\.json/);
    assert.doesNotMatch(out, /would write stats\.json/); // only lastUpdated changed
    assert.equal(readFileSync(join(dir, "seen-summary"), "utf8").trim(), '{"seeded":true}');
    const log = readFileSync(join(dir, "curl.log"), "utf8");
    assert.match(log, /hackathon-data\/gsoc-2027-warmup\.json/);
    assert.doesNotMatch(log, /may-2025-hackathon/); // ended hackathons are not seeded
    out = run({ STATS_N: "2" });
    assert.match(out, /would write stats\.json/);
    assert.doesNotMatch(out, /state\/fetch-state\.json/); // no state, none written
    assert.match(out, /no refresh state in KV/);
    assert.match(readFileSync(join(dir, "seen-state-path"), "utf8"), /state\/fetch-state\.json 900/);

    // The refresh state is read from KV and written back only when the fetch changed it.
    writeFileSync(join(dir, "state.json"), '{"cursor":1}\n');
    out = run({ KV_GET_FROM: join(dir, "state.json"), STATE_OUT: '{"cursor":1}' });
    assert.match(out, /loaded refresh state from KV/);
    assert.equal(readFileSync(join(dir, "seen-state"), "utf8"), '{"cursor":1}\n');
    assert.doesNotMatch(out, /would write state\/fetch-state\.json/);
    out = run({ KV_GET_FROM: join(dir, "state.json"), STATE_OUT: '{"cursor":2}' });
    assert.match(out, /would write state\/fetch-state\.json/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
