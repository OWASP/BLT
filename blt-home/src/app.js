// blt-home request handling (the Worker entry point is src/worker.js).
//
// The Worker runs first for every request (run_worker_first in wrangler.toml):
//   /                 -> the landing page (public/index.html)
//   /_home/*, a few root files -> static assets from public/ (a prefix neither blt-next nor legacy uses)
//   /api/home-stats   -> live numbers, cached for 15 minutes
//   legacy Django paths (/issue/1/, /profile/x/, /api/v1/, ... see legacy.js)
//                     -> 308 to the same path on legacy.owaspblt.org
//   anything else     -> 308 to the same path on blt-next (next.owaspblt.org),
//                        so old owaspblt.org links (/pages/report-bug.html, /api/stats, ...) keep working.

import { LEGACY_ORIGIN, isLegacyPath } from "./legacy.js";
import { collectStats } from "./stats.js";

export const NEXT_ORIGIN = "https://next.owaspblt.org";
export const STATS_PATH = "/api/home-stats";
export const STATS_TTL_SECONDS = 900;
const ROOT_FILES = new Set(["/", "/index.html", "/favicon.ico", "/robots.txt"]);

export const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; " +
    "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'",
  "Strict-Transport-Security": "max-age=31536000",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "SAMEORIGIN",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Resource-Policy": "same-site",
  "X-Permitted-Cross-Domain-Policies": "none",
};

export function isHomePath(pathname) {
  return ROOT_FILES.has(pathname) || pathname.startsWith("/_home/");
}

export function redirectTarget(url) {
  const u = new URL(url);
  return (isLegacyPath(u.pathname) ? LEGACY_ORIGIN : NEXT_ORIGIN) + u.pathname + u.search;
}

function withHeaders(response, extra = {}) {
  const res = new Response(response.body, response);
  for (const [k, v] of Object.entries({ ...SECURITY_HEADERS, ...extra })) res.headers.set(k, v);
  return res;
}

function json(body, { status = 200, cache = "no-store" } = {}) {
  return withHeaders(
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json; charset=utf-8" } }),
    { "Cache-Control": cache },
  );
}

// One copy per isolate, so repeated requests skip the Cache API lookup too.
let memo = { at: 0, body: null };

export function resetMemo() {
  memo = { at: 0, body: null };
}

export async function homeStats({ fetcher = fetch, cache = globalThis.caches?.default, now = Date.now(), ctx } = {}) {
  if (memo.body && now - memo.at < STATS_TTL_SECONDS * 1000) return memo.body;
  const key = "https://blt-home.cache/api/home-stats";
  if (cache) {
    try {
      const hit = await cache.match(key);
      if (hit) {
        const body = await hit.json();
        memo = { at: now, body };
        return body;
      }
    } catch {
      /* cache unavailable: fall through to a live fetch */
    }
  }
  const body = await collectStats({ fetcher, now });
  const anyData = ["forge", "pool", "monitor", "pages"].some((k) => body[k]);
  // Cache a complete failure only briefly, so a short outage of every source is retried soon.
  const ttl = anyData ? STATS_TTL_SECONDS : 60;
  memo = { at: anyData ? now : now - (STATS_TTL_SECONDS - 60) * 1000, body };
  if (cache) {
    const put = cache
      .put(key, new Response(JSON.stringify(body), { headers: { "content-type": "application/json", "Cache-Control": `max-age=${ttl}` } }))
      .catch(() => {});
    if (ctx?.waitUntil) ctx.waitUntil(put);
    else await put;
  }
  return body;
}

export async function handle(request, env, ctx, { fetcher = fetch, cache } = {}) {
  const url = new URL(request.url);
  const { pathname } = url;

  if (pathname === STATS_PATH) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return json({ error: "method not allowed" }, { status: 405 });
    }
    const body = await homeStats({ fetcher, cache: cache === undefined ? globalThis.caches?.default : cache, ctx });
    return json(body, { cache: "public, max-age=300" });
  }

  if (isHomePath(pathname) && (request.method === "GET" || request.method === "HEAD")) {
    const res = await env.ASSETS.fetch(request);
    const cacheControl = pathname.startsWith("/_home/") ? "public, max-age=3600" : "public, max-age=300";
    return withHeaders(res, res.ok ? { "Cache-Control": cacheControl } : {});
  }

  return withHeaders(new Response(null, { status: 308, headers: { Location: redirectTarget(request.url) } }));
}
