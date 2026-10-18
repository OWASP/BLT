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
  ASSETS: staticAssets({ "/data/ossh_catalog.json": "{\"static\":true}", "/data/profiles.json": "[]" }),
});
const get = (path) => new Request(`https://ossh.test${path}`);

test("the catalog comes from KV, falling back to the committed file", async () => {
  const e = env();
  let res = await worker.fetch(get("/data/ossh_catalog.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.deepEqual(await res.json(), { static: true });
  await e.DATA.put("data/ossh_catalog.json", "{\"repos\":[]}", { metadata: { updatedAt: "2026-10-18T06:05:00Z" } });
  res = await worker.fetch(get("/data/ossh_catalog.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "kv");
  assert.deepEqual(await res.json(), { repos: [] });
  // profiles.json is not KV data.
  await worker.fetch(get("/data/profiles.json"), e, {});
  assert.deepEqual(e.DATA.puts, ["data/ossh_catalog.json"]);
});

test("the committed catalog has no gitlab.com/owasp-blt repos", () => {
  const catalog = JSON.parse(readFileSync(new URL("../public/data/ossh_catalog.json", import.meta.url), "utf8"));
  assert.ok(catalog.repos.length > 0);
  assert.equal(catalog.repos.filter((r) => String(r.url).startsWith("https://gitlab.com/owasp-blt/")).length, 0);
});

test("refresh-kv.sh seeds the KV catalog, drops gitlab.com/owasp-blt and writes changes only", () => {
  const dir = mkdtempSync(join(tmpdir(), "ossh-kv-"));
  try {
    const bin = join(dir, "bin");
    const pub = join(dir, "pub");
    mkdirSync(bin);
    mkdirSync(join(pub, "data"), { recursive: true });
    writeFileSync(join(pub, "data", "ossh_catalog.json"), '{"repos":[{"url":"https://github.com/committed/x"}]}');
    const live = JSON.stringify({
      repos: [{ url: "https://github.com/a/b" }, { url: "https://gitlab.com/owasp-blt/www-project-bug-logging-tool" }],
      articles: [],
    });
    writeFileSync(join(dir, "live.json"), live);
    // python: each fetcher records its name; fetch_articles.py may add articles.
    writeFileSync(join(bin, "fakepy"), `#!/bin/bash
echo "$1" >> "${dir}/ran"
if [[ "$1" == scripts/fetch_articles.py && -n "\${ARTICLE:-}" ]]; then
  jq --arg t "$ARTICLE" '.articles = [{title: $t}]' "$OSSH_CATALOG_PATH" > "$OSSH_CATALOG_PATH.tmp" && mv "$OSSH_CATALOG_PATH.tmp" "$OSSH_CATALOG_PATH"
fi
`);
    chmodSync(join(bin, "fakepy"), 0o755);
    const run = (extra = {}) => execFileSync("bash", ["scripts/refresh-kv.sh"], {
      cwd: new URL("..", import.meta.url).pathname,
      encoding: "utf8",
      env: {
        ...process.env, ...extra, DISCORD_BOT_TOKEN: extra.DISCORD_BOT_TOKEN || "",
        KV_GET_FROM: extra.KV_GET_FROM || join(dir, "live.json"),
        PYTHON: join(bin, "fakepy"),
        PUBLIC_DIR: pub,
        KV_PUT_DRY_RUN: "1",
        KV_NAMESPACE_ID: "0123456789abcdef0123456789abcdef",
      },
    });
    let out = run();
    assert.match(out, /seeded data\/ossh_catalog\.json from KV/);
    assert.match(out, /would write data\/ossh_catalog\.json/); // the gitlab entry was dropped
    const written = JSON.parse(readFileSync(join(pub, "data", "ossh_catalog.json"), "utf8"));
    assert.deepEqual(written.repos, [{ url: "https://github.com/a/b" }]);
    assert.deepEqual(readFileSync(join(dir, "ran"), "utf8").trim().split("\n"), ["scripts/fetch_articles.py", "scripts/fetch_reddit.py"]);

    // No KV copy yet: the checked-out file is the base. A KV copy that is not a catalog stops the run.
    out = run({ KV_GET_FROM: join(dir, "missing.json") });
    assert.match(out, /no catalog in KV yet/);
    writeFileSync(join(dir, "broken.json"), "{}");
    assert.throws(() => run({ KV_GET_FROM: join(dir, "broken.json") }), /could not read a valid catalog from KV/);

    // KV copy already clean and nothing fetched: nothing written.
    writeFileSync(join(dir, "live.json"), JSON.stringify(written));
    out = run({ DISCORD_BOT_TOKEN: "t" });
    assert.match(out, /catalog unchanged/);
    assert.match(readFileSync(join(dir, "ran"), "utf8"), /fetch_discord\.py/);
    out = run({ ARTICLE: "new" });
    assert.match(out, /would write data\/ossh_catalog\.json/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
