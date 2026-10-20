// node --test scripts/actions/*.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as forge from "./forge.mjs";

const COMMIT_BACK = join(forge.ROOT, "scripts", "actions", "commit-back.sh");

async function withStub(fn) {
  const requests = [];
  const savedFetch = globalThis.fetch;
  const saved = { ...process.env };
  process.env.FORKMESH_API_URL = "http://job-api.test/";
  process.env.FORKMESH_TOKEN = "job-token";
  globalThis.fetch = async (url, init = {}) => {
    const { pathname } = new URL(String(url));
    const headers = new Headers(init.headers || {});
    const method = String(init.method || "GET").toUpperCase();
    requests.push({ method, url: pathname, auth: headers.get("authorization"), body: init.body ? JSON.parse(init.body) : null });
    const json = (status, value) => new Response(value, { status, headers: { "Content-Type": "application/json" } });
    if (pathname === "/api/actions/job/issues/404") return json(404, '{"error":"not found"}');
    if (method === "GET") return json(200, JSON.stringify({ number: 7, title: "t", body: "b", state: "open", labels: ["profile"], author: "alice" }));
    return json(200, pathname.endsWith("/issues") ? '{"number":9}' : "{}");
  };
  try {
    await fn(requests);
  } finally {
    globalThis.fetch = savedFetch;
    process.env = saved;
  }
}

test("job API calls use the bearer token and documented paths", async () => {
  await withStub(async (requests) => {
    assert.equal((await forge.getIssue(7)).author, "alice");
    await forge.comment(7, "hi");
    await forge.changeLabels(7, { add: ["a"] });
    await forge.closeIssue(7);
    assert.deepEqual(await forge.createIssue({ title: "x" }), { number: 9 });
    await assert.rejects(forge.getIssue(404), /HTTP 404/);
    assert.deepEqual(requests.map((r) => `${r.method} ${r.url}`), [
      "GET /api/actions/job/issues/7",
      "POST /api/actions/job/issues/7/comments",
      "POST /api/actions/job/issues/7/labels",
      "POST /api/actions/job/issues/7/state",
      "POST /api/actions/job/issues",
      "GET /api/actions/job/issues/404",
    ]);
    assert.ok(requests.every((r) => r.auth === "Bearer job-token"));
    assert.deepEqual(requests[1].body, { body: "hi" });
    assert.deepEqual(requests[2].body, { add: ["a"], remove: [] });
    assert.deepEqual(requests[3].body, { state: "closed" });
    assert.deepEqual(requests[4].body, { title: "x", body: "", labels: [] });
  });
});

test("issue helpers accept event and job API shapes", () => {
  assert.deepEqual(forge.labelNames({ labels: [{ name: "a" }, "b", null] }), ["a", "b"]);
  assert.equal(forge.authorLogin({ user: { login: "bob" } }), "bob");
  assert.equal(forge.authorLogin({ author: "carol" }), "carol");
  assert.equal(forge.authorLogin({ author: { login: "dan" } }), "dan");
  process.env.FORKMESH_API_URL = "https://git.example.org/";
  process.env.GITHUB_REPOSITORY = "BLT/BLT";
  assert.equal(forge.issueUrl(5), "https://git.example.org/BLT/BLT/issues/5");
});

test("readEvent reads FORKMESH_EVENT_PATH", () => {
  const dir = mkdtempSync(join(tmpdir(), "forge-"));
  writeFileSync(join(dir, "event.json"), '{"issue":{"number":3}}');
  process.env.FORKMESH_EVENT_PATH = join(dir, "event.json");
  assert.equal(forge.readEvent().issue.number, 3);
});

