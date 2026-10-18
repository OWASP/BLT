// node --test scripts/actions/*.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as forge from "./forge.mjs";

const COMMIT_BACK = join(forge.ROOT, "scripts", "actions", "commit-back.sh");

async function withStub(fn) {
  const requests = [];
  const server = createServer((req, res) => {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      requests.push({ method: req.method, url: req.url, auth: req.headers.authorization, body: body ? JSON.parse(body) : null });
      res.setHeader("Content-Type", "application/json");
      if (req.url === "/api/actions/job/issues/404") { res.statusCode = 404; return res.end('{"error":"not found"}'); }
      if (req.method === "GET") return res.end(JSON.stringify({ number: 7, title: "t", body: "b", state: "open", labels: ["profile"], author: "alice" }));
      res.end(req.url.endsWith("/issues") ? '{"number":9}' : "{}");
    });
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const saved = { ...process.env };
  process.env.FORKMESH_API_URL = `http://127.0.0.1:${server.address().port}/`;
  process.env.FORKMESH_TOKEN = "job-token";
  try {
    await fn(requests);
  } finally {
    process.env = saved;
    server.close();
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
