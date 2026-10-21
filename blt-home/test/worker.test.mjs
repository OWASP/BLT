import { test } from "node:test";
import assert from "node:assert/strict";

import { handle, homeStats, isHomePath, redirectTarget, resetMemo, SECURITY_HEADERS, SHARED_HEADERS, STATS_TTL_SECONDS } from "../src/app.js";
import { SOURCES, collectStats, summariseForge, summarisePages, summarisePool, weeklyCommits } from "../src/stats.js";

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

const NOW = Date.parse("2026-10-21T02:30:00Z");
const FIXTURES = {
  [SOURCES.forge]: {
    commitCount: 45613,
    contributorsTruncated: false,
    contributors: [
      { name: "GitHub Action" }, { name: "github-actions[bot]" }, { name: "dependabot[bot]" }, { name: "Copilot" },
      { name: "DonnieBLT" }, { name: "Md Kaif Ansari" }, { name: "Sarthak5598" }, { name: "sarthak5598" },
    ],
    counts: { openIssues: 189, openPulls: 2 },
  },
  [SOURCES.pool]: {
    month: "2026-10",
    users: {
      alice: { total: 19 }, bob: { total: 25 }, "renovate[bot]": { total: 99 }, carol: { total: 0 }, dave: { total: 3 }, erin: { total: 1 },
    },
  },
  [SOURCES.pages]: { total_bugs: 0, total_domains: 0, leaderboard: [] },
};

function fakeFetch(map = FIXTURES, calls = []) {
  return async (url) => {
    calls.push(url);
    if (!(url in map)) throw new Error("network down");
    const v = map[url];
    return v instanceof Response ? v : json(v);
  };
}

function fakeCache() {
  const store = new Map();
  return {
    store,
    async match(key) { const r = store.get(key); return r ? r.clone() : undefined; },
    async put(key, res) { store.set(key, res); },
  };
}

const env = {
  ASSETS: {
    async fetch(request) {
      const { pathname } = new URL(request.url);
      if (["/", "/_home/home.css", "/_shared/blt-nav.js", "/_home/logos/blt-zero.webp"].includes(pathname)) return new Response("ok", { status: 200 });
      return new Response("missing", { status: 404 });
    },
  },
};

// ---- summarisers -------------------------------------------------------------

test("forge: counts people, not bots, and dedupes case", () => {
  assert.deepEqual(summariseForge(FIXTURES[SOURCES.forge]), { commits: 45613, contributors: 3, openIssues: 189, openPulls: 2 });
});

test("forge: truncated contributor list gives no contributor count", () => {
  const out = summariseForge({ ...FIXTURES[SOURCES.forge], contributorsTruncated: true });
  assert.equal(out.contributors, undefined);
  assert.equal(out.commits, 45613);
});

test("forge: junk gives null", () => {
  assert.equal(summariseForge(null), null);
  assert.equal(summariseForge({ commitCount: "lots", counts: { openIssues: -1 } }), null);
});

test("pool: top three by points, bots and zero rows dropped", () => {
  const out = summarisePool(FIXTURES[SOURCES.pool]);
  assert.equal(out.month, "2026-10");
  assert.deepEqual(out.top.map((r) => r.login), ["bob", "alice", "dave"]);
  assert.equal(summarisePool({ users: {} }), null);
  assert.equal(summarisePool({ month: "<script>", users: { a: { total: 1 } } }).month, null);
});

test("weekly commits: people only, oldest first, last 52 weeks", () => {
  const weeks = (n, v) => Array.from({ length: n }, (_, i) => v(i));
  const data = {
    activityStart: "2025-10-20T00:00:00+00:00",
    contributorsTruncated: false,
    contributors: [
      { name: "alice", activityWeeks: weeks(53, (i) => i) },
      { name: "bob", activityWeeks: weeks(53, () => 1) },
      { name: "dependabot[bot]", activityWeeks: weeks(53, () => 100) },
    ],
  };
  const out = weeklyCommits(data);
  assert.equal(out.counts.length, 52);
  assert.equal(out.counts[0], 2);
  assert.equal(out.counts[51], 53);
  assert.equal(out.start, "2025-10-27");
  const forge = summariseForge({ ...data, commitCount: 9 });
  assert.equal(forge.recentCommits, 50 + 51 + 52 + 53);
  assert.equal(forge.weeksStart, "2025-10-27");
  assert.equal(weeklyCommits({ ...data, contributorsTruncated: true }), null);
  assert.equal(weeklyCommits({ ...data, contributors: [{ name: "a", activityWeeks: [1, 2] }] }), null);
  assert.equal(weeklyCommits({ ...data, contributors: [data.contributors[0], { name: "c", activityWeeks: [1] }] }), null);
});