test("commit-back.sh commits only the named paths, skips no-ops and pushes", () => {
  const dir = mkdtempSync(join(tmpdir(), "commit-back-"));
  const git = (cwd, ...args) => execFileSync("git", args, { cwd, encoding: "utf8" }).trim();
  const id = ["-c", "user.name=t", "-c", "user.email=t@example.org"];
  execFileSync("git", ["init", "-q", "--bare", "-b", "main", join(dir, "origin.git")]);
  execFileSync("git", ["clone", "-q", join(dir, "origin.git"), join(dir, "work")], { stdio: "ignore" });
  const work = join(dir, "work");
  git(work, "config", "user.name", "t");
  git(work, "config", "user.email", "t@example.org");
  writeFileSync(join(work, "data.json"), "1\n");
  writeFileSync(join(work, "other.txt"), "x\n");
  git(work, "add", ".");
  git(work, ...id, "commit", "-q", "-m", "init");
  git(work, "push", "-q", "origin", "HEAD:main");

  // Nothing changed: no commit.
  let r = spawnSync(COMMIT_BACK, ["-m", "p: none", "--", "data.json", "missing.json"], { cwd: work, encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /no changes/);

  // Someone else pushed meanwhile: the commit is rebased and pushed; other.txt stays uncommitted.
  execFileSync("git", ["clone", "-q", join(dir, "origin.git"), join(dir, "other")], { stdio: "ignore" });
  writeFileSync(join(dir, "other", "late.txt"), "y\n");
  git(join(dir, "other"), "add", ".");
  git(join(dir, "other"), ...id, "commit", "-q", "-m", "late");
  git(join(dir, "other"), "push", "-q", "origin", "HEAD:main");

  writeFileSync(join(work, "data.json"), "2\n");
  writeFileSync(join(work, "other.txt"), "changed\n");
  r = spawnSync(COMMIT_BACK, ["-m", "p: update data", "--", "data.json"], { cwd: work, encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
  const bare = join(dir, "origin.git");
  assert.equal(git(bare, "log", "-1", "--format=%s", "main"), "p: update data");
  assert.equal(git(bare, "log", "-2", "--format=%s", "main").split("\n")[1], "late");
  assert.equal(git(bare, "show", "main:data.json"), "2");
  assert.equal(git(bare, "show", "main:other.txt"), "x");
  assert.equal(readFileSync(join(work, "other.txt"), "utf8"), "changed\n");
});

test("commit-back.sh --rebuild regenerates on the new origin instead of keeping its side", () => {
  const dir = mkdtempSync(join(tmpdir(), "commit-back-rebuild-"));
  const git = (cwd, ...args) => execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@example.org", ...args], { cwd, encoding: "utf8" }).trim();
  execFileSync("git", ["init", "-q", "--bare", "-b", "main", join(dir, "origin.git")]);
  execFileSync("git", ["clone", "-q", join(dir, "origin.git"), join(dir, "work")], { stdio: "ignore" });
  const work = join(dir, "work");
  git(work, "config", "user.name", "t");
  git(work, "config", "user.email", "t@example.org");
  writeFileSync(join(work, "log.txt"), "a\n");
  git(work, "add", ".");
  git(work, "commit", "-q", "-m", "init");
  git(work, "push", "-q", "origin", "HEAD:main");

  // Another writer appends to the same file; -X theirs would drop its line.
  execFileSync("git", ["clone", "-q", join(dir, "origin.git"), join(dir, "other")], { stdio: "ignore" });
  writeFileSync(join(dir, "other", "log.txt"), "a\nother\n");
  git(join(dir, "other"), "commit", "-q", "-am", "other");
  git(join(dir, "other"), "push", "-q", "origin", "HEAD:main");

  const append = "grep -qx mine log.txt || echo mine >> log.txt";
  execFileSync("bash", ["-c", append], { cwd: work });
  const r = spawnSync(COMMIT_BACK, ["-m", "p: append", "--rebuild", append, "--", "log.txt"], { cwd: work, encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stderr, /rebuilding on origin\/main/);
  assert.equal(git(join(dir, "origin.git"), "show", "main:log.txt"), "a\nother\nmine");
  assert.equal(git(join(dir, "origin.git"), "log", "-1", "--format=%s", "main"), "p: append");
});
