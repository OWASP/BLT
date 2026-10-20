// node --test blt-action/forge/
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash, createPublicKey, verify } from "node:crypto";
import { execFileSync, spawn } from "node:child_process";
import { copyFileSync, cpSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as A from "./assign.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");
const SEED = Buffer.alloc(32, 7);
const signer = A.makeSigner(SEED);

// forkmesh app/src/entry.py: MENTION_RE (applied to the lowercased text) and NODE_NAME_RE.
const MENTION_RE = /(?<![A-Za-z0-9._%+-])@([a-z](?:[a-z0-9-]{0,61}[a-z0-9])?)\b/g;
const notified = (text) => [...String(text).toLowerCase().matchAll(MENTION_RE)].map((m) => m[1]);

function record(number, { assignees = [], status = "open", comments = [] } = {}) {
  return {
    assignees,
    author: "x",
    authorName: "someone",
    events: [
      { attachments: [], author: "x", body: "b", id: `open-${number}`, sig: "s", title: "t", ts: 1, type: "open" },
      ...comments.map(([id, login, body], i) => ({ attachments: [], author: `key-${login}`, authorName: login, body, id, sig: "s", ts: 10 + i, type: "comment" })),
    ],
    labels: [],
    number,
    schema: "forkmesh-issue-v1",
    status,
    title: "t",
    updatedAt: 100,
  };
}

function ledger(issues) {
  const root = mkdtempSync(join(tmpdir(), "assign-"));
  for (const [number, rec, side = "open"] of issues) {
    const dir = join(root, ".forkmesh", "issues", side, String(number));
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, `issue-${number}.json`), `${JSON.stringify(rec, null, 4)}\n`);
  }
  return root;
}

const issue = (rec, side = "open") => ({ side, record: rec });
const quiet = () => {};

test("parseCommand finds /assign and /unassign at the start of a line only", () => {
  assert.equal(A.parseCommand("/assign"), "assign");
  assert.equal(A.parseCommand("  /Assign please"), "assign");
  assert.equal(A.parseCommand("I'd like this.\n/assign"), "assign");
  assert.equal(A.parseCommand("/unassign"), "unassign");
  assert.equal(A.parseCommand("/assign.\n/unassign"), "assign");
  assert.equal(A.parseCommand("please /assign me"), null);
  assert.equal(A.parseCommand("/assignee"), null);
  assert.equal(A.parseCommand("/assigned"), null);
  assert.equal(A.parseCommand("> /assign"), null);
  assert.equal(A.parseCommand("```\n/assign\n```"), null);
  assert.equal(A.parseCommand("    /assign"), null);
  assert.equal(A.parseCommand("`/assign`"), null);
  assert.equal(A.parseCommand(""), null);
  assert.equal(A.parseCommand(undefined), null);
  assert.equal(A.parseCommand("$(rm -rf /)\n/assign"), "assign");
});

test("account names, bots and command keys", () => {
  assert.equal(A.accountName("Vanshika2720"), "vanshika2720");
  assert.equal(A.accountName("a-b"), "a-b");
  assert.equal(A.accountName("Cu6HYOAI_KXF_0n4il24bXIniH5dBGJ0ELffhPIkLLQ"), "");
  assert.equal(A.accountName("bad name"), "");
  assert.equal(A.accountName("$(id)"), "");
  for (const bot of ["blt-tasks[bot]", "owasp-blt-actions", "forkmesh-actions", "", null]) assert.ok(A.isBot(bot), String(bot));
  assert.ok(!A.isBot("vanshika2720"));
  assert.equal(A.commandKey(27, "c1", "Alice"), A.commandKey(27, "c1", "alice"));
  assert.notEqual(A.commandKey(27, "c1", "alice"), A.commandKey(27, "c2", "alice"));
});

