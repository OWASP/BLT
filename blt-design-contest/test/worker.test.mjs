import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import worker, { PAGES } from "../worker/index.js";
import { MemoryKV, staticAssets } from "../../scripts/worker-data/testing.mjs";

const env = () => ({
  DATA: new MemoryKV(),
  ASSETS: staticAssets({ "/": "<static index>", "/blt-logo.html": "<static logo>", "/assets/x.png": "png" }),
});
const get = (path) => new Request(`https://contest.test${path}`);

test("pages come from KV, falling back to the committed files", async () => {
  const e = env();
  let res = await worker.fetch(get("/blt-logo.html"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.equal(await res.text(), "<static logo>");
  await e.DATA.put("blt-logo.html", "<kv logo>", { metadata: { updatedAt: "2026-10-18T10:00:00Z" } });
  for (const path of ["/blt-logo.html", "/blt-logo"]) {
    res = await worker.fetch(get(path), e, {});
    assert.equal(res.headers.get("x-data-source"), "kv");
    assert.equal(res.headers.get("content-type"), "text/html; charset=utf-8");
    assert.equal(await res.text(), "<kv logo>");
  }
  res = await worker.fetch(get("/"), e, {});
  assert.equal(await res.text(), "<static index>");
  await e.DATA.put("index.html", "<kv index>");
  assert.equal(await (await worker.fetch(get("/"), e, {})).text(), "<kv index>");
});

test("other paths are plain static assets", async () => {
  const e = env();
  assert.equal(await (await worker.fetch(get("/assets/x.png"), e, {})).text(), "png");
  await e.DATA.put("other.html", "<kv>");
  assert.equal((await worker.fetch(get("/other.html"), e, {})).status, 404);
});

test("the page list matches the generator's contests and wrangler.toml", () => {
  const generator = readFileSync(new URL("../scripts/build_showcase.py", import.meta.url), "utf8");
  const contests = [...generator.matchAll(/^\s+"id": "([a-z0-9-]+)",$/gm)].map((m) => m[1]);
  assert.deepEqual(PAGES, ["index", "show-all-entries", ...contests]);
  const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
  const first = toml.match(/run_worker_first = \[([^\]]*)\]/)[1];
  const listed = [...first.matchAll(/"([^"]+)"/g)].map((m) => m[1]).sort();
  const expected = ["/", ...PAGES.flatMap((p) => [`/${p}`, `/${p}.html`])].sort();
  assert.deepEqual(listed, expected);
});
