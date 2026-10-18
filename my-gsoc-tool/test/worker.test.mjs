import assert from "node:assert/strict";
import test from "node:test";
import worker from "../worker/index.js";
import { CONTRIBUTIONS_KEY, FORKS_KEY, summarizeEvents, usernameFromConfig } from "../worker/refresh.js";
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

test("the daily refresh writes both files to KV with one request each", async () => {
  const e = env();
  const fetches = stubFetch((url, init) => {
    assert.equal(init.headers.Authorization, "token gh");
    if (url.includes("/users/Sumit6307/events/public")) return EVENTS;
    if (url.includes("/repos/OWASP-BLT/MY-GSOC-TOOL/forks")) return [{ full_name: "a/b", html_url: "h", stargazers_count: 2, owner: {} }];
    return new Response("nope", { status: 404 });
  });
  try {
    const res = await worker.fetch(cronRequest({ scheduledTime: 1 }), e, {});
    assert.equal(res.status, 200);
    assert.equal(fetches.calls.length, 2);
    const data = JSON.parse(e.DATA.text(CONTRIBUTIONS_KEY));
    assert.equal(data.stats.commits, 2);
    assert.deepEqual(JSON.parse(e.DATA.text(FORKS_KEY)).forks, [{ full_name: "a/b", html_url: "h", stargazers_count: 2 }]);
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
  const fetches = stubFetch((url) => (url.includes("/forks") ? [] : EVENTS));
  const waits = [];
  try {
    await worker.scheduled({ scheduledTime: 1 }, e, { waitUntil: (p) => waits.push(p) });
    await Promise.all(waits);
    assert.equal(fetches.calls.length, 2);
    assert.ok(e.DATA.text(CONTRIBUTIONS_KEY));
    assert.ok(e.DATA.text(FORKS_KEY));
  } finally {
    fetches.restore();
  }
});

test("a missing template repository skips the forks refresh and keeps the last list", async () => {
  const e = env();
  e.DATA.put(FORKS_KEY, JSON.stringify({ forks: [{ full_name: "kept/one" }] }));
  const fetches = stubFetch((url) => (url.includes("/forks")
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
