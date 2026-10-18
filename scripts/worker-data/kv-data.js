// Shared helper for BLT Workers that keep refreshed data in Workers KV instead of git.
//
// Each Worker imports this file (wrangler bundles it at deploy time):
//   - serveData(): answer GET for a data path from KV, falling back to the deployed static file
//     (so the first deploy, before any refresh, still serves the last committed data);
//   - putData() / readJson(): store and read values, with `updatedAt` kept as KV metadata;
//   - handleCronDispatch(): the authenticated POST /__scheduled endpoint that blt-cron calls;
//   - runChunked(): spread one refresh over several invocations with a cursor in KV, so each
//     invocation stays under the free plan's 50 subrequests and 10 ms CPU.
//
// The KV binding is `DATA` unless a caller passes another one. Keys are the public path without
// the leading slash (for example `hackathon-data/gsoc-2027-warmup.json`); internal state keys
// start with `state:`.

export const CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=600";
export const DEFAULT_BUDGET = 30;

const CONTENT_TYPES = {
  json: "application/json; charset=utf-8",
  js: "text/javascript; charset=utf-8",
  txt: "text/plain; charset=utf-8",
};

export function contentTypeFor(key) {
  const ext = String(key).split(".").pop();
  return CONTENT_TYPES[ext] || "application/octet-stream";
}

function kv(env, binding = "DATA") {
  const ns = env && env[binding];
  if (!ns) throw new Error(`missing KV binding ${binding}`);
  return ns;
}

// Serve `key` from KV (streamed, never parsed, so large values cost no CPU). When KV has no
// value, the static asset at the same path answers instead. Only GET and HEAD reach KV.
export async function serveData(request, env, ctx, { key, contentType, binding = "DATA" } = {}) {
  const url = new URL(request.url);
  const dataKey = key || decodeURIComponent(url.pathname.replace(/^\/+/, ""));
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Method not allowed", { status: 405, headers: { allow: "GET, HEAD" } });
  }
  const cache = globalThis.caches && globalThis.caches.default;
  const cacheKey = new Request(url.origin + url.pathname, { method: "GET" });
  if (cache && request.method === "GET") {
    const hit = await cache.match(cacheKey);
    if (hit) return hit;
  }
  const { value, metadata } = await kv(env, binding).getWithMetadata(dataKey, { type: "stream" });
  if (value === null || value === undefined) {
    if (!env.ASSETS) return new Response("Not found", { status: 404 });
    const asset = await env.ASSETS.fetch(new Request(url.origin + url.pathname, { method: request.method }));
    const headers = new Headers(asset.headers);
    headers.set("x-data-source", "static");
    return new Response(asset.body, { status: asset.status, headers });
  }
  const headers = new Headers({
    "content-type": contentType || contentTypeFor(dataKey),
    "cache-control": CACHE_CONTROL,
    "x-data-source": "kv",
    "access-control-allow-origin": "*",
  });
  if (metadata && metadata.updatedAt) headers.set("x-data-updated-at", metadata.updatedAt);
  const response = new Response(request.method === "HEAD" ? null : value, { status: 200, headers });
  if (cache && request.method === "GET" && ctx && ctx.waitUntil) {
    ctx.waitUntil(cache.put(cacheKey, response.clone()).catch(() => {}));
  }
  return response;
}

// Store a value (string or object; objects are JSON-encoded) with `updatedAt` metadata.
export async function putData(env, key, value, { binding = "DATA", updatedAt, metadata = {} } = {}) {
  const body = typeof value === "string" ? value : JSON.stringify(value);
  const meta = { ...metadata, updatedAt: updatedAt || new Date().toISOString() };
  await kv(env, binding).put(key, body, { metadata: meta });
  return meta;
}

export async function readJson(env, key, { binding = "DATA" } = {}) {
  return kv(env, binding).get(key, { type: "json" });
}

