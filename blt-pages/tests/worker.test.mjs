import assert from "node:assert/strict";
import test from "node:test";
import worker from "../worker/index.js";
import { MemoryKV, staticAssets } from "../../scripts/worker-data/testing.mjs";

const env = () => ({
  DATA: new MemoryKV(),
  ASSETS: staticAssets({
    "/": "<p>committed home</p>",
    "/leaderboard": "<p>committed board</p>",
    "/data/leaderboard.json": "{\"static\":true}",
    "/js/app.js": "app",
  }),
});
const get = (path) => new Request(`https://pages.test${path}`);

test("pages and data come from KV, falling back to the committed files", async () => {
  const e = env();
  assert.equal(await (await worker.fetch(get("/"), e, {})).text(), "<p>committed home</p>");
  assert.equal(await (await worker.fetch(get("/leaderboard"), e, {})).text(), "<p>committed board</p>");
  await e.DATA.put("index.html", "<p>fresh home</p>", { metadata: { updatedAt: "2026-10-18T05:11:00Z" } });
  await e.DATA.put("leaderboard.html", "<p>fresh board</p>");
  await e.DATA.put("data/leaderboard.json", "{\"fresh\":true}");
  const home = await worker.fetch(get("/"), e, {});
  assert.equal(home.headers.get("content-type"), "text/html; charset=utf-8");
  assert.equal(home.headers.get("x-data-updated-at"), "2026-10-18T05:11:00Z");
  assert.equal(await home.text(), "<p>fresh home</p>");
  assert.equal(await (await worker.fetch(get("/leaderboard"), e, {})).text(), "<p>fresh board</p>");
  assert.equal(await (await worker.fetch(get("/leaderboard.html"), e, {})).text(), "<p>fresh board</p>");
  assert.deepEqual(await (await worker.fetch(get("/data/leaderboard.json"), e, {})).json(), { fresh: true });
});

test("everything else is a static asset", async () => {
  const e = env();
  assert.equal(await (await worker.fetch(get("/js/app.js"), e, {})).text(), "app");
  assert.deepEqual(e.DATA.puts, []);
});
