import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import worker, { TASKS } from "../worker/index.js";
import { KEY as STATS_KEY, PROJECTS, keepPrevious, parseLastPage, parseScript, projectCost, renderScript } from "../worker/gsoc2026-stats.js";
import { KEY as PROGRESS_KEY, commitMatchesContributor, contributorCost, dayWindow } from "../worker/progress.js";
import { MemoryKV, cronRequest, staticAssets, stubFetch } from "../../scripts/worker-data/testing.mjs";

const committedStats = readFileSync(new URL("../js/gsoc2026_stats.generated.js", import.meta.url), "utf8");
const contributors = JSON.parse(readFileSync(new URL("../data/contributors.json", import.meta.url), "utf8"));

function makeEnv(extra = {}) {
  return {
    CRON_SECRET: "s3cret",
    GH_API_TOKEN: "gh",
    DATA: new MemoryKV(),
    ASSETS: staticAssets({
      [`/${STATS_KEY}`]: committedStats,
      "/data/contributors.json": contributors,
      "/data/progress.json": { updated: null, days: { "2026-06-01": { old: { commits: 1 } } } },
      "/index.html": "<html>",
    }),
    ...extra,
  };
}

test("the committed stats file round-trips through parseScript/renderScript", () => {
  const payload = parseScript(committedStats);
  assert.ok(payload.projects["blt-netguardian"]);
  assert.deepEqual(parseScript(renderScript(payload)), payload);
});

test("every project fits one invocation's budget", () => {
  for (const project of PROJECTS) assert.ok(projectCost(project) <= 24, project.id);
  assert.equal(parseLastPage('<https://api.github.com/x?per_page=1&page=82>; rel="last"'), 82);
});

test("keepPrevious fills failed counts from yesterday", () => {
  const next = { repoStats: { openPR: null, mergedPR: 3 }, userStats: { u: { prTotal: null, closedIssues: 1 } } };
  keepPrevious(next, { repoStats: { openPR: 7, mergedPR: 1 }, userStats: { u: { prTotal: 4, closedIssues: 0 } } });
  assert.deepEqual(next, { repoStats: { openPR: 7, mergedPR: 3 }, userStats: { u: { prTotal: 4, closedIssues: 1 } } });
});

test("gsoc2026-stats refresh runs in chunks under the subrequest budget and publishes to KV", async () => {
  const env = makeEnv();
  const fetches = stubFetch((url, init) => {
    assert.equal(init.headers.Authorization, "Bearer gh");
    if (url.includes("/search/issues")) {
      return url.includes("BLT-University") ? new Response("{}", { status: 403 }) : { total_count: 2 };
    }
    return new Response("[{}]", { headers: { link: '<https://api.github.com/r?page=50>; rel="last"' } });
  });
  try {
    const scheduledTime = Date.parse("2026-10-18T02:17:00Z");
    let calls = 0;
    let result;
    do {
      const before = fetches.calls.length;
      const res = await worker.fetch(cronRequest({ task: "gsoc2026-stats", scheduledTime }), env, {});
      assert.equal(res.status, 200);
      result = (await res.json()).results["gsoc2026-stats"];
      assert.ok(fetches.calls.length - before <= 24, "budget per invocation");
      calls += 1;
    } while (!result.done && calls < 20);
    assert.ok(calls > 1 && calls <= 15, `took ${calls} calls`);
    const payload = parseScript(env.DATA.text(STATS_KEY));
    assert.equal(payload.projects["blt-netguardian"].repoStats.totalCommits, 100);
    assert.equal(payload.projects["blt-netguardian"].repoStats.openPR, 4);
    // The University searches answer 403 and the committed file has no previous count: null.
    assert.equal(payload.projects["blt-university"].repoStats.totalCommits, 50);
    assert.equal(payload.projects["blt-university"].repoStats.openPR, null);
    const again = await worker.fetch(cronRequest({ task: "gsoc2026-stats", scheduledTime }), env, {});
    assert.equal((await again.json()).results["gsoc2026-stats"].skipped, true);
  } finally {
    fetches.restore();
  }
});

test("the stats script is served from KV, else from the deployed file", async () => {
  const env = makeEnv();
  let res = await worker.fetch(new Request(`https://gsoc.test/${STATS_KEY}`), env, {});
  assert.equal(res.headers.get("x-data-source"), "static");
  assert.equal(await res.text(), committedStats);
  await env.DATA.put(STATS_KEY, "window.GSOC2026_STATS = {};\n", { metadata: { updatedAt: "t" } });
  res = await worker.fetch(new Request(`https://gsoc.test/${STATS_KEY}`), env, {});
  assert.equal(res.headers.get("content-type"), "text/javascript; charset=utf-8");
  assert.equal(await res.text(), "window.GSOC2026_STATS = {};\n");
  res = await worker.fetch(new Request("https://gsoc.test/index.html"), env, {});
  assert.equal(await res.text(), "<html>");
});

test("commit matching uses names, logins and email local parts", () => {
  const c = { name: "Md Kaif Ansari", github: "mdkaifansari04", commit_authors: ["amdkaif843"] };
  assert.ok(commitMatchesContributor({ author_name: "MD KAIF ANSARI" }, c));
  assert.ok(commitMatchesContributor({ author_email: "amdkaif843@gmail.com" }, c));
  assert.ok(!commitMatchesContributor({ author_name: "someone" }, c));
  assert.deepEqual(dayWindow("2026-06-11"), ["2026-06-11T00:00:00Z", "2026-06-12T00:00:00Z"]);
  for (const contributor of contributors) assert.ok(contributorCost(contributor) <= 30);
});

test("progress refresh fills today's entry over several calls and keeps older days", async () => {
  const env = makeEnv({ GITLAB_TOKEN: "gl", SLACK_TOKEN_OWASP: "xoxp" });
  const fetches = stubFetch((url, init) => {
    if (url.startsWith("https://slack.com/")) return { ok: true, messages: { total: url.includes("rosai") ? 1 : 0 } };
    assert.equal(init.headers["PRIVATE-TOKEN"], "gl");
    if (url.includes("BLT-NetGuardian")) return [{ author_name: "Preetham" }, { author_name: "other" }];
    return [];
  });
  try {
    const scheduledTime = Date.parse("2026-10-18T23:07:00Z");
    let result;
    let calls = 0;
    do {
      const before = fetches.calls.length;
      const res = await worker.fetch(cronRequest({ task: "progress", scheduledTime }), env, {});
      result = (await res.json()).results.progress;
      assert.ok(fetches.calls.length - before <= 30);
      calls += 1;
    } while (!result.done && calls < 10);
    assert.ok(calls >= 2 && calls <= 5, `took ${calls} calls`);
    const progress = JSON.parse(env.DATA.text(PROGRESS_KEY));
    assert.deepEqual(Object.keys(progress.days), ["2026-06-01", "2026-10-18"]);
    assert.equal(progress.days["2026-10-18"].Pritz395.commits, 1);
    assert.deepEqual(progress.days["2026-10-18"]["Nachiket-Roy"], { commits: 0, checkin: true, slack: { owasp: true, blt: false } });
    // Slack calls only go out for workspaces with a token and contributors with a username.
    assert.equal(fetches.calls.filter((c) => c.url.startsWith("https://slack.com/")).length, 1);
  } finally {
    fetches.restore();
  }
});

test("TASKS lists both refreshes", () => {
  assert.deepEqual(Object.keys(TASKS).sort(), ["gsoc2026-stats", "progress"]);
});
