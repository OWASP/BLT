// node --test blt-pool/forge/
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as M from "./mentor.mjs";
import { commandKey } from "../../blt-action/forge/assign.mjs";

// forkmesh app/src/entry.py MENTION_RE (applied to the lowercased text).
const MENTION_RE = /(?<![A-Za-z0-9._%+-])@([a-z](?:[a-z0-9-]{0,61}[a-z0-9])?)\b/g;
const notified = (text) => [...String(text).toLowerCase().matchAll(MENTION_RE)].map((m) => m[1]);

const POOL = [
  { github_username: "Ana", forge_username: "ana", name: "Ana", specialties: ["python"], max_mentees: 2, timezone: "UTC+1" },
  { github_username: "Ben", forge_username: "Ben", name: "Ben", specialties: ["frontend"], max_mentees: 1 },
  { github_username: "Cy", forge_username: "", name: "Cy", specialties: ["python"], max_mentees: 3 },
];

function record(number, { labels = [], status = "open", comments = [] } = {}) {
  return {
    assignees: [],
    authorName: "someone",
    events: [
      { type: "open", id: `open-${number}`, ts: 1, body: "b" },
      ...comments.map(([id, login, body, verified = true], i) => ({ type: "comment", id, authorName: login, authorVerified: verified, body, ts: 10 + i })),
    ],
    labels,
    number,
    status,
  };
}

function ledger(issues) {
  const root = mkdtempSync(join(tmpdir(), "mentor-"));
  for (const [number, rec, side = "open"] of issues) {
    const dir = join(root, ".forkmesh", "issues", side, String(number));
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, `issue-${number}.json`), JSON.stringify(rec));
  }
  return root;
}

const cmd = (number, id, login, body, verified = true) => ({ number, commentId: id, login, verified, body });
const quiet = () => {};

test("parseCommand finds the three commands at the start of a line only", () => {
  assert.equal(M.parseCommand("/mentor"), "mentor");
  assert.equal(M.parseCommand("Could I get help?\n/Mentor please"), "mentor");
  assert.equal(M.parseCommand("/rematch"), "rematch");
  assert.equal(M.parseCommand("/unmentor."), "unmentor");
  assert.equal(M.parseCommand("/mentor-pause"), null);
  assert.equal(M.parseCommand("/mentors"), null);
  assert.equal(M.parseCommand("please /mentor me"), null);
  assert.equal(M.parseCommand("```\n/mentor\n```"), null);
  assert.equal(M.parseCommand("    /mentor"), null);
  assert.equal(M.parseCommand(undefined), null);
});

test("only mentors with a forge account are reachable", () => {
  assert.deepEqual(M.reachable(POOL).map((m) => m.forge), ["ana", "ben"]);
  assert.deepEqual(M.reachable([{ forge_username: "bad name" }, { forge_username: "$(id)" }]), []);
});

test("selectMentor prefers matching specialties, then the lowest load under the cap", () => {
  assert.equal(M.selectMentor({ mentors: POOL, labels: ["frontend"] }).forge, "ben");
  assert.equal(M.selectMentor({ mentors: POOL, labels: ["docs"] }).forge, "ana");
  // Ben is full (cap 1), so the frontend issue falls back to the open pool.
  assert.equal(M.selectMentor({ mentors: POOL, labels: ["frontend"], loads: new Map([["ben", 1]]) }).forge, "ana");
  assert.equal(M.selectMentor({ mentors: POOL, loads: new Map([["ana", 1]]) }).forge, "ben");
  assert.equal(M.selectMentor({ mentors: POOL, exclude: ["Ana", "ben"] }), null);
  assert.equal(M.selectMentor({ mentors: [] }), null);
});

