// blt-home request handling (the Worker entry point is src/worker.js).
//
// The Worker runs first for every request (run_worker_first in wrangler.toml):
//   /                 -> the landing page (public/index.html)
//   /_home/*, a few root files -> static assets from public/ (a prefix neither blt-next nor legacy uses)
//   /_shared/*        -> the BLT top bar (blt-nav.js) that every BLT site loads; it and the
//                        logos it shows may be embedded from other origins (see SHARED_HEADERS)
//   /api/home-stats   -> live numbers, cached for 15 minutes
//   legacy Django paths (/issue/1/, /profile/x/, /api/v1/, ... see legacy.js)
//                     -> 308 to next.owaspblt.org/moved?from=<path + query, URL-encoded>
//   anything else     -> 308 to the same path on blt-next (next.owaspblt.org),
//                        so old owaspblt.org links (/pages/report-bug.html, /api/stats, ...) keep working.

import { isLegacyPath, legacyTarget } from "./legacy.js";
import { collectStats } from "./stats.js";

export const NEXT_ORIGIN = "https://next.owaspblt.org";
export const STATS_PATH = "/api/home-stats";
export const STATS_TTL_SECONDS = 900;
const ROOT_FILES = new Set(["/", "/index.html", "/favicon.ico", "/robots.txt"]);

// The forge (git.owaspblt.org): its Analytics SDK and event endpoint (see public/_shared/blt-analytics.js).
export const FORGE_ORIGIN = "https://git.owaspblt.org";

export const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self' " + FORGE_ORIGIN + "; style-src 'self'; img-src 'self' data:; font-src 'self'; " +
    "connect-src 'self' " + FORGE_ORIGIN + "; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'",
  "Strict-Transport-Security": "max-age=31536000",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "SAMEORIGIN",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Resource-Policy": "same-site",
  "X-Permitted-Cross-Domain-Policies": "none",
};

// Files other BLT sites load from here: the shared top bar and the images it shows.
export const SHARED_HEADERS = {
  "Cross-Origin-Resource-Policy": "cross-origin",
  "Access-Control-Allow-Origin": "*",
};

export function isHomePath(pathname) {
  return ROOT_FILES.has(pathname) || pathname.startsWith("/_home/") || pathname.startsWith("/_shared/");
}

export function isSharedPath(pathname) {
  return pathname.startsWith("/_shared/") || pathname.startsWith("/_home/logos/") || pathname === "/_home/blt-logo.svg";
}

export function redirectTarget(url) {
  const u = new URL(url);
  return isLegacyPath(u.pathname) ? legacyTarget(u.pathname, u.search) : NEXT_ORIGIN + u.pathname + u.search;
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
  const anyData = ["forge", "pool", "pages"].some((k) => body[k]);
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
    const cacheControl = pathname.startsWith("/_home/") || pathname.startsWith("/_shared/") ? "public, max-age=3600" : "public, max-age=300";
    const extra = res.ok ? { "Cache-Control": cacheControl } : {};
    if (res.ok && isSharedPath(pathname)) Object.assign(extra, SHARED_HEADERS);
    return withHeaders(res, extra);
  }

  return withHeaders(new Response(null, { status: 308, headers: { Location: redirectTarget(request.url) } }));
}