test("pages: real zero stays zero; rows need login and count", () => {
  assert.deepEqual(summarisePages(FIXTURES[SOURCES.pages]), { bugs: 0, domains: 0, top: [] });
  const out = summarisePages({ total_bugs: 5, leaderboard: [{ login: "a", count: 3 }, { login: "", count: 1 }, { count: 2 }] });
  assert.deepEqual(out.top, [{ login: "a", bugs: 3 }]);
  assert.equal(summarisePages({}), null);
});

test("collectStats: a failing source becomes null, the rest still load", async () => {
  const map = { ...FIXTURES };
  delete map[SOURCES.pool];
  map[SOURCES.pages] = new Response("oops", { status: 502 });
  const out = await collectStats({ fetcher: fakeFetch(map), now: NOW });
  assert.equal(out.pool, null);
  assert.equal(out.pages, null);
  assert.equal("monitor" in out, false);
  assert.equal(out.forge.commits, 45613);
});

test("collectStats: invalid JSON from a source is treated as missing", async () => {
  const map = { ...FIXTURES, [SOURCES.forge]: new Response("<html>", { status: 200 }) };
  const out = await collectStats({ fetcher: fakeFetch(map), now: NOW });
  assert.equal(out.forge, null);
});

// ---- /api/home-stats ----------------------------------------------------------

test("home-stats: cached for 15 minutes, then refetched", async () => {
  resetMemo();
  const calls = [];
  const cache = fakeCache();
  const fetcher = fakeFetch(FIXTURES, calls);
  await homeStats({ fetcher, cache, now: NOW });
  assert.equal(calls.length, 3);
  await homeStats({ fetcher, cache, now: NOW + 60e3 });
  assert.equal(calls.length, 3, "second call within the TTL is served from memory");
  const cached = cache.store.values().next().value;
  assert.match(cached.headers.get("Cache-Control"), new RegExp(`max-age=${STATS_TTL_SECONDS}`));
  resetMemo();
  cache.store.clear();
  await homeStats({ fetcher, cache, now: NOW + (STATS_TTL_SECONDS + 1) * 1000 });
  assert.equal(calls.length, 6);
});

test("home-stats: total outage is cached only briefly", async () => {
  resetMemo();
  const cache = fakeCache();
  const out = await homeStats({ fetcher: fakeFetch({}), cache, now: NOW });
  assert.deepEqual([out.forge, out.pool, out.pages], [null, null, null]);
  assert.match(cache.store.values().next().value.headers.get("Cache-Control"), /max-age=60\b/);
});

test("GET /api/home-stats returns JSON with security headers", async () => {
  resetMemo();
  const res = await handle(new Request("https://owaspblt.org/api/home-stats"), env, {}, { fetcher: fakeFetch(), cache: null });
  assert.equal(res.status, 200);
  assert.match(res.headers.get("content-type"), /application\/json/);
  assert.equal(res.headers.get("Content-Security-Policy"), SECURITY_HEADERS["Content-Security-Policy"]);
  const body = await res.json();
  assert.equal(body.forge.openIssues, 189);
});

test("POST /api/home-stats is refused", async () => {
  const res = await handle(new Request("https://owaspblt.org/api/home-stats", { method: "POST" }), env, {}, { cache: null });
  assert.equal(res.status, 405);
});

// ---- routing -------------------------------------------------------------------

test("landing page and its assets are served with security headers", async () => {
  for (const path of ["/", "/_home/home.css"]) {
    const res = await handle(new Request("https://owaspblt.org" + path), env, {});
    assert.equal(res.status, 200, path);
    for (const [k, v] of Object.entries(SECURITY_HEADERS)) assert.equal(res.headers.get(k), v, `${path} ${k}`);
  }
  assert.equal((await handle(new Request("https://owaspblt.org/_home/missing.js"), env, {})).status, 404);
});

test("the shared top bar and its logos can be embedded by other BLT sites; the page cannot", async () => {
  for (const path of ["/_shared/blt-nav.js", "/_home/logos/blt-zero.webp"]) {
    const res = await handle(new Request("https://owaspblt.org" + path), env, {});
    assert.equal(res.status, 200, path);
    for (const [k, v] of Object.entries(SHARED_HEADERS)) assert.equal(res.headers.get(k), v, `${path} ${k}`);
  }
  for (const path of ["/", "/_home/home.css"]) {
    const res = await handle(new Request("https://owaspblt.org" + path), env, {});
    assert.equal(res.headers.get("Cross-Origin-Resource-Policy"), "same-site", path);
    assert.equal(res.headers.get("Access-Control-Allow-Origin"), null, path);
  }
});

