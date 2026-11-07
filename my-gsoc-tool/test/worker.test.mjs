import assert from "node:assert/strict";
import test from "node:test";
import worker from "../worker/index.js";
import { CONTRIBUTIONS_KEY, DIRECTORY_KEY, FORKS_KEY, directoryItems, keepKnownStats, sampleTitles, siteCandidates, summarizeEvents, summarizeSite, usernameFromConfig } from "../worker/refresh.js";
import { MemoryKV, cronRequest, staticAssets, stubFetch } from "../../scripts/worker-data/testing.mjs";

const EVENTS = [
  { id: "1", type: "PushEvent", created_at: "2026-10-01T10:00:00Z", repo: { name: "o/r" }, payload: { commits: [{ message: "fix" }, { message: "b" }] } },
  { id: "1", type: "PushEvent", created_at: "2026-10-01T10:00:00Z", repo: { name: "o/r" }, payload: { commits: [{}] } },
  { id: "2", type: "PullRequestEvent", created_at: "2026-10-03T10:00:00Z", repo: { name: "o/r" }, payload: { action: "opened", pull_request: { title: "T", body: null, html_url: "u2" } } },
  { id: "3", type: "IssuesEvent", created_at: "2026-10-02T10:00:00Z", repo: { name: "o/r" }, payload: { action: "closed", issue: { title: "I", body: "x".repeat(300), html_url: "u3" } } },
  { id: "4", type: "PullRequestReviewEvent", created_at: "2026-09-30T10:00:00Z", repo: { name: "o/r" }, payload: { pull_request: { title: "R", html_url: "u4" } } },
  { id: "5", type: "WatchEvent", created_at: "2026-10-04T10:00:00Z", repo: { name: "o/r" }, payload: {} },
];

const env = () => ({
  CRON_SECRET: "s3cret",
  GH_API_TOKEN: "gh",
  DATA: new MemoryKV(),
  ASSETS: staticAssets({
    "/config.json": { student: { github: "https://github.com/Sumit6307" } },
    [`/${CONTRIBUTIONS_KEY}`]: { stats: { commits: 9 }, contributions: [] },
    [`/${FORKS_KEY}`]: { forks: [] },
  }),
});

test("summarizeEvents counts and orders like the old script", () => {
  const { stats, contributions } = summarizeEvents(EVENTS);
  assert.deepEqual(stats, { commits: 2, pullRequests: 1, issues: 1, reviews: 1 });
  assert.deepEqual(contributions.map((c) => c.type), ["pull_request", "issue", "commit", "review"]);
  assert.equal(contributions[0].description, "Pull request");
  assert.equal(contributions[1].description.length, 150);
  assert.equal(usernameFromConfig({ student: { github: "https://github.com/a/" } }), "a");
});

test("the daily refresh writes contributions and forks, then probes the forks' sites", async () => {
  const e = env();
  const fetches = stubFetch((url, init) => {
    if (url.startsWith("https://api.github.com")) assert.equal(init.headers.Authorization, "token gh");
    if (url.includes("/users/Sumit6307/events/public")) return EVENTS;
    if (url.includes("/repos/ananya-in-tech/MY-GSOC-TOOL/forks")) return [{ full_name: "a/b", html_url: "h", stargazers_count: 2, has_pages: false, owner: {} }];
    if (url.endsWith("/repos/ananya-in-tech/MY-GSOC-TOOL")) return { full_name: "ananya-in-tech/MY-GSOC-TOOL", html_url: "s", has_pages: true };
    return new Response("nope", { status: 404 });
  });
  try {
    const res = await worker.fetch(cronRequest({ scheduledTime: 1 }), e, {});
    assert.equal(res.status, 200);
    const data = JSON.parse(e.DATA.text(CONTRIBUTIONS_KEY));
    assert.equal(data.stats.commits, 2);
    const forks = JSON.parse(e.DATA.text(FORKS_KEY));
    assert.deepEqual(forks.forks, [{ full_name: "a/b", html_url: "h", stargazers_count: 2, homepage: "", has_pages: false, pushed_at: null }]);
    assert.equal(forks.source.full_name, "ananya-in-tech/MY-GSOC-TOOL");
    // a/b has no Pages site, so only the source repository's site is probed (and is down).
    assert.ok(fetches.calls.some((c) => c.url === "https://ananya-in-tech.github.io/MY-GSOC-TOOL/config.json"));
    assert.deepEqual(JSON.parse(e.DATA.text(DIRECTORY_KEY)).sites, []);
    const served = await worker.fetch(new Request(`https://t.test/${CONTRIBUTIONS_KEY}`), e, {});
    assert.equal(served.headers.get("x-data-source"), "kv");
    assert.equal((await served.json()).stats.commits, 2);
  } finally {
    fetches.restore();
  }
});

test("a failed GitHub call keeps the old data and reports 500", async () => {
  const e = env();
  const fetches = stubFetch(() => new Response("rate limited", { status: 403 }));
  try {
    const res = await worker.fetch(cronRequest({ task: "contributions" }), e, {});
    assert.equal(res.status, 500);
    assert.equal(e.DATA.text(CONTRIBUTIONS_KEY), null);
    const served = await worker.fetch(new Request(`https://t.test/${CONTRIBUTIONS_KEY}`), e, {});
    assert.equal(served.headers.get("x-data-source"), "static");
    assert.equal((await served.json()).stats.commits, 9);
  } finally {
    fetches.restore();
  }
});

