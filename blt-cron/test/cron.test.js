import assert from "node:assert/strict";
import test from "node:test";
import { cronMatches, parseCron } from "../src/cron.js";
import { dueJobs, runJob } from "../src/index.js";
import { JOBS } from "../src/jobs.js";

const at = (iso) => new Date(iso);

test("every job's cron parses", () => {
  for (const job of JOBS) parseCron(job.cron);
});

test("cron matching", () => {
  assert.ok(cronMatches("* * * * *", at("2026-10-18T03:17:00Z")));
  assert.ok(cronMatches("*/5 * * * *", at("2026-10-18T03:15:00Z")));
  assert.ok(!cronMatches("*/5 * * * *", at("2026-10-18T03:16:00Z")));
  assert.ok(cronMatches("0 */2 * * *", at("2026-10-18T04:00:00Z")));
  assert.ok(!cronMatches("0 */2 * * *", at("2026-10-18T05:00:00Z")));
  assert.ok(cronMatches("0 9 * * 1-5", at("2026-10-19T09:00:00Z")));
  assert.ok(!cronMatches("0 9 * * 1-5", at("2026-10-18T09:00:00Z")));
  assert.ok(cronMatches("0 0 * * 7", at("2026-10-18T00:00:00Z")));
  assert.ok(cronMatches("30 1 1,15 * *", at("2026-10-15T01:30:00Z")));
  assert.throws(() => parseCron("* * * *"));
  assert.throws(() => parseCron("61 * * * *"));
});

test("due jobs at the top of an even hour", () => {
  const names = dueJobs(Date.parse("2026-10-18T04:00:30Z")).map((j) => j.name).sort();
  assert.deepEqual(names, ["blt-leaf", "blt-lettuce", "blt-monitor", "blt-netguardian", "blt-pool", "blt-sizzle", "blt-toasty"]);
  const quiet = dueJobs(Date.parse("2026-10-18T04:07:00Z")).map((j) => j.name);
  assert.deepEqual(quiet, ["blt-lettuce"]);
});

test("chunked data refreshes run once a minute in their window", () => {
  const names = (iso) => dueJobs(Date.parse(iso)).map((j) => j.name);
  assert.ok(names("2026-10-18T02:17:00Z").includes("blt-gsoc-stats"));
  assert.ok(names("2026-10-18T02:31:00Z").includes("blt-gsoc-stats"));
  assert.ok(!names("2026-10-18T02:32:00Z").includes("blt-gsoc-stats"));
  assert.ok(names("2026-10-18T23:09:00Z").includes("blt-gsoc-progress"));
  assert.ok(names("2026-10-18T00:03:00Z").includes("my-gsoc-tool"));
  for (const job of JOBS) assert.ok(job.binding, job.name);
});

test("runJob posts the cron and secret through the binding", async () => {
  const calls = [];
  const env = {
    CRON_SECRET: "s3cret",
    LEAF: { fetch: async (url, init) => { calls.push({ url, init }); return new Response("{}", { status: 200 }); } },
  };
  const result = await runJob(env, { name: "blt-leaf", binding: "LEAF", cron: "0 * * * *" }, 123);
  assert.equal(result.ok, true);
  assert.equal(calls[0].url, "https://cron.internal/__scheduled");
  assert.equal(calls[0].init.headers["x-blt-cron-secret"], "s3cret");
  assert.deepEqual(JSON.parse(calls[0].init.body), { cron: "0 * * * *", scheduledTime: 123 });
  await runJob(env, { name: "g", binding: "LEAF", cron: "7-11 23 * * *", task: "progress" }, 9);
  assert.deepEqual(JSON.parse(calls[1].init.body), { cron: "7-11 23 * * *", scheduledTime: 9, task: "progress" });
  const missing = await runJob({}, { name: "x", binding: "NOPE", cron: "* * * * *" }, 1);
  assert.equal(missing.ok, false);
});
