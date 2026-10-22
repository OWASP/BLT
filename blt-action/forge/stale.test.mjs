// node --test blt-action/forge/
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as S from "./stale.mjs";

const H = S.HOUR_MS;
const T0 = Date.parse("2026-10-01T12:00:00Z");
const quiet = () => {};

const claim = (assignee, by, ts, extra = {}) => ({
  assignee,
  author: `key-${by}`,
  authorName: by,
  authorVerified: true,
  claimState: "assigned",
  id: `claim-${by}-${ts}`,
  sig: "s",
  ts,
  type: "claim",
  ...extra,
});
const comment = (login, body, ts, verified = true) => ({
  attachments: [],
  author: `key-${login}`,
  authorName: login,
  authorVerified: verified,
  body,
  id: `c-${login}-${ts}`,
  sig: "s",
  ts,
  type: "comment",
});

function record(number, { assignees = [], events = [], status = "open" } = {}) {
  return {
    assignees,
    author: "x",
    authorName: "someone",
    events: [{ attachments: [], author: "x", body: "b", id: `open-${number}`, sig: "s", title: "t", ts: 1, type: "open" }, ...events],
    labels: [],
    number,
    schema: "forkmesh-issue-v1",
    status,
    title: "t",
    updatedAt: 100,
  };
}

function ledger(issues) {
  const root = mkdtempSync(join(tmpdir(), "stale-"));
  for (const [number, rec, side = "open"] of issues) {
    const dir = join(root, ".forkmesh", "issues", side, String(number));
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, `issue-${number}.json`), `${JSON.stringify(rec, null, 4)}\n`);
  }
  return root;
}

const run = (root, now, pulls = []) =>
  S.plan({ root, numbers: S.openIssueNumbers(root), pulls, now, log: quiet }).map((a) => `${a.action} #${a.number} @${a.name}`);