test("other paths are static and /__scheduled needs the secret", async () => {
  const e = env();
  assert.equal((await worker.fetch(cronRequest({}, "bad"), e, {})).status, 403);
  const res = await worker.fetch(new Request("https://t.test/config.json"), e, {});
  assert.equal(res.headers.get("x-static"), "1");
});

test("the scheduled handler runs both refreshes for forks with their own cron trigger", async () => {
  const e = env();
  const fetches = stubFetch((url) => (url.includes("/forks") ? [] : url.includes("/repos/") ? {} : EVENTS));
  const waits = [];
  try {
    await worker.scheduled({ scheduledTime: 1 }, e, { waitUntil: (p) => waits.push(p) });
    await Promise.all(waits);
    assert.equal(fetches.calls.length, 3);
    assert.ok(e.DATA.text(CONTRIBUTIONS_KEY));
    assert.ok(e.DATA.text(FORKS_KEY));
  } finally {
    fetches.restore();
  }
});

test("a missing template repository skips the forks refresh and keeps the last list", async () => {
  const e = env();
  e.DATA.put(FORKS_KEY, JSON.stringify({ forks: [{ full_name: "kept/one" }] }));
  const fetches = stubFetch((url) => (url.includes("/repos/")
    ? new Response('{"message":"Not Found"}', { status: 404 })
    : EVENTS));
  try {
    const res = await worker.fetch(cronRequest({ task: "forks" }), e, { waitUntil() {} });
    const body = await res.json();
    assert.equal(body.ok, true);
    assert.equal(body.results.forks.skipped, "repository_not_found");
    assert.deepEqual(JSON.parse(e.DATA.text(FORKS_KEY)).forks, [{ full_name: "kept/one" }]);
  } finally {
    fetches.restore();
  }
});

test("site candidates skip the deleted original's homepage and use the fork's Pages site", () => {
  assert.deepEqual(siteCandidates({ full_name: "Jane/MY-GSOC-TOOL", homepage: "https://owasp-blt.github.io/MY-GSOC-TOOL/", has_pages: true }),
    ["https://jane.github.io/MY-GSOC-TOOL/"]);
  assert.deepEqual(siteCandidates({ full_name: "j/r", homepage: "https://jane.dev/gsoc?x=1", has_pages: false }), ["https://jane.dev/gsoc/"]);
  assert.deepEqual(siteCandidates({ full_name: "j/r", homepage: "javascript:alert(1)", has_pages: false }), []);
  const items = directoryItems(
    { source: { full_name: "s/r", has_pages: true }, forks: [{ full_name: "s/r", has_pages: true }, { full_name: "x/r", has_pages: false }] },
    { sites: [{ url: "https://gsoc-tool.owaspblt.org" }] },
  );
  assert.deepEqual(items.map((i) => i.id), ["https://gsoc-tool.owaspblt.org/", "https://s.github.io/r/"]);
});

test("a live site is probed for its student, search counts and own content", async () => {
  const e = env();
  e.DATA.put(FORKS_KEY, JSON.stringify({ forks: [{ full_name: "Jane/MY-GSOC-TOOL", html_url: "https://github.com/Jane/MY-GSOC-TOOL", has_pages: true, pushed_at: "2026-11-01T00:00:00Z" }] }));
  e.ASSETS = staticAssets({ "/data/blog-posts.json": [{ title: "Week 1: sample" }] });
  const site = "https://jane.github.io/MY-GSOC-TOOL/";
  const fetches = stubFetch((url) => {
    if (url === `${site}config.json`) return { student: { name: "Jane <b>", github: "https://github.com/Jane", email: "j@x.org" }, project: { title: "Your GSoC Project Title", organization: "OWASP" } };
    if (url === `${site}data/blog-posts.json`) return [{ title: "Week 1: sample" }, { title: "My real post" }];
    if (url.includes("/search/issues")) return { total_count: url.includes("is%3Amerged") ? 3 : 5 };
    return new Response("nope", { status: 404 });
  });
  try {
    const res = await worker.fetch(cronRequest({ task: "directory", scheduledTime: 1 }), e, {});
    assert.equal(res.status, 200);
    const [entry] = JSON.parse(e.DATA.text(DIRECTORY_KEY)).sites;
    assert.equal(entry.url, site);
    assert.equal(entry.name, "Jane <b>");
    assert.equal(entry.username, "Jane");
    assert.equal(entry.project.title, "");
    assert.equal(entry.project.organization, "OWASP");
    assert.deepEqual(entry.stats, { pullRequests: 5, mergedPullRequests: 3, issues: 5 });
    assert.equal(entry.content.blogPosts, 1);
    assert.equal(entry.email, undefined);
    assert.equal(JSON.stringify(entry).includes("j@x.org"), false);
  } finally {
    fetches.restore();
  }
});

test("titles shared by three dashboards count as sample text; failed searches keep old counts", () => {
  const sites = ["a", "b", "c"].map((id) => ({ url: id, stats: {}, content: { blogPosts: ["Old sample", `Own ${id}`] } }));
  const samples = sampleTitles(sites);
  assert.ok(samples.has("Old sample"));
  assert.equal(summarizeSite(sites[0], samples).content.blogPosts, 1);
  const kept = keepKnownStats({ stats: { pullRequests: null, issues: 2 } }, { stats: { pullRequests: 7, issues: 1 } });
  assert.deepEqual(kept.stats, { pullRequests: 7, issues: 2 });
});