// Read a JSON value from KV, else from the deployed static asset at `/${key}`.
export async function readJsonOrAsset(env, key, { binding = "DATA", assetPath } = {}) {
  const stored = await readJson(env, key, { binding });
  if (stored !== null && stored !== undefined) return stored;
  return readAssetJson(env, assetPath || `/${key}`);
}

export async function readAssetJson(env, path) {
  if (!env.ASSETS) return null;
  try {
    const response = await env.ASSETS.fetch(new Request(`https://assets.local${path}`));
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

function timingSafeEqual(a, b) {
  const x = new TextEncoder().encode(String(a));
  const y = new TextEncoder().encode(String(b));
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] || 0) ^ (y[i] || 0);
  return diff === 0;
}

export function cronAuthorized(request, env) {
  const expected = String((env && env.CRON_SECRET) || "");
  const provided = String(request.headers.get("x-blt-cron-secret") || "");
  return expected !== "" && timingSafeEqual(provided, expected);
}

// POST /__scheduled from blt-cron: {cron, scheduledTime, task?, reset?, ...}. `tasks` maps a task
// name to async (env, {...body, scheduledTime, reset}) => result. With no `task` in the body, every task runs.
// The work is awaited (not waitUntil) so blt-cron sees failures in the status code.
export async function handleCronDispatch(request, env, tasks) {
  if (request.method !== "POST") return json({ ok: false, error: "Method not allowed" }, 405);
  if (!cronAuthorized(request, env)) return json({ ok: false, error: "Forbidden" }, 403);
  let body = {};
  try {
    body = JSON.parse((await request.text()) || "{}") || {};
  } catch {
    body = {};
  }
  const names = body.task ? [body.task] : Object.keys(tasks);
  const unknown = names.filter((name) => !tasks[name]);
  if (unknown.length) return json({ ok: false, error: `unknown task ${unknown.join(", ")}` }, 400);
  const scheduledTime = Number(body.scheduledTime) || Date.now();
  const results = {};
  let ok = true;
  for (const name of names) {
    try {
      results[name] = await tasks[name](env, { ...body, scheduledTime, reset: Boolean(body.reset) });
    } catch (error) {
      ok = false;
      results[name] = { error: String((error && error.message) || error) };
      console.error(`${name}: ${results[name].error}`);
    }
  }
  return json({ ok, results }, ok ? 200 : 500);
}

export function utcDay(time) {
  return new Date(time).toISOString().slice(0, 10);
}

// Spread one refresh over several invocations. State lives in KV at `state:<name>`:
//   {run, next, results, done}
// `run` names the refresh (usually the UTC day); a new run starts from item 0. Each invocation
// processes items while their estimated subrequest cost fits in `budget`, then saves the cursor.
// After the last item, `finish(results)` publishes the data and the run is marked done, so later
// calls on the same run do nothing until the next run (or `reset`).
export async function runChunked(env, {
  name, run, items, process, finish,
  cost = () => 1, budget = DEFAULT_BUDGET, reset = false, binding = "DATA",
}) {
  const stateKey = `state:${name}`;
  let state = reset ? null : await readJson(env, stateKey, { binding });
  if (!state || state.run !== run) state = { run, next: 0, results: {}, done: false };
  if (state.done) return { run, done: true, skipped: true };
  let spent = 0;
  let processed = 0;
  while (state.next < items.length) {
    const item = items[state.next];
    const itemCost = Math.max(1, Number(cost(item)) || 1);
    if (processed > 0 && spent + itemCost > budget) break;
    const id = item && typeof item === "object" ? item.id : String(item);
    state.results[id] = await process(item, state.results[id]);
    spent += itemCost;
    processed += 1;
    state.next += 1;
  }
  if (state.next >= items.length) {
    await finish(state.results);
    state.done = true;
  }
  await kv(env, binding).put(stateKey, JSON.stringify(state));
  return { run, processed, next: state.next, total: items.length, done: state.done };
}
