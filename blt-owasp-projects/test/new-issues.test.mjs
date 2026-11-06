import assert from "node:assert/strict";
import test from "node:test";
import worker from "../worker/index.js";
import { STATE_KEY, issueLine, slackMessage } from "../worker/new-issues.js";
import { MemoryKV, cronRequest, stubFetch } from "../../scripts/worker-data/testing.mjs";

const HOOK = "https://hooks.slack.test/new-issues";
const issue = (id, repo, number, created, extra = {}) => ({
  id, number, title: `Issue ${number}`, html_url: `https://github.com/OWASP/${repo}/issues/${number}`,
  repository_url: `https://api.github.com/repos/OWASP/${repo}`, user: { login: "alice" }, labels: [],
  created_at: `2026-11-02T${created}:00Z`, ...extra,
});

function github(items) {
  return stubFetch((url) => {
    if (url.startsWith("https://api.github.com/search/issues")) return { items };
    if (url === HOOK) return new Response("ok");
    return new Response("unexpected", { status: 500 });
  });
}

const env = (state, hook = HOOK) => ({
  CRON_SECRET: "s3cret",
  SLACK_NEW_ISSUES_WEBHOOK: hook,
  DATA: new MemoryKV(state ? { [STATE_KEY]: JSON.stringify(state) } : {}),
});
const run = (e) => worker.fetch(cronRequest({ task: "new-issues" }), e, {});
const posts = (stub) => stub.calls.filter((c) => c.url === HOOK).map((c) => JSON.parse(c.init.body).text);

test("the first run only records the listing and posts nothing", async () => {
  const stub = github([issue(2, "www-project-a", 5, "10:00"), issue(1, "zap", 4, "09:00")]);
  try {
    const e = env();
    assert.equal((await run(e)).status, 200);
    assert.deepEqual(JSON.parse(e.DATA.text(STATE_KEY)), { ids: [2, 1], since: "2026-11-02T10:00:00Z" });
    await run(e);
    assert.deepEqual(posts(stub), []);
  } finally {
    stub.restore();
  }
});

test("new issues are posted once in one compact message, oldest first", async () => {
  const stub = github([
    issue(4, "www-project-b", 9, "12:00", { title: "Broken <link>", labels: [{ name: "bug" }, { name: "help wanted" }] }),
    issue(3, "zap", 8, "11:00"),
    issue(1, "zap", 4, "09:00"),
  ]);
  try {
    const e = env({ ids: [1], since: "2026-11-02T10:00:00Z" });
    await run(e);
    assert.deepEqual(posts(stub), ["*2 new OWASP issues*\n"
      + "• <https://github.com/OWASP/zap/issues/8|zap#8> Issue 8 · alice\n"
      + "• <https://github.com/OWASP/www-project-b/issues/9|www-project-b#9> Broken &lt;link&gt; · alice · bug, help wanted"]);
    await run(e);
    assert.equal(posts(stub).length, 1);
  } finally {
    stub.restore();
  }
});

test("a late-indexed issue within the lag still alerts; an old one never does", async () => {
  const stub = github([issue(6, "a", 2, "09:30"), issue(5, "b", 1, "07:00")]);
  try {
    await run(env({ ids: [9], since: "2026-11-02T10:00:00Z" }));
    assert.deepEqual(posts(stub), ["*1 new OWASP issue*\n• <https://github.com/OWASP/a/issues/2|a#2> Issue 2 · alice"]);
  } finally {
    stub.restore();
  }
});

test("without the webhook secret it keeps the state current and posts nothing", async () => {
  const stub = github([issue(3, "zap", 8, "11:00")]);
  try {
    const e = env({ ids: [1], since: "2026-11-02T10:00:00Z" }, "");
    const res = await run(e);
    assert.equal((await res.json()).results["new-issues"].skipped, 1);
    assert.deepEqual(JSON.parse(e.DATA.text(STATE_KEY)).ids, [3, 1]);
    assert.equal(stub.calls.length, 1);
  } finally {
    stub.restore();
  }
});

test("a failed Slack post keeps the issues new for the next run", async () => {
  const stub = stubFetch((url) => (url === HOOK ? new Response("no", { status: 500 }) : { items: [issue(3, "zap", 8, "11:00")] }));
  try {
    const e = env({ ids: [1], since: "2026-11-02T10:00:00Z" });
    assert.equal((await run(e)).status, 500);
    assert.deepEqual(JSON.parse(e.DATA.text(STATE_KEY)), { ids: [1], since: "2026-11-02T10:00:00Z" });
  } finally {
    stub.restore();
  }
});

test("long lists and titles stay compact", () => {
  assert.match(issueLine(issue(1, "r", 1, "01:00", { title: "t".repeat(200) })), /t{99}… · alice$/);
  const text = slackMessage(Array.from({ length: 35 }, (_, i) => issue(i, "r", i, "01:00"))).text;
  assert.equal(text.split("\n").length, 32);
  assert.match(text, /…and 5 more$/);
});