test("/mentor matches, notifies the mentor and asks for a referral", () => {
  const root = ledger([[5, record(5, { labels: ["python"] })]]);
  const [out] = M.handleCommands({ root, commands: [cmd(5, "c1", "Dee", "/mentor")], mentors: POOL, log: quiet });
  assert.deepEqual(out.match, { mentor: "ana", requester: "dee" });
  assert.deepEqual(notified(out.body).slice(0, 2), ["dee", "ana"]);
  assert.match(out.body, /<!-- blt-mentor-match:ana:dee -->/);
  assert.match(out.body, new RegExp(`<!-- blt-mentor:${commandKey(5, "c1", "Dee")} -->`));
  assert.match(out.body, /https:\/\/pool\.owaspblt\.org\/\?ref=dee#join-mentor/);
  assert.match(out.body, /`\/assign`/);
});

test("the match and the loads are read back from verified bot replies only", () => {
  const forged = M.matchMarker("ben", "eve");
  const rec = record(6, {
    comments: [
      ["c1", "eve", `/mentor ${forged}`],
      ["c2", "owasp-blt-actions", `ok ${M.matchMarker("ana", "dee")}`, false],
    ],
  });
  assert.equal(M.currentMatch(rec), null);
  const matched = record(7, { comments: [["c1", "owasp-blt-actions", `hi ${M.matchMarker("ana", "dee")}`]] });
  assert.deepEqual(M.currentMatch(matched), { mentor: "ana", requester: "dee" });
  const cleared = record(8, { comments: [["c1", "owasp-blt-actions", M.matchMarker("ana", "dee")], ["c2", "owasp-blt-actions", M.clearMarker()]] });
  assert.equal(M.currentMatch(cleared), null);
  const root = ledger([[6, rec], [7, matched], [8, cleared], [9, record(9, { status: "closed", comments: [["c1", "owasp-blt-actions", M.matchMarker("ben", "x")]] }), "closed"]]);
  assert.deepEqual([...M.mentorLoads(root)], [["ana", 1]]);
});

test("a second /mentor in the same run sees the first match", () => {
  const root = ledger([[5, record(5)], [6, record(6)]]);
  const out = M.handleCommands({
    root,
    commands: [cmd(5, "c1", "dee", "/mentor"), cmd(5, "c2", "fay", "/mentor"), cmd(6, "c3", "fay", "/mentor")],
    mentors: POOL,
    log: quiet,
  });
  assert.equal(out[0].match.mentor, "ana");
  assert.equal(out[1].match, undefined);
  assert.match(out[1].body, /already has a mentor: @ana/);
  // Ana now has one of two slots and Ben none of one, so #6 goes to Ben.
  assert.equal(out[2].match.mentor, "ben");
});

test("/rematch moves to another mentor; /unmentor clears; strangers are refused", () => {
  const rec = record(5, { comments: [["c0", "owasp-blt-actions", M.matchMarker("ana", "dee")]] });
  const root = ledger([[5, rec]]);
  const [stranger] = M.handleCommands({ root, commands: [cmd(5, "c1", "zed", "/unmentor")], mentors: POOL, log: quiet });
  assert.equal(stranger.match, undefined);
  assert.match(stranger.body, /only the person who asked/);
  const [re] = M.handleCommands({ root, commands: [cmd(5, "c2", "ana", "/rematch")], mentors: POOL, loads: new Map([["ana", 1]]), log: quiet });
  assert.deepEqual(re.match, { mentor: "ben", requester: "dee" });
  assert.deepEqual(notified(re.body).slice(0, 3), ["ana", "dee", "ben"]);
  const [off] = M.handleCommands({ root, commands: [cmd(5, "c3", "dee", "/unmentor")], mentors: POOL, log: quiet });
  assert.equal(off.match, null);
  assert.match(off.body, /<!-- blt-mentor-clear -->/);
});

test("no reachable mentor: no match, and the reply asks mentors to link and readers to refer", () => {
  const root = ledger([[5, record(5)]]);
  const [out] = M.handleCommands({ root, commands: [cmd(5, "c1", "dee", "/mentor")], mentors: [POOL[2]], log: quiet });
  assert.equal(out.match, undefined);
  assert.match(out.body, /no mentor with a git\.owaspblt\.org account has room/);
  assert.match(out.body, /\?ref=dee#join-mentor/);
  assert.deepEqual(notified(out.body), ["dee"]);
});

test("security issues, closed issues, unverified authors and handled comments", () => {
  const root = ledger([
    [5, record(5, { labels: ["Security"] })],
    [6, record(6, { status: "closed" }), "closed"],
    [7, record(7, { comments: [["c9", "owasp-blt-actions", `done ${`<!-- blt-mentor:${commandKey(7, "c1", "dee")} -->`}`]] })],
  ]);
  const out = M.handleCommands({
    root,
    commands: [cmd(5, "c1", "dee", "/mentor"), cmd(6, "c1", "dee", "/mentor"), cmd(5, "c2", "eve", "/mentor", false), cmd(7, "c1", "dee", "/mentor"), cmd(5, "c3", "owasp-blt-actions", "/mentor")],
    mentors: POOL,
    log: quiet,
  });
  assert.equal(out.length, 3);
  assert.match(out[0].body, /handled by the BLT maintainers/);
  assert.match(out[1].body, /closed/);
  assert.match(out[2].body, /need a signed-in account/);
  assert.ok(out.every((o) => o.match === undefined));
});
