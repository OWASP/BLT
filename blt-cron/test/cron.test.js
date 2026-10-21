import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { cronMatches, parseCron } from "../src/cron.js";
import { dueJobs, runJob } from "../src/index.js";
import { JOBS } from "../src/jobs.js";

const at = (iso) => new Date(iso);

test("every job's cron parses", () => {
  for (const job of JOBS) parseCron(job.cron);
});

test("every job's binding is a service binding in wrangler.toml", () => {
  const toml = readFileSync(new URL("../wrangler.toml", import.meta.url), "utf8");
  for (const job of JOBS) assert.match(toml, new RegExp(`binding = "${job.binding}"`), job.name);
  assert.match(toml, /binding = "HACKERHOUSE"\nservice = "hackerhouse"/);
  assert.match(toml, /binding = "SAMMICH"\nservice = "blt-sammich"/);
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
  assert.deepEqual(names, ["blt-leaf", "blt-lettuce", "blt-monitor", "blt-netguardian", "blt-sizzle"]);
  const quiet = dueJobs(Date.parse("2026-10-18T04:08:00Z")).map((j) => j.name);
  assert.deepEqual(quiet, []);
  assert.ok(!dueJobs(Date.parse("2026-10-18T04:30:00Z")).some((j) => j.name === "blt-lettuce"));
});

test("hackerhouse polls the forge every 5 minutes, off the other jobs' minutes", () => {
  const names = (iso) => dueJobs(Date.parse(iso)).map((j) => j.name);
  const job = JOBS.find((j) => j.name === "hackerhouse");
  assert.equal(job.binding, "HACKERHOUSE");
  assert.deepEqual(names("2026-10-18T04:02:00Z"), ["hackerhouse"]);
  assert.deepEqual(names("2026-10-18T04:57:00Z"), ["hackerhouse"]);
  assert.ok(!names("2026-10-18T04:05:00Z").includes("hackerhouse"));
  assert.ok(!names("2026-10-18T04:00:00Z").includes("hackerhouse"));
  const perDay = Array.from({ length: 1440 }, (_, m) => Date.parse("2026-10-18T00:00:00Z") + m * 60000)
    .filter((t) => dueJobs(t).some((j) => j.name === "hackerhouse")).length;
  assert.equal(perDay, 288);
});

test("blt-pool only runs its forge leaderboard task (no GitHub stale-assignment sweep)", () => {
  const pool = JOBS.filter((j) => j.binding === "POOL");
  assert.deepEqual(pool.map((j) => j.task), ["forge-leaderboard"]);
});

test("blt-pool reads the forge pulls ledger every 20 minutes on its own minutes", () => {
  const names = (iso) => dueJobs(Date.parse(iso)).map((j) => j.name);
  const job = JOBS.find((j) => j.name === "blt-pool-leaderboard");
  assert.equal(job.binding, "POOL");
  assert.equal(job.task, "forge-leaderboard");
  for (const iso of ["2026-10-18T04:06:00Z", "2026-10-18T04:26:00Z", "2026-10-18T04:46:00Z", "2026-10-18T00:06:00Z"]) {
    assert.deepEqual(names(iso), ["blt-pool-leaderboard"], iso);
  }
  assert.ok(!names("2026-10-18T04:00:00Z").includes("blt-pool-leaderboard"));
  const perDay = Array.from({ length: 1440 }, (_, m) => Date.parse("2026-10-18T00:00:00Z") + m * 60000)
    .filter((t) => dueJobs(t).some((j) => j.name === "blt-pool-leaderboard")).length;
  assert.equal(perDay, 72);
});

test("blt-sammich sends reminders every 5 minutes on a minute no other job uses", () => {
  const names = (iso) => dueJobs(Date.parse(iso)).map((j) => j.name);
  const job = JOBS.find((j) => j.name === "blt-sammich");
  assert.equal(job.binding, "SAMMICH");
  assert.equal(job.task, undefined);
  for (const iso of ["2026-10-18T04:04:00Z", "2026-10-18T04:09:00Z", "2026-10-18T00:59:00Z", "2026-10-18T23:34:00Z"]) {
    assert.deepEqual(names(iso), ["blt-sammich"], iso);
  }
  for (const iso of ["2026-10-18T04:00:00Z", "2026-10-18T04:02:00Z", "2026-10-18T04:05:00Z", "2026-10-18T00:03:00Z"]) {
    assert.ok(!names(iso).includes("blt-sammich"), iso);
  }
  const perDay = Array.from({ length: 1440 }, (_, m) => Date.parse("2026-10-18T00:00:00Z") + m * 60000)
    .filter((t) => dueJobs(t).some((j) => j.name === "blt-sammich")).length;
  assert.equal(perDay, 288);
});

test("chunked data refreshes run once a minute in their window", () => {
  const names = (iso) => dueJobs(Date.parse(iso)).map((j) => j.name);
  assert.ok(!names("2026-10-18T02:17:00Z").includes("blt-gsoc-stats"), "GSoC 2026 stats are off");
  assert.ok(!names("2026-10-18T23:09:00Z").includes("blt-gsoc-progress"), "GSoC 2026 progress is off");
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
