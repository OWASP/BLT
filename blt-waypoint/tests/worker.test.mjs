import assert from "node:assert/strict";
import test from "node:test";
import worker from "../worker/index.js";
import { MemoryKV, staticAssets } from "../../scripts/worker-data/testing.mjs";

const env = () => ({
  DATA: new MemoryKV(),
  ASSETS: staticAssets({ "/forge_data.json": "{\"static\":true}", "/index.html": "<html>" }),
});
const get = (path) => new Request(`https://waypoint.test${path}`);

test("forge_data.json comes from KV, falling back to the committed file", async () => {
  const e = env();
  let res = await worker.fetch(get("/forge_data.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.deepEqual(await res.json(), { static: true });
  await e.DATA.put("forge_data.json", "{\"fresh\":1}", { metadata: { updatedAt: "2026-10-18T06:29:00Z" } });
  res = await worker.fetch(get("/forge_data.json"), e, {});
  assert.equal(res.headers.get("x-data-source"), "kv");
  assert.equal(res.headers.get("x-data-updated-at"), "2026-10-18T06:29:00Z");
  assert.deepEqual(await res.json(), { fresh: 1 });
});

test("the old /gitlab_data.json URL serves the forge data", async () => {
  const e = env();
  let res = await worker.fetch(get("/gitlab_data.json"), e, {});
  assert.deepEqual(await res.json(), { static: true });
  await e.DATA.put("forge_data.json", "{\"fresh\":2}");
  res = await worker.fetch(get("/gitlab_data.json?t=1"), e, {});
  assert.equal(res.headers.get("x-data-source"), "kv");
  assert.deepEqual(await res.json(), { fresh: 2 });
});

test("other paths are plain static assets", async () => {
  const e = env();
  assert.equal(await (await worker.fetch(get("/index.html"), e, {})).text(), "<html>");
  assert.equal((await worker.fetch(get("/github_data.json"), e, {})).status, 404);
});

test("screenshots come from KV as JPEG, and 404 before the first capture", async () => {
  const e = env();
  assert.equal((await worker.fetch(get("/screenshots/blt-api.jpg"), e, {})).status, 404);
  await e.DATA.put("screenshots/blt-api.jpg", "\xff\xd8jpeg");
  const res = await worker.fetch(get("/screenshots/blt-api.jpg"), e, {});
  assert.equal(res.headers.get("content-type"), "image/jpeg");
  assert.equal(res.headers.get("x-data-source"), "kv");
  await e.DATA.put("screenshots/index.json", "{\"shots\":{}}");
  assert.deepEqual(await (await worker.fetch(get("/screenshots/index.json"), e, {})).json(), { shots: {} });
  assert.equal((await worker.fetch(get("/screenshots/..%2Fforge_data.json"), e, {})).status, 404);
});
