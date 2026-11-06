import assert from "node:assert/strict";
import test from "node:test";
import worker from "../worker/index.js";
import { STATE_KEY, parseIndex, parseLeaders, repoLine } from "../worker/new-projects.js";
import { MemoryKV, cronRequest, stubFetch } from "../../scripts/worker-data/testing.mjs";

const HOOK = "https://hooks.slack.test/new-projects";
const repo = (id, name, created, extra = {}) => ({
  id, name, full_name: `OWASP/${name}`, html_url: `https://github.com/OWASP/${name}`,
  default_branch: "main", created_at: `2026-11-0${created}T00:00:00Z`, ...extra,
});

function github(repos, pages = {}) {
  return stubFetch((url) => {
    if (url.startsWith("https://api.github.com/orgs/owasp/repos")) return repos;
    if (url.startsWith("https://raw.githubusercontent.com/")) {
      const path = url.slice("https://raw.githubusercontent.com/".length);
      return path in pages ? new Response(pages[path]) : new Response("", { status: 404 });
    }
    if (url === HOOK) return new Response("ok");
    return new Response("unexpected", { status: 500 });
  });
}

const env = (state) => ({
  CRON_SECRET: "s3cret",
  SLACK_WEBHOOK_URL: HOOK,
  DATA: new MemoryKV(state ? { [STATE_KEY]: JSON.stringify(state) } : {}),
});
const run = (e) => worker.fetch(cronRequest({ task: "new-projects" }), e, {});
const posts = (stub) => stub.calls.filter((c) => c.url === HOOK).map((c) => JSON.parse(c.init.body).text);

test("the first run only records the listing and posts nothing", async () => {
  const stub = github([repo(2, "www-project-b", 2), repo(1, "tool", 1)]);
  try {
    const e = env();
    assert.equal((await run(e)).status, 200);
    assert.deepEqual(JSON.parse(e.DATA.text(STATE_KEY)), { ids: [2, 1], since: "2026-11-02T00:00:00Z" });
    assert.deepEqual(posts(stub), []);
    assert.equal(stub.calls.length, 1);
    await run(e);
    assert.deepEqual(posts(stub), []);
  } finally {
    stub.restore();
  }
});

test("an old repository sliding into the newest 100 does not alert", async () => {
  const stub = github([repo(5, "www-project-old", 1), repo(4, "older-tool", 1)]);
  try {
    await run(env({ ids: [9], since: "2026-11-03T00:00:00Z" }));
    assert.deepEqual(posts(stub), []);
  } finally {
    stub.restore();
  }
});

test("new repositories are posted once, oldest first, compact, with project details", async () => {
  const stub = github(
    [
      repo(4, "www-project-d", 5),
      repo(3, "zap-helper", 4, { language: "Python", description: "Helper <for> ZAP" }),
      repo(1, "www-project-a", 1),
    ],
    {
      "OWASP/www-project-d/main/index.md": "---\nlayout: col-sidebar\ntitle: OWASP D\ntags: example\nlevel: 2\ntype: tool\npitch: \"Finds things.\"\n---\nBody.",
      "OWASP/www-project-d/main/leaders.md": "### Leaders\n* [Jane Doe](mailto:jane@owasp.org)\n* [Sam Roe](mailto:sam@owasp.org)\n",
    },
  );
  try {
    const e = env({ ids: [1], since: "2026-11-01T00:00:00Z" });
    const res = await run(e);
    assert.deepEqual((await res.json()).results["new-projects"].repos, ["OWASP/zap-helper", "OWASP/www-project-d"]);
    assert.deepEqual(posts(stub), ["*2 new OWASP repos*\n"
      + "• <https://github.com/OWASP/zap-helper|zap-helper> · Python — Helper &lt;for&gt; ZAP\n"
      + "• <https://github.com/OWASP/www-project-d|OWASP D> · level 2 · tool · 👤 Jane Doe, Sam Roe — Finds things."]);
    assert.equal(JSON.parse(e.DATA.text(STATE_KEY)).since, "2026-11-05T00:00:00Z");

    await run(e);
    assert.equal(posts(stub).length, 1);
  } finally {
    stub.restore();
  }
});

test("a failed Slack post keeps the repositories new for the next run", async () => {
  const stub = stubFetch((url) => (url === HOOK ? new Response("no", { status: 404 })
    : url.includes("api.github.com") ? [repo(2, "tool", 2)] : new Response("", { status: 404 })));
  try {
    const e = env({ ids: [1], since: "2026-11-01T00:00:00Z" });
    assert.equal((await run(e)).status, 500);
    assert.deepEqual(JSON.parse(e.DATA.text(STATE_KEY)), { ids: [1], since: "2026-11-01T00:00:00Z" });
  } finally {
    stub.restore();
  }
});

test("a GitHub error posts nothing and keeps the state", async () => {
  const stub = stubFetch((url) => (url === HOOK ? new Response("ok") : new Response("rate limited", { status: 403 })));
  try {
    const e = env();
    assert.equal((await run(e)).status, 500);
    assert.equal(e.DATA.text(STATE_KEY), null);
    assert.deepEqual(posts(stub), []);
  } finally {
    stub.restore();
  }
});

test("/__scheduled needs the cron secret", async () => {
  const res = await worker.fetch(cronRequest({ task: "new-projects" }, "wrong"), env(), {});
  assert.equal(res.status, 403);
});

test("index.md and leaders.md parsing", () => {
  assert.deepEqual(parseIndex("---\ntitle: 'X'\nlevel: 3\n---\n## Head\nOne [link](u). Two? Three."),
    { title: "X", level: "3", summary: "One link. Two?" });
  assert.deepEqual(parseLeaders("* [A](mailto:a)\n* [B](https://b) and [A](x)"), ["A", "B"]);
  const line = repoLine(repo(1, "www-project-x", 1), { summary: "s".repeat(300) }, ["A", "B", "C", "D"]);
  assert.match(line, /👤 A, B, C \+1 — s{159}…$/);
});