test("CSP allows only this origin: no CDNs", () => {
  const csp = SECURITY_HEADERS["Content-Security-Policy"];
  assert.doesNotMatch(csp, /https?:|unsafe-inline|unsafe-eval/);
});

test("isHomePath", () => {
  assert.ok(isHomePath("/"));
  assert.ok(isHomePath("/_home/logos/blt-zero.webp"));
  assert.ok(isHomePath("/_shared/blt-nav.js"));
  assert.ok(!isHomePath("/static/img/logo.png"));
  assert.ok(!isHomePath("/pages/report-bug.html"));
});

test("blt-next paths 308 to next.owaspblt.org with path and query", async () => {
  const cases = {
    "/pages/report-bug.html": "https://next.owaspblt.org/pages/report-bug.html",
    "/pages/leaderboard.html?x=1": "https://next.owaspblt.org/pages/leaderboard.html?x=1",
    "/api/stats": "https://next.owaspblt.org/api/stats",
    "/api/auth/login": "https://next.owaspblt.org/api/auth/login",
    "/assets/img/logo-lg.png": "https://next.owaspblt.org/assets/img/logo-lg.png",
    "/something-new": "https://next.owaspblt.org/something-new",
  };
  for (const [path, target] of Object.entries(cases)) {
    const res = await handle(new Request("https://owaspblt.org" + path), env, {});
    assert.equal(res.status, 308, path);
    assert.equal(res.headers.get("Location"), target, path);
  }
  const post = await handle(new Request("https://owaspblt.org/api/bugs", { method: "POST", body: "{}" }), env, {});
  assert.equal(post.status, 308, "308 keeps the method and body");
  assert.equal(post.headers.get("Location"), "https://next.owaspblt.org/api/bugs");
});

test("legacy Django paths 308 to blt-next's /legacy page with the original path and query", async () => {
  const L = "https://next.owaspblt.org/moved?from=";
  const cases = {
    "/issue/1234/": L + "%2Fissue%2F1234%2F",
    "/profile/alice/": L + "%2Fprofile%2Falice%2F",
    "/domain/example.com/": L + "%2Fdomain%2Fexample.com%2F",
    "/report/": L + "%2Freport%2F",
    "/api/v1/issues/?page=2": L + "%2Fapi%2Fv1%2Fissues%2F%3Fpage%3D2",
    "/accounts/login/?next=/&x=a%20b": L + "%2Faccounts%2Flogin%2F%3Fnext%3D%2F%26x%3Da%2520b",
    "/organization/acme/": L + "%2Forganization%2Facme%2F",
    "/hunt/7/": L + "%2Fhunt%2F7%2F",
    "/leaderboard/": L + "%2Fleaderboard%2F",
    "/bounties/": L + "%2Fbounties%2F",
    "/scoreboard/": L + "%2Fscoreboard%2F",
    "/static/img/logo.png": L + "%2Fstatic%2Fimg%2Flogo.png",
    "/media/screenshots/a.png": L + "%2Fmedia%2Fscreenshots%2Fa.png",
  };
  for (const [path, target] of Object.entries(cases)) {
    assert.equal(redirectTarget("https://owaspblt.org" + path), target, path);
    const res = await handle(new Request("https://owaspblt.org" + path), env, {});
    assert.equal(res.status, 308, path);
    assert.equal(res.headers.get("Location"), target, path);
    // the from= value decodes back to exactly the original path and query
    assert.equal(new URL(target).searchParams.get("from"), new URL("https://owaspblt.org" + path).pathname + new URL("https://owaspblt.org" + path).search);
  }
});

test("nothing redirects to the retired legacy host", () => {
  for (const path of ["/issue/1/", "/api/v1/x", "/pages/report-bug.html", "/whatever"]) {
    assert.doesNotMatch(redirectTarget("https://owaspblt.org" + path), /legacy\.owaspblt\.org/);
  }
});

test("segment matching is exact", () => {
  assert.equal(redirectTarget("https://owaspblt.org/issues-archive"), "https://next.owaspblt.org/issues-archive");
  assert.equal(redirectTarget("https://owaspblt.org/api/leaderboard"), "https://next.owaspblt.org/api/leaderboard");
  assert.equal(redirectTarget("https://owaspblt.org/api/v2/x"), "https://next.owaspblt.org/moved?from=%2Fapi%2Fv2%2Fx");
});