test("a quiet /assign claim is warned after 18 hours and released at 24 hours", () => {
  const rec = record(5, { assignees: ["alice"], events: [claim("alice", "owasp-blt-actions", T0)] });
  const root = ledger([[5, rec]]);
  assert.deepEqual(run(root, T0 + 17 * H), []);
  const [warn] = S.plan({ root, numbers: [5], pulls: [], now: T0 + 18 * H, log: quiet });
  assert.equal(warn.action, "warn");
  assert.match(warn.reply, /^@alice /);
  assert.ok(warn.reply.includes(S.warningMarker("alice", T0)));

  // The warning reaches the ledger as a comment from the -actions bot.
  rec.events.push(comment("owasp-blt-actions", warn.reply, T0 + 18 * H + 1000));
  const root2 = ledger([[5, rec]]);
  assert.deepEqual(run(root2, T0 + 20 * H), [], "warned, not stale yet");
  const [release] = S.plan({ root: root2, numbers: [5], pulls: [], now: T0 + 24 * H + 1000, log: quiet });
  assert.equal(release.action, "unassign");
  assert.match(release.reply, /^@alice you've been unassigned/);
  assert.ok(release.reply.includes("`/assign`"));
});

test("a late warning still gets its grace period", () => {
  const rec = record(5, {
    assignees: ["alice"],
    events: [claim("alice", "alice", T0), comment("owasp-blt-actions", `@alice ${S.warningMarker("alice", T0)}`, T0 + 30 * H)],
  });
  const root = ledger([[5, rec]]);
  assert.deepEqual(run(root, T0 + 30 * H + S.WARN_GRACE_MS - 1), [], "stale for hours, but warned too recently");
  assert.deepEqual(run(root, T0 + 30 * H + S.WARN_GRACE_MS), ["unassign #5 @alice"]);
});

test("a comment by the assignee restarts the clock and needs a new warning", () => {
  const warned = S.warningMarker("alice", T0);
  const rec = record(5, {
    assignees: ["alice"],
    events: [
      claim("alice", "alice", T0),
      comment("owasp-blt-actions", `@alice ... ${warned}`, T0 + 18 * H),
      comment("alice", "still on it", T0 + 20 * H),
    ],
  });
  const root = ledger([[5, rec]]);
  assert.deepEqual(run(root, T0 + 26 * H), [], "6 hours since alice's update");
  assert.deepEqual(run(root, T0 + 38.5 * H), ["warn #5 @alice"]);
});

test("comments that don't count: unverified, and a fake warning from a person", () => {
  const rec = record(5, {
    assignees: ["alice"],
    events: [
      claim("alice", "alice", T0),
      comment("alice", "unverified update", T0 + 17 * H, false),
      comment("mallory", `nope ${S.warningMarker("alice", T0)}`, T0 + 18 * H),
    ],
  });
  const root = ledger([[5, rec]]);
  assert.deepEqual(run(root, T0 + 21 * H), ["warn #5 @alice"], "the unverified comment and mallory's marker are ignored");
});

test("an open pull request, or one opened since the claim, keeps the claim", () => {
  const rec = record(5, { assignees: ["alice"], events: [claim("alice", "owasp-blt-actions", T0)] });
  const root = ledger([[5, rec]]);
  const now = T0 + 30 * H;
  assert.deepEqual(run(root, now, [{ number: 1, author: "Alice", status: "open", opened: T0 - 30 * H }]), []);
  assert.deepEqual(run(root, now, [{ number: 2, author: "alice", status: "merged", opened: T0 + H }]), []);
  assert.deepEqual(run(root, now, [{ number: 3, author: "alice", status: "closed", opened: T0 - H }]), ["warn #5 @alice"]);
  assert.deepEqual(run(root, now, [{ number: 4, author: "bob", status: "open", opened: T0 + H }]), ["warn #5 @alice"]);
});

test("only self-claims are released: a maintainer's assignment is left alone", () => {
  const root = ledger([
    [5, record(5, { assignees: ["alice"], events: [claim("alice", "donnieblt", T0)] })],
    [6, record(6, { assignees: ["bob"], events: [] })],
    [7, record(7, { assignees: ["carol"], events: [{ id: "blt-assign-abc", type: "assignees", assignees: ["carol"], authorName: "blt-tasks[bot]", ts: T0 }] })],
    [8, record(8, { assignees: ["dave"], events: [claim("dave", "dave", T0)] }), "closed"],
    [9, record(9, { assignees: ["erin"], events: [claim("erin", "erin", T0, { authorVerified: false })] })],
  ]);
  assert.deepEqual(run(root, T0 + 30 * H), ["warn #7 @carol"]);
});

test("the newest claim wins: a claim released and re-made later restarts the clock", () => {
  const rec = record(5, {
    assignees: ["alice"],
    events: [claim("alice", "alice", T0), claim("alice", "alice", T0 + 5 * H)],
  });
  assert.equal(S.assignment(rec, "alice").ts, T0 + 5 * H);
  const root = ledger([[5, rec]]);
  assert.deepEqual(run(root, T0 + 20 * H), []);
  assert.deepEqual(run(root, T0 + 23 * H), ["warn #5 @alice"]);
});

test("readPulls reads pull.md front matter from the forkmesh/pulls ledger", async () => {
  const urls = [];
  const getJson = async (url) => {
    urls.push(url);
    const u = new URL(url);
    if (u.pathname.endsWith("/tree")) {
      return { status: 200, data: { entries: [{ name: "1", type: "tree" }, { name: "2", type: "tree" }, { name: "x", type: "tree" }, { name: "3", type: "blob" }] } };
    }
    const blobs = {
      ".forkmesh/pulls/1/pull.md": "---\ntitle: blt-pool: fix\nstatus: open\nts: 1790000000000\nauthorName: alice\n---\nbody",
      ".forkmesh/pulls/2/pull.md": { encoding: "base64", content: Buffer.from("---\nstatus: merged\nts: 1790000001000\nauthorName: bob\n---\n").toString("base64") },
    };
    return { status: 200, data: { blobs } };
  };
  const pulls = await S.readPulls(getJson, { url: "https://forge.test/" });
  assert.deepEqual(pulls, [
    { number: 1, author: "alice", status: "open", opened: 1790000000000 },
    { number: 2, author: "bob", status: "merged", opened: 1790000001000 },
  ]);
  assert.match(urls[0], /^https:\/\/forge\.test\/api\/repo\/owasp-blt\/BLT\/tree\?path=.forkmesh%2Fpulls&ref=forkmesh%2Fpulls$/);
  assert.equal(new URL(urls[1]).searchParams.getAll("path").length, 2);
});

test("readPulls: no ledger means no pull requests; any other error stops the run", async () => {
  assert.deepEqual(await S.readPulls(async () => ({ status: 404, data: { error: "not_found" } })), []);
  await assert.rejects(S.readPulls(async () => ({ status: 502, data: null })), /answered 502/);
});

test("execute unassigns before replying and stops on an instance without the endpoint", async () => {
  const calls = [];
  const client = {
    changeAssignees: async (n, body) => calls.push(["assignees", n, body]),
    comment: async (n, body) => calls.push(["comment", n, body]),
  };
  const actions = [
    { number: 5, name: "alice", action: "unassign", reply: "@alice bye" },
    { number: 6, name: "bob", action: "warn", reply: "@bob heads up" },
  ];
  const done = await S.execute(actions, { client, log: quiet });
  assert.equal(done.length, 2);
  assert.deepEqual(calls, [
    ["assignees", 5, { remove: ["alice"] }],
    ["comment", 5, "@alice bye"],
    ["comment", 6, "@bob heads up"],
  ]);

  const missing = Object.assign(new Error("404"), { status: 404, body: { error: "not_found" } });
  const replies = [];
  const old = {
    changeAssignees: async () => {
      throw missing;
    },
    missingEndpoint: (e) => e === missing,
    comment: async (n, b) => replies.push(b),
  };
  assert.deepEqual(await S.execute(actions, { client: old, log: quiet }), []);
  assert.deepEqual(replies, [], "no reply claims an unassignment that did not happen");

  const many = Array.from({ length: 12 }, (_, i) => ({ number: i, name: "a", action: "warn", reply: "r" }));
  calls.length = 0;
  assert.equal((await S.execute(many, { client, log: quiet })).length, S.MAX_ACTIONS_PER_RUN);
});
