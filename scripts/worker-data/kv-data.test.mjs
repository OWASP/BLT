import assert from "node:assert/strict";
import test from "node:test";
import {
  CACHE_CONTROL, contentTypeFor, cronAuthorized, handleCronDispatch, kvSiteWorker, putData, readJsonOrAsset, runChunked,
  serveData,
} from "./kv-data.js";
import { MemoryKV, cronRequest, staticAssets } from "./testing.mjs";

const get = (path) => new Request(`https://site.test${path}`);

test("serveData streams the KV value with cache headers and updatedAt", async () => {
  const env = { DATA: new MemoryKV(), ASSETS: staticAssets({ "/data/x.json": "{\"old\":true}" }) };
  await putData(env, "data/x.json", { fresh: true }, { updatedAt: "2026-10-18T00:00:00Z" });
  const res = await serveData(get("/data/x.json"), env, {});
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("cache-control"), CACHE_CONTROL);
  assert.equal(res.headers.get("content-type"), "application/json; charset=utf-8");
  assert.equal(res.headers.get("x-data-source"), "kv");
  assert.equal(res.headers.get("x-data-updated-at"), "2026-10-18T00:00:00Z");
  assert.deepEqual(await res.json(), { fresh: true });
  assert.deepEqual(env.ASSETS.requests, []);
});

test("serveData falls back to the static file while KV is empty", async () => {
  const env = { DATA: new MemoryKV(), ASSETS: staticAssets({ "/data/x.json": "{\"old\":true}" }) };
  const res = await serveData(get("/data/x.json"), env, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.deepEqual(await res.json(), { old: true });
  const missing = await serveData(get("/data/none.json"), env, {});
  assert.equal(missing.status, 404);
  const post = await serveData(new Request("https://site.test/data/x.json", { method: "POST" }), env, {});
  assert.equal(post.status, 405);
});

test("contentTypeFor", () => {
  assert.equal(contentTypeFor("js/a.generated.js"), "text/javascript; charset=utf-8");
  assert.equal(contentTypeFor("a.bin"), "application/octet-stream");
});

test("readJsonOrAsset prefers KV", async () => {
  const env = { DATA: new MemoryKV(), ASSETS: staticAssets({ "/p.json": { a: 1 } }) };
  assert.deepEqual(await readJsonOrAsset(env, "p.json"), { a: 1 });
  await putData(env, "p.json", { a: 2 });
  assert.deepEqual(await readJsonOrAsset(env, "p.json"), { a: 2 });
});

test("cron dispatch checks the secret and runs the named task", async () => {
  const env = { CRON_SECRET: "s3cret" };
  const ran = [];
  const tasks = {
    a: async (_env, opts) => { ran.push(["a", opts.scheduledTime, opts.reset, opts.day]); return { done: true }; },
    b: async () => { throw new Error("boom"); },
  };
  assert.equal((await handleCronDispatch(cronRequest({ task: "a" }, "wrong"), env, tasks)).status, 403);
  assert.equal((await handleCronDispatch(cronRequest({ task: "a" }), {}, tasks)).status, 403);
  assert.equal((await handleCronDispatch(get("/__scheduled"), env, tasks)).status, 405);
  assert.equal((await handleCronDispatch(cronRequest({ task: "zzz" }), env, tasks)).status, 400);
  const ok = await handleCronDispatch(cronRequest({ task: "a", scheduledTime: 5, reset: true, day: "2026-01-02" }), env, tasks);
  assert.equal(ok.status, 200);
  assert.deepEqual(ran, [["a", 5, true, "2026-01-02"]]);
  const all = await handleCronDispatch(cronRequest({}), env, tasks);
  assert.equal(all.status, 500);
  const body = await all.json();
  assert.equal(body.results.b.error, "boom");
  assert.ok(cronAuthorized(cronRequest({}), env));
});

test("runChunked spreads items over calls within the budget and finishes once", async () => {
  const env = { DATA: new MemoryKV() };
  const items = [{ id: "a", n: 10 }, { id: "b", n: 10 }, { id: "c", n: 25 }, { id: "d", n: 5 }];
  const seen = [];
  let finished = null;
  const opts = (extra = {}) => ({
    name: "t", run: "2026-10-18", items, budget: 20, cost: (i) => i.n,
    process: async (item) => { seen.push(item.id); return item.n * 2; },
    finish: async (results) => { finished = results; },
    ...extra,
  });
  let r = await runChunked(env, opts());
  assert.deepEqual([r.processed, r.next, r.done], [2, 2, false]);
  r = await runChunked(env, opts());
  assert.deepEqual([r.processed, r.next, r.done], [1, 3, false]); // an item over budget still runs alone
  r = await runChunked(env, opts());
  assert.equal(r.done, true);
  assert.deepEqual(finished, { a: 20, b: 20, c: 50, d: 10 });
  r = await runChunked(env, opts());
  assert.equal(r.skipped, true);
  assert.deepEqual(seen, ["a", "b", "c", "d"]);
  r = await runChunked(env, opts({ run: "2026-10-19", budget: 100 }));
  assert.equal(r.done, true);
  r = await runChunked(env, opts({ run: "2026-10-19", budget: 100, reset: true }));
  assert.equal(r.done, true);
  assert.equal(seen.length, 12);
});

test("kvSiteWorker serves matching paths from KV and the rest from ASSETS", async () => {
  const worker = kvSiteWorker([/^\/data\/[\w.-]+\.json$/, "/index.html"], { aliases: { "/": "index.html" } });
  const env = {
    DATA: new MemoryKV(),
    ASSETS: staticAssets({ "/data/a.json": "{\"old\":1}", "/index.html": "<p>old</p>", "/app.js": "x" }),
  };
  await putData(env, "index.html", "<p>new</p>");
  const home = await worker.fetch(get("/"), env, {});
  assert.equal(home.headers.get("content-type"), "text/html; charset=utf-8");
  assert.equal(await home.text(), "<p>new</p>");
  const data = await worker.fetch(get("/data/a.json"), env, {});
  assert.equal(data.headers.get("x-data-source"), "static");
  assert.equal(await (await worker.fetch(get("/app.js"), env, {})).text(), "x");
  assert.equal((await worker.fetch(get("/data/../x.json"), env, {})).status, 404);
});