test("assign: commenter only, refused when taken, closed or over the limit", () => {
  let d = A.decide({ command: "assign", name: "alice", issue: issue(record(1)) });
  assert.deepEqual(d.change, { assignees: ["alice"] });
  assert.match(d.reply, /^@alice you're assigned to this issue\. Please open a pull request for it within 7 days\./);

  d = A.decide({ command: "assign", name: "alice", issue: issue(record(1, { assignees: ["Alice"] })) });
  assert.equal(d.change, null);
  assert.match(d.reply, /already assigned to this issue/);

  d = A.decide({ command: "assign", name: "alice", issue: issue(record(1, { assignees: ["bob"] })) });
  assert.equal(d.change, null);
  assert.match(d.reply, /already assigned to @bob\. Please pick another issue/);

  d = A.decide({ command: "assign", name: "alice", issue: issue(record(1)), others: [5] });
  assert.equal(d.change, null);
  assert.match(d.reply, /already assigned to #5/);

  d = A.decide({ command: "assign", name: "alice", issue: issue(record(1, { status: "closed" }), "closed") });
  assert.equal(d.change, null);
  assert.match(d.reply, /closed/);
});

test("unassign removes only the commenter", () => {
  let d = A.decide({ command: "unassign", name: "alice", issue: issue(record(1, { assignees: ["bob", "alice"] })) });
  assert.deepEqual(d.change, { assignees: ["bob"] });
  assert.match(d.reply, /^@alice you're unassigned from this issue/);
  d = A.decide({ command: "unassign", name: "alice", issue: issue(record(1, { assignees: ["bob"] })) });
  assert.equal(d.change, null);
  assert.match(d.reply, /not assigned/);
});

test("every reply @mentions the commenter in the form the forge notifies", () => {
  const cases = [
    ["assign", record(1)],
    ["assign", record(1, { assignees: ["bob"] })],
    ["assign", record(1, { status: "closed" })],
    ["unassign", record(1, { assignees: ["vanshika2720"] })],
    ["unassign", record(1)],
  ];
  for (const [command, rec] of cases) {
    const { reply } = A.decide({ command, name: "vanshika2720", issue: issue(rec) });
    assert.ok(reply.startsWith("@vanshika2720 "), reply);
    assert.ok(notified(reply).includes("vanshika2720"), reply);
  }
  // The full reply with its dedupe marker still notifies exactly the assignee.
  const root = ledger([[27, record(27, { comments: [["c1", "vanshika2720", "/assign"]] })]]);
  const { pending } = A.applyCommands({ root, commands: A.collectCommands({ root, issueOverride: 27 }), signer, log: quiet });
  const body = A.replyFor(root, pending[0]);
  assert.match(body, /^@vanshika2720 you're assigned to this issue\./);
  assert.deepEqual(notified(body), ["vanshika2720"]);
  assert.ok(body.endsWith(A.replyMarker(pending[0].key)));
});

test("signed events verify with the forkmesh-issue-event-v2 message", () => {
  const ev = signer.sign(27, { id: "blt-assign-x", type: "assignees", assignees: ["alice"], ts: 123 });
  assert.equal(ev.authorName, "blt-tasks[bot]");
  assert.deepEqual(Object.keys(ev), [...Object.keys(ev)].sort());
  const hash = createHash("sha256").update("alice").digest("hex");
  const message = `forkmesh-issue-event-v2\nowasp-blt/blt\nassignees\n27\n${ev.author}\n123\n${hash}`;
  const pub = createPublicKey({ key: { kty: "OKP", crv: "Ed25519", x: ev.author }, format: "jwk" });
  assert.ok(verify(null, Buffer.from(message), pub, Buffer.from(ev.sig, "base64url")));
  assert.equal(A.parseSeed(SEED.toString("hex")).equals(SEED), true);
  assert.equal(A.parseSeed(SEED.toString("base64url")).equals(SEED), true);
  assert.throws(() => A.parseSeed("short"), /32 bytes/);
});

test("applyCommands: applies once, ignores bots, keys per comment, caps the work", () => {
  const comments = [
    ["c1", "alice", "/assign"],
    ["c2", "owasp-blt-actions", "/assign"],
    ["c3", "bob", "/assign"],
    ["c4", "alice", "/unassign"],
  ];
  const root = ledger([[27, record(27, { comments })], [5, record(5, { assignees: ["carol"] })]]);
  const commands = A.collectCommands({ root, issueOverride: 27 });
  assert.equal(commands.length, 4);
  const first = A.applyCommands({ root, commands, signer, now: 1000, log: quiet });
  assert.equal(first.changed.length, 1);
  const rec = JSON.parse(readFileSync(first.changed[0], "utf8"));
  // alice assigned, bob refused (taken), alice unassigned; the bot comment is ignored.
  assert.deepEqual(rec.assignees, []);
  const mine = rec.events.filter((e) => e.id.startsWith("blt-assign-"));
  assert.deepEqual(mine.map((e) => e.assignees), [["alice"], []]);
  assert.ok(mine.every((e, i) => e.ts > 100 && (i === 0 || e.ts > mine[i - 1].ts)));
  assert.equal(rec.updatedAt, mine[1].ts);
  assert.equal(first.pending.length, 3);

  // Rerunning applied commands changes nothing; their replies are still owed.
  const before = readFileSync(first.changed[0], "utf8");
  const applied = A.collectCommands({ root, issueOverride: 27 }).filter((c) => c.login === "alice");
  const second = A.applyCommands({ root, commands: applied, signer, now: 2000, log: quiet });
  assert.equal(second.changed.length, 0);
  assert.equal(second.pending.length, 2);
  assert.equal(readFileSync(first.changed[0], "utf8"), before);

  // A posted reply (materialized into the ledger) marks the command handled.
  const r = JSON.parse(before);
  for (const p of first.pending) r.events.push({ type: "comment", id: `r-${p.key}`, body: `x ${A.replyMarker(p.key)}`, author: "bot", authorName: "owasp-blt-actions", sig: "s", ts: 3000 });
  writeFileSync(first.changed[0], `${JSON.stringify(r, null, 4)}\n`);
  assert.equal(A.applyCommands({ root, commands: A.collectCommands({ root, issueOverride: 27 }), signer, log: quiet }).pending.length, 0);

  const many = ledger([[9, record(9, { comments: Array.from({ length: 30 }, (_, i) => [`m${i}`, "dave", "/assign"]) })]]);
  assert.equal(A.collectCommands({ root: many, issueOverride: 9 }).length, A.MAX_COMMANDS_PER_RUN);
});

test("the open-assignment limit counts other open issues only", () => {
  const root = ledger([
    [1, record(1)],
    [2, record(2, { assignees: ["Alice"] })],
    [3, record(3, { assignees: ["alice"], status: "closed" }), "closed"],
  ]);
  assert.deepEqual(A.openAssignments(root, "alice", 1), [2]);
  assert.deepEqual(A.openAssignments(root, "alice", 2), []);
});

test("collectCommands reads issue_comment payloads and skips other actions", () => {
  const event = { action: "created", issue: { number: 27 }, comment: { id: "c9", body: "/assign", user: { login: "alice" } } };
  assert.deepEqual(A.collectCommands({ root: "/nonexistent", event, name: "issue_comment" }), [
    { number: 27, commentId: "c9", login: "alice", author: "", body: "/assign" },
  ]);
  assert.deepEqual(A.collectCommands({ root: "/nonexistent", event: { ...event, action: "edited" }, name: "issue_comment" }), []);
  assert.deepEqual(A.collectCommands({ root: "/nonexistent", event, name: "push" }), []);
});

test("a comment without an account name gets a sign-in reply and no assignment", () => {
  const root = ledger([[4, record(4)]]);
  const event = { action: "created", issue: { number: 4 }, comment: { id: "k1", body: "/assign", user: { login: "Cu6HYOAI_KXF_0n4il24bXIniH5dBGJ0ELffhPIkLLQ" } } };
  const { pending, changed } = A.applyCommands({ root, commands: A.collectCommands({ root, event, name: "issue_comment" }), signer, log: quiet });
  assert.equal(changed.length, 0);
  assert.match(A.replyFor(root, pending[0]), /need a signed-in account/);
});

test("the issue #27 ledger: vanshika2720's /assign assigns her", () => {
  const live = join(REPO, ".forkmesh", "issues", "open", "27", "issue-27.json");
  const rec = JSON.parse(readFileSync(live, "utf8"));
  const root = ledger([[27, rec]]);
  const commands = A.collectCommands({ root, issueOverride: 27 });
  const cmd = commands.find((c) => c.commentId === "comment-web-1792476476195");
  assert.ok(cmd, "the /assign comment is in the ledger");
  const { pending } = A.applyCommands({ root, commands: [cmd], signer, log: quiet });
  const after = JSON.parse(readFileSync(join(root, ".forkmesh/issues/open/27/issue-27.json"), "utf8"));
  assert.deepEqual(after.assignees, ["vanshika2720"]);
  assert.match(A.replyFor(root, pending[0]), /^@vanshika2720 you're assigned to this issue\./);
});

// End to end: an issue_comment event, a bare origin that moves meanwhile, and a stub job API.
test("workflow run: pushes the signed assignment (rebuilt on a moved origin) and posts the @mention reply", async () => {
  const dir = mkdtempSync(join(tmpdir(), "assign-e2e-"));
  const git = (cwd, ...args) => execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@e", ...args], { cwd, encoding: "utf8" }).trim();
  const origin = join(dir, "origin.git");
  execFileSync("git", ["init", "-q", "--bare", "-b", "main", origin]);
  const seed = join(dir, "seedrepo");
  mkdirSync(seed);
  git(seed, "init", "-q", "-b", "main");
  for (const f of ["blt-action/forge/assign.mjs", "scripts/actions/forge.mjs", "scripts/actions/commit-back.sh"]) {
    mkdirSync(dirname(join(seed, f)), { recursive: true });
    copyFileSync(join(REPO, f), join(seed, f));
  }
  const issueDir = join(seed, ".forkmesh/issues/open/27");
  mkdirSync(issueDir, { recursive: true });
  writeFileSync(join(issueDir, "issue-27.json"), `${JSON.stringify(record(27, { comments: [["c1", "vanshika2720", "/assign"]] }), null, 4)}\n`);
  git(seed, "add", ".");
  git(seed, "commit", "-q", "-m", "init");
  git(seed, "push", "-q", origin, "HEAD:main");
  const work = join(dir, "work");
  execFileSync("git", ["clone", "-q", origin, work]);
  git(work, "config", "user.name", "runner");
  git(work, "config", "user.email", "runner@e");

  // Someone else appends a comment to the same ledger after the runner's checkout.
  const other = join(dir, "other");
  execFileSync("git", ["clone", "-q", origin, other]);
  const otherFile = join(other, ".forkmesh/issues/open/27/issue-27.json");
  const moved = JSON.parse(readFileSync(otherFile, "utf8"));
  moved.events.push({ attachments: [], author: "k", authorName: "zed", body: "nice", id: "c2", sig: "s", ts: 50, type: "comment" });
  writeFileSync(otherFile, `${JSON.stringify(moved, null, 4)}\n`);
  git(other, "commit", "-q", "-am", "intake");
  git(other, "push", "-q", "origin", "HEAD:main");

  const posts = [];
  const server = createServer((req, res) => {
    let data = "";
    req.on("data", (c) => (data += c));
    req.on("end", () => {
      posts.push({ url: req.url, auth: req.headers.authorization, body: JSON.parse(data || "null") });
      res.writeHead(201, { "Content-Type": "application/json" }).end('{"ok":true}');
    });
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const eventFile = join(dir, "event.json");
  writeFileSync(eventFile, JSON.stringify({ action: "created", issue: { number: 27 }, comment: { id: "c1", body: "/assign", user: { login: "vanshika2720" } } }));
  const env = {
    PATH: process.env.PATH,
    HOME: dir,
    FORKMESH_EVENT: "issue_comment",
    FORKMESH_EVENT_PATH: eventFile,
    FORKMESH_API_URL: `http://127.0.0.1:${server.address().port}`,
    FORKMESH_TOKEN: "job-token",
    BLT_TASKS_SEED: SEED.toString("base64url"),
  };
  const run = () =>
    new Promise((resolve) => {
      const child = spawn("node", ["blt-action/forge/assign.mjs"], { cwd: work, env });
      let out = "";
      child.stdout.on("data", (c) => (out += c));
      child.stderr.on("data", (c) => (out += c));
      child.on("close", (code) => resolve({ code, out }));
    });
  try {
    let r = await run();
    assert.equal(r.code, 0, r.out);
    const pushed = JSON.parse(git(origin, "show", "main:.forkmesh/issues/open/27/issue-27.json"));
    assert.deepEqual(pushed.assignees, ["vanshika2720"]);
    assert.ok(pushed.events.some((e) => e.id === "c2"), "the concurrent comment survived");
    assert.ok(pushed.events.some((e) => e.type === "assignees" && e.authorName === "blt-tasks[bot]"));
    assert.equal(posts.length, 1);
    assert.equal(posts[0].url, "/api/actions/job/issues/27/comments");
    assert.equal(posts[0].auth, "Bearer job-token");
    assert.match(posts[0].body.body, /^@vanshika2720 you're assigned to this issue\./);
    assert.deepEqual(notified(posts[0].body.body), ["vanshika2720"]);

    // The reply reaches the ledger through the inbox; a rerun then does nothing.
    git(work, "pull", "-q", "origin", "main");
    const file = join(work, ".forkmesh/issues/open/27/issue-27.json");
    const rec = JSON.parse(readFileSync(file, "utf8"));
    rec.events.push({ attachments: [], author: "bot", authorName: "owasp-blt-actions", body: posts[0].body.body, id: "actions-1", sig: "s", ts: rec.updatedAt + 5, type: "comment" });
    writeFileSync(file, `${JSON.stringify(rec, null, 4)}\n`);
    git(work, "commit", "-q", "-am", "intake reply");
    git(work, "push", "-q", "origin", "HEAD:main");
    const head = git(origin, "rev-parse", "main");
    r = await run();
    assert.equal(r.code, 0, r.out);
    assert.equal(git(origin, "rev-parse", "main"), head);
    assert.equal(posts.length, 1);
  } finally {
    server.close();
  }
});
