// node --test test/*.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  parseIssueBody, isProfileIssue, hasTemplate, profileUsername, buildProfile, upsertIndex, ownsProfile, processIssue,
} from "../scripts/actions/add-profile.mjs";

const TEMPLATE = readFileSync(new URL("../issue-templates/add-profile.md", import.meta.url), "utf8");

function filled({ username = "", confirm = true, extra = {} } = {}) {
  let body = TEMPLATE
    .replace(/## Username\n\n<!--[^\n]*-->/, `## Username\n\n${username}`)
    .replace("## GitHub Username\n", "## GitHub Username\n\n@Alice-GH\n")
    .replace("## Website URL\n", "## Website URL\n\nhttps://alice.example\n")
    .replace("## LinkedIn Profile URL\n", "## LinkedIn Profile URL\n\njavascript:alert(1)\n")
    .replace("## Question 1: What is your involvement in cybersecurity?\n", `## Question 1: What is your involvement in cybersecurity?\n\n${"word ".repeat(60)}\n`);
  if (confirm) body = body.replace("- [ ] I confirm", "- [x] I confirm");
  for (const [k, v] of Object.entries(extra)) body = body.replace(`## ${k}\n\n`, `## ${k}\n\n${v}\n`);
  return body;
}

function issue(over = {}) {
  return { number: 12, title: "[blt-profiles] Add profile: alice", state: "open", labels: [], user: { login: "Alice", avatar_url: "https://img/a.png" }, body: filled(), ...over };
}

function harness() {
  const dir = mkdtempSync(join(tmpdir(), "profiles-"));
  writeFileSync(join(dir, "index.json"), JSON.stringify([{ username: "zed", name: "Zed" }]));
  const calls = [];
  const deps = {
    dir,
    comment: async (n, body) => calls.push(["comment", n, body]),
    closeIssue: async (n) => calls.push(["close", n]),
    commit: ({ message }) => (calls.push(["commit", message]), true),
    issueUrl: (n) => `https://forge.test/BLT/issues/${n}`,
    now: () => "2026-10-18T00:00:00Z",
  };
  const read = (name) => JSON.parse(readFileSync(join(dir, name), "utf8"));
  return { dir, calls, deps, read };
}

test("parses the template fields and the confirmation box", () => {
  const fields = parseIssueBody(filled());
  assert.equal(fields["Display Name"], "Your Name");
  assert.equal(fields["Role Section"], "Contributors");
  assert.equal(fields.Username, "");
  assert.equal(fields.Confirmation, "");
  assert.equal(fields.confirmed, true);
  assert.equal(parseIssueBody(filled({ confirm: false })).confirmed, false);
  assert.ok(hasTemplate(TEMPLATE));
  assert.ok(!hasTemplate("Broken link on the profile page"));
});

test("detects profile issues by label, title prefix or headings", () => {
  assert.ok(isProfileIssue({ title: "x", labels: [{ name: "Profile" }] }));
  assert.ok(isProfileIssue({ title: "x", labels: ["add-profile"] }));
  assert.ok(isProfileIssue({ title: "[blt-profiles] Add profile: bob", labels: [] }));
  assert.ok(isProfileIssue({ title: "hello", body: TEMPLATE }));
  assert.ok(!isProfileIssue({ title: "[blt-jobs] x", labels: ["bug"], body: "text" }));
});

test("username defaults to the author and is validated", () => {
  assert.equal(profileUsername({ Username: "" }, "Alice"), "alice");
  assert.equal(profileUsername({ Username: "@Bob.Smith" }, "alice"), "bob.smith");
  assert.throws(() => profileUsername({ Username: "a" }, "x"), /2-39/);
  assert.throws(() => profileUsername({ Username: "../etc" }, "x"), /2-39/);
  assert.throws(() => profileUsername({ Username: "profiles" }, "x"), /reserved/);
});

test("buildProfile cleans links and keeps counters of an existing profile", () => {
  const fields = parseIssueBody(filled({ extra: { "Role Section": "mentors", "Tags / Labels": "a; b, c" } }));
  const fresh = buildProfile(fields, { username: "alice", author: "Alice", now: "T1" });
  assert.equal(fresh.github, "https://github.com/alice-gh");
  assert.equal(fresh.linkedin, "");
  assert.equal(fresh.website, "https://alice.example");
  assert.equal(fresh.forge, "https://git.owaspblt.org/@Alice");
  assert.equal(fresh.created_at, "T1");
  assert.equal(fresh.stats.bugs_reported, 0);
  const updated = buildProfile(fields, { username: "alice", author: "Alice", now: "T2", existing: { ...fresh, stats: { bugs_reported: 5 }, badges: ["x"] } });
  assert.equal(updated.created_at, "T1");
  assert.equal(updated.updated_at, "T2");
  assert.deepEqual(updated.stats, { bugs_reported: 5 });
  assert.deepEqual(updated.badges, ["x"]);
});

test("upsertIndex replaces the entry and sorts by username", () => {
  const index = upsertIndex([{ username: "zed" }, { username: "alice", name: "old" }], {
    username: "alice", name: "new", role: "r", role_section: "Contributors", avatar: "", tags: [], stats: {}, prs: {},
    questions: { involvement: "x ".repeat(150) }, created_at: "T",
  });
  assert.deepEqual(index.map((e) => [e.username, e.name]), [["alice", "new"], ["zed", undefined]]);
  assert.ok(index[0].questions.involvement.length <= 203);
});

test("ownership: only the submitter, or the same-named account for older profiles", () => {
  assert.ok(ownsProfile(null, "alice", "bob"));
  assert.ok(ownsProfile({ submitted_by: "Bob" }, "alice", "bob"));
  assert.ok(!ownsProfile({ submitted_by: "carol" }, "alice", "bob"));
  assert.ok(ownsProfile({}, "alice", "Alice"));
  assert.ok(!ownsProfile({}, "alice", "mallory"));
});

test("processIssue writes the files, commits, comments and closes", async () => {
  const { calls, deps, read } = harness();
  const result = await processIssue(issue(), deps);
  assert.deepEqual(result, { status: "added", username: "alice", pushed: true });
  const profile = read("alice.json");
  assert.equal(profile.submitted_by, "Alice");
  assert.equal(profile.avatar, "https://img/a.png");
  assert.equal(profile.source_issue, "https://forge.test/BLT/issues/12");
  assert.deepEqual(read("index.json").map((e) => e.username), ["alice", "zed"]);
  assert.deepEqual(calls.map((c) => c[0]), ["commit", "comment", "close"]);
  assert.match(calls[0][1], /^blt-profiles: add profile @alice \(issue #12\)$/);
  assert.match(calls[1][2], /https:\/\/profiles\.owaspblt\.org\/alice/);

  calls.length = 0;
  const again = await processIssue(issue({ number: 13 }), deps);
  assert.equal(again.status, "updated");
  assert.match(calls[0][1], /update profile @alice/);
});

test("processIssue refuses another account's profile and unconfirmed issues", async () => {
  const { dir, calls, deps } = harness();
  writeFileSync(join(dir, "alice.json"), JSON.stringify({ username: "alice", submitted_by: "alice" }));
  const stolen = await processIssue(issue({ user: { login: "mallory" }, body: filled({ username: "alice" }) }), deps);
  assert.equal(stolen.status, "failed");
  assert.match(stolen.error, /belongs to another account/);
  const unconfirmed = await processIssue(issue({ body: filled({ confirm: false }) }), deps);
  assert.equal(unconfirmed.status, "failed");
  assert.deepEqual(calls.map((c) => c[0]), ["comment", "comment"]);
  assert.equal(JSON.parse(readFileSync(join(dir, "alice.json"), "utf8")).submitted_by, "alice");
});

test("processIssue skips closed issues and unrelated [blt-profiles] issues", async () => {
  const { dir, calls, deps } = harness();
  assert.equal((await processIssue(issue({ state: "closed" }), deps)).status, "skipped");
  assert.equal((await processIssue(issue({ title: "[blt-profiles] broken link", body: "The footer link 404s." }), deps)).status, "skipped");
  assert.equal(calls.length, 0);
  assert.ok(!existsSync(join(dir, "alice.json")));
  const labelled = await processIssue(issue({ labels: [{ name: "profile" }], body: "please add me" }), deps);
  assert.equal(labelled.status, "failed");
  assert.equal(calls.length, 1);
});

test("job API issue shape (author string, label strings) works", async () => {
  const { deps } = harness();
  const result = await processIssue({ number: 3, title: "Add me", state: "open", labels: ["profile"], author: "dave", body: filled() }, deps);
  assert.equal(result.username, "dave");
});
