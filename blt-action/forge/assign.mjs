// `/assign` and `/unassign` for BLT forge issues (git.owaspblt.org/BLT), the forge port of
// BLT-Action's comment commands (blt-action/src/index.js). Run by .forkmesh/blt-action--assign.yml.
//
//   node blt-action/forge/assign.mjs                 issue_comment event, or workflow_dispatch input `issue`
//   node blt-action/forge/assign.mjs --issue 27      process the /assign and /unassign comments in #27's ledger
//   ... --apply-only                                 change the ledger files only (no commit, no reply)
//   ... --dry-run                                    print what would happen; write nothing
//
// The assignment is a signed `assignees` event (forkmesh-issue-event-v2, the same event the desktop
// writes for an owner's assignee change) appended to .forkmesh/issues/open/<n>/issue-<n>.json together
// with the record's `assignees`, signed by blt-tasks[bot] (seed: secret BLT_TASKS_SEED) and pushed with
// scripts/actions/commit-back.sh --rebuild. The reply is posted through the job API
// (scripts/actions/forge.mjs comment), because only the issue inbox raises notifications: the
// `@user` at the start of the reply is what notifies the commenter.
//
// The comment is read from the event JSON and never reaches a shell. Each command is keyed by
// sha256(issue, comment id, login): the ledger event id `blt-assign-<key>` marks it applied and a
// `<!-- blt-assign:<key> -->` marker in the reply marks it answered, so reruns do nothing twice.
import { createHash, createPrivateKey, createPublicKey, sign as edSign, generateKeyPairSync } from "node:crypto";
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import * as forge from "../../scripts/actions/forge.mjs";

export const BOT_NAME = "blt-tasks[bot]";
export const REPO_KEY = "owasp-blt/blt"; // forkmesh-issue-event-v2 signing key: lower(owner)/lower(repo)
// BLT-Action blocks a new assignment while the user holds another open issue without an open pull
// request, i.e. one unfinished issue at a time.
export const MAX_OPEN_ASSIGNMENTS = 1;
export const PR_DAYS = 7;
export const MAX_COMMANDS_PER_RUN = 10;
// Spam guards. One refusal reply per person per day: further refused /assign comments get no reply.
// More than COOLDOWN_MAX_ATTEMPTS /assign comments within COOLDOWN_WINDOW_MS puts the person on a
// COOLDOWN_MS pause from /assign, announced once.
export const REFUSAL_QUIET_MS = 24 * 60 * 60 * 1000;
export const COOLDOWN_WINDOW_MS = 60 * 60 * 1000;
export const COOLDOWN_MAX_ATTEMPTS = 3;
export const COOLDOWN_MS = 24 * 60 * 60 * 1000;
const MAX_SCAN_BYTES = 64 * 1024;
const MAX_SCAN_LINES = 200;
// An account name, as the forge's NODE_NAME_RE; only these turn `@name` into a notification
// (MENTION_RE in forkmesh app/src/entry.py).
const ACCOUNT_RE = /^[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$/;
const PKCS8_ED25519 = Buffer.from("302e020100300506032b657004220420", "hex");

// ---- parsing -----------------------------------------------------------------------------------

/** "assign" | "unassign" | null: the first command at the start of a line, outside code and quotes. */
export function parseCommand(body) {
  const text = String(body ?? "").slice(0, MAX_SCAN_BYTES);
  let fence = "";
  for (const raw of text.split(/\r?\n/).slice(0, MAX_SCAN_LINES)) {
    const line = raw.trim();
    const marker = line.match(/^(```|~~~)/);
    if (fence) {
      if (marker && line.startsWith(fence)) fence = "";
      continue;
    }
    if (marker) {
      fence = marker[1];
      continue;
    }
    if (raw.startsWith("    ") || raw.startsWith("\t")) continue; // indented code block
    const match = line.match(/^\/(assign|unassign)(?=$|\s|[.!,;:])/i);
    if (match) return match[1].toLowerCase();
  }
  return null;
}

export function accountName(login) {
  const name = String(login ?? "").trim().toLowerCase();
  return ACCOUNT_RE.test(name) ? name : "";
}

export function isBot(login) {
  const name = String(login ?? "").trim().toLowerCase();
  return !name || name.endsWith("[bot]") || name.endsWith("-actions") || name === BOT_NAME;
}

export const mention = (name) => `@${name}`;

export function commandKey(number, commentId, login) {
  return createHash("sha256")
    .update(`${Number(number)}\n${commentId}\n${String(login).trim().toLowerCase()}`)
    .digest("hex")
    .slice(0, 20);
}

const sameName = (a, b) => String(a).trim().toLowerCase() === String(b).trim().toLowerCase();

// ---- ledger --------------------------------------------------------------------------------------

export function issuePath(root, number) {
  for (const side of ["open", "closed"]) {
    const file = join(root, ".forkmesh", "issues", side, String(number), `issue-${number}.json`);
    if (existsSync(file)) return { file, side };
  }
  return null;
}

export function loadIssue(root, number) {
  const found = issuePath(root, number);
  if (!found) return null;
  const record = JSON.parse(readFileSync(found.file, "utf8"));
  return { ...found, record };
}

export function isOpen(issue) {
  return issue.side === "open" && String(issue.record.status || "open") === "open";
}

/** Other open issues assigned to `name`, oldest number first. */
export function openAssignments(root, name, except) {
  const dir = join(root, ".forkmesh", "issues", "open");
  if (!existsSync(dir)) return [];
  const found = [];
  for (const entry of readdirNumbers(dir)) {
    if (entry === Number(except)) continue;
    const issue = loadIssue(root, entry);
    if (issue && isOpen(issue) && (issue.record.assignees || []).some((a) => sameName(a, name))) found.push(entry);
  }
  return found;
}

function readdirNumbers(dir) {
  return readdirSync(dir).filter((n) => /^\d+$/.test(n)).map(Number).sort((a, b) => a - b);
}

/** Comments in the ledger (not deleted), oldest first. */
export function ledgerComments(record) {
  const events = Array.isArray(record.events) ? record.events : [];
  const deleted = new Set(events.filter((e) => e?.type === "delete" && e.target && e.target !== "self").map((e) => e.target));
  return events
    .filter((e) => e?.type === "comment" && e.id && !deleted.has(e.id))
    .sort((a, b) => Number(a.ts || 0) - Number(b.ts || 0));
}

export const refusalMarker = (name) => `<!-- blt-assign-refused:${String(name).toLowerCase()} -->`;
export const cooldownMarker = (name) => `<!-- blt-assign-cooldown:${String(name).toLowerCase()} -->`;
const toMs = (ts) => {
  const n = Number(ts || 0);
  return n > 1e12 ? n : n * 1000;
};

/**
 * What `name` has been doing with /assign across open issues: the times of their /assign comments
 * and of the last refusal and cooldown replies addressed to them (found by marker).
 */
export function userActivity(root, name) {
  const activity = { attempts: [], lastRefusal: 0, lastCooldown: 0 };
  const dir = join(root, ".forkmesh", "issues", "open");
  if (!name || !existsSync(dir)) return activity;
  const refused = refusalMarker(name);
  const cooled = cooldownMarker(name);
  for (const number of readdirNumbers(dir)) {
    const issue = loadIssue(root, number);
    if (!issue) continue;
    for (const c of ledgerComments(issue.record)) {
      const body = String(c.body || "");
      const ts = toMs(c.ts);
      if (sameName(c.authorName || "", name) && parseCommand(body) === "assign") activity.attempts.push(ts);
      if (body.includes(refused)) activity.lastRefusal = Math.max(activity.lastRefusal, ts);
      if (body.includes(cooled)) activity.lastCooldown = Math.max(activity.lastCooldown, ts);
    }
  }
  return activity;
}

/**
 * Apply the spam guards to a decision for /assign. `activity` comes from userActivity; `run` holds
 * replies already decided earlier in this run ({refused: Set, cooled: Set}).
 */
export function guard(decision, { command, name, activity, now = Date.now(), run }) {
  if (command !== "assign" || !activity || !name) return decision;
  const key = String(name).toLowerCase();
  const recent = activity.attempts.filter((t) => now - t <= COOLDOWN_WINDOW_MS).length;
  const cooling = (activity.lastCooldown && now - activity.lastCooldown < COOLDOWN_MS) || run?.cooled?.has(key);
  if (cooling || recent > COOLDOWN_MAX_ATTEMPTS) {
    if (cooling) return { change: null, reply: "" };
    run?.cooled?.add(key);
    return {
      change: null,
      reply:
        `${mention(name)} that's a lot of \`/assign\` requests in a short time, so \`/assign\` is paused for you for ` +
        `24 hours. Please focus on one issue and open a pull request for it. ${cooldownMarker(name)}`,
    };
  }
  if (decision.change || !decision.reply) return decision;
  const quiet = (activity.lastRefusal && now - activity.lastRefusal < REFUSAL_QUIET_MS) || run?.refused?.has(key);
  if (quiet) return { change: null, reply: "" };
  run?.refused?.add(key);
  return { change: null, reply: `${decision.reply} ${refusalMarker(name)}` };
}

export const appliedEvent = (record, key) => (record.events || []).find((e) => e?.id === `blt-assign-${key}`);
export const replyMarker = (key) => `<!-- blt-assign:${key} -->`;
export const replied = (record, key) =>
  (record.events || []).some((e) => e?.type === "comment" && String(e.body || "").includes(replyMarker(key)));

// ---- rules ---------------------------------------------------------------------------------------

/**
 * Decide one command against the current ledger.
 * Returns {change: null | {assignees: [...]}, reply: "<text without marker>"}; reply "" means stay silent.
 */
export function decide({ command, name, issue, others = [] }) {
  const who = mention(name);
  const assignees = (issue.record.assignees || []).map(String);
  const mine = assignees.some((a) => sameName(a, name));
  if (command === "assign") {
    if (!isOpen(issue)) return { change: null, reply: `${who} this issue is closed, so it can't be assigned.` };
    if (mine) return { change: null, reply: `${who} you are already assigned to this issue.` };
    if (assignees.length) {
      const list = assignees.map((a) => (accountName(a) ? mention(accountName(a)) : a)).join(", ");
      return { change: null, reply: `${who} this issue is already assigned to ${list}. Please pick another issue.` };
    }
    if (others.length >= MAX_OPEN_ASSIGNMENTS) {
      const list = others.map((n) => `#${n}`).join(", ");
      return {
        change: null,
        reply:
          `${who} you can't be assigned to this issue because you are already assigned to ${list}. ` +
          `Please open a pull request for it, or comment \`/unassign\` there, before taking another issue.`,
      };
    }
    return {
      change: { assignees: [name] },
      reply:
        `${who} you're assigned to this issue. Please open a pull request for it within ${PR_DAYS} days. ` +
        `If you stop working on it, comment \`/unassign\` so someone else can pick it up.`,
    };
  }
  if (command === "unassign") {
    if (!mine) return { change: null, reply: `${who} you are not assigned to this issue, so there was nothing to unassign.` };
    return {
      change: { assignees: assignees.filter((a) => !sameName(a, name)) },
      reply: `${who} you're unassigned from this issue. It's open for others now; comment \`/assign\` to take it again.`,
    };
  }
  return { change: null, reply: "" };
}

/** The reply for a command the ledger already shows as applied. */
export function appliedReply(event, name, issue) {
  const assigned = (event.assignees || []).some((a) => sameName(a, name));
  return decide({
    command: assigned ? "assign" : "unassign",
    name,
    issue: { side: "open", record: { status: "open", assignees: assigned ? [] : [name] } },
  }).reply;
}

// ---- signing -------------------------------------------------------------------------------------

export function parseSeed(text) {
  const value = String(text ?? "").trim();
  const bytes = /^[0-9a-fA-F]{64}$/.test(value) ? Buffer.from(value, "hex") : Buffer.from(value, "base64url");
  if (bytes.length !== 32) throw new Error("the signing seed must be 32 bytes (base64url or 64 hex characters)");
  return bytes;
}

export function makeSigner(seed, { repoKey = REPO_KEY, authorName = BOT_NAME } = {}) {
  const key = createPrivateKey({ key: Buffer.concat([PKCS8_ED25519, seed]), format: "der", type: "pkcs8" });
  const author = createPublicKey(key).export({ format: "jwk" }).x;
  return {
    author,
    authorName,
    /** Sign an issue event the way forkmesh app/src/events.py verify_issue_event checks it. */
    sign(number, event) {
      const full = { ...event, author, authorName };
      const message =
        `forkmesh-issue-event-v2\n${repoKey}\n${full.type}\n${Number(number)}\n${author}\n${full.ts}\n` +
        createHash("sha256").update(eventContent(full)).digest("hex");
      full.sig = edSign(null, Buffer.from(message, "utf8"), key).toString("base64url");
      return Object.fromEntries(Object.entries(full).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
    },
  };
}

export function throwawaySigner() {
  const { privateKey } = generateKeyPairSync("ed25519");
  const seed = privateKey.export({ format: "der", type: "pkcs8" }).subarray(-32);
  return makeSigner(seed);
}

/** events.py issue_event_content, for the event types written here. */
export function eventContent(event) {
  if (event.type === "assignees") return (event.assignees || []).join(",");
  if (event.type === "comment") return `${event.body || ""}\u0000${(event.attachments || []).join(",")}`;
  throw new Error(`unsupported event type ${event.type}`);
}

export function applyChange(issue, { key, change, signer, now }) {
  const record = issue.record;
  const ts = Math.max(Number(now), Number(record.updatedAt || 0) + 1);
  const event = signer.sign(record.number, { id: `blt-assign-${key}`, type: "assignees", assignees: change.assignees, ts });
  record.events = [...(record.events || []), event];
  record.assignees = [...change.assignees];
  record.updatedAt = ts;
  return event;
}

export function writeIssue(issue) {
  writeFileSync(issue.file, `${JSON.stringify(issue.record, null, 4)}\n`);
}

// ---- commands ------------------------------------------------------------------------------------

/** Commands to handle: [{number, commentId, login, body}], at most MAX_COMMANDS_PER_RUN. */
export function collectCommands({ root, event, name, issueOverride }) {
  const dispatchIssue = Number(issueOverride || process.env.INPUT_ISSUE || event?.inputs?.issue || 0);
  if (name === "workflow_dispatch" || issueOverride) {
    if (!Number.isInteger(dispatchIssue) || dispatchIssue <= 0) throw new Error("workflow_dispatch needs the issue number");
    const issue = loadIssue(root, dispatchIssue);
    if (!issue) throw new Error(`issue #${dispatchIssue} has no ledger file`);
    return ledgerComments(issue.record)
      .map((c) => ({ number: dispatchIssue, commentId: String(c.id), login: c.authorName || c.author || "", author: c.author || "", body: c.body }))
      .filter((c) => parseCommand(c.body))
      .slice(0, MAX_COMMANDS_PER_RUN);
  }
  if (name !== "issue_comment" || event?.action !== "created") return [];
  const comment = event.comment || {};
  const number = Number(event.issue?.number || 0);
  if (!number || event.issue?.pull_request) return [];
  return [{ number, commentId: String(comment.id || ""), login: comment.user?.login || "", author: "", body: comment.body }];
}

/**
 * Apply every collected command to the ledger files. Returns [{number, key, name, command}] for the
 * commands that still need a reply, and the files it changed.
 */
export function applyCommands({ root, commands, signer, now = Date.now(), dryRun = false, log = console.log }) {
  const pending = [];
  const run = { refused: new Set(), cooled: new Set() };
  const changed = new Set();
  for (const c of commands) {
    const command = parseCommand(c.body);
    const label = `#${c.number} comment ${c.commentId || "?"} by ${JSON.stringify(String(c.login).slice(0, 80))}`;
    if (!command) continue;
    if (isBot(c.login)) {
      log(`${label}: ignored (bot)`);
      continue;
    }
    if (!c.commentId) {
      log(`${label}: ignored (no comment id to deduplicate on)`);
      continue;
    }
    const issue = loadIssue(root, c.number);
    if (!issue) {
      log(`${label}: issue has no ledger file yet, skipped`);
      continue;
    }
    const name = accountName(c.login);
    const key = commandKey(c.number, c.commentId, c.login);
    if (replied(issue.record, key)) {
      log(`${label}: /${command} already handled`);
      continue;
    }
    const entry = { number: c.number, key, name, command, login: String(c.login) };
    if (!name || name === String(c.author || "").toLowerCase()) {
      log(`${label}: /${command} from a comment without an account name`);
      pending.push(entry);
      continue;
    }
    if (appliedEvent(issue.record, key)) {
      log(`${label}: /${command} already applied, reply pending`);
      pending.push(entry);
      continue;
    }
    const decision = guard(
      decide({ command, name, issue, others: command === "assign" ? openAssignments(root, name, c.number) : [] }),
      { command, name, activity: command === "assign" ? userActivity(root, name) : null, now, run },
    );
    entry.preview = decision.reply;
    entry.decided = decision;
    if (decision.change) {
      if (!signer) throw new Error("BLT_TASKS_SEED is not set, so the assignment cannot be signed");
      applyChange(issue, { key, change: decision.change, signer, now });
      if (!dryRun) writeIssue(issue);
      changed.add(issue.file);
      log(`${label}: /${command} applied, assignees now ${JSON.stringify(issue.record.assignees)}`);
    } else {
      log(`${label}: /${command} refused or nothing to do`);
    }
    pending.push(entry);
  }
  return { pending, changed: [...changed] };
}

/** The reply text (with marker) for a pending command, from the ledger as it is now. */
export function replyFor(root, entry) {
  const marker = replyMarker(entry.key);
  const issue = loadIssue(root, entry.number);
  if (!entry.name) {
    return `Commands like \`/${entry.command}\` need a signed-in account: sign in on git.owaspblt.org and comment again. ${marker}`;
  }
  if (!issue) return "";
  const applied = appliedEvent(issue.record, entry.key);
  if (applied) return `${appliedReply(applied, entry.name, issue)} ${marker}`;
  // The guarded decision from applyCommands (the ledger's reply markers only appear after posting).
  const decision = entry.decided || decide({
    command: entry.command,
    name: entry.name,
    issue,
    others: entry.command === "assign" ? openAssignments(root, entry.name, entry.number) : [],
  });
  // A decision that would still change the ledger was not pushed (e.g. --apply-only): no reply.
  if (decision.change || !decision.reply) return "";
  return `${decision.reply} ${marker}`;
}

export function loadSigner(env = process.env) {
  let text = env.BLT_TASKS_SEED || "";
  if (!text && env.BLT_TASKS_SEED_FILE) text = readFileSync(env.BLT_TASKS_SEED_FILE, "utf8");
  if (!text.trim()) return null;
  return makeSigner(parseSeed(text), { repoKey: env.BLT_ASSIGN_REPO_KEY || REPO_KEY });
}

function arg(name) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

async function main() {
  const root = forge.ROOT;
  const dryRun = process.argv.includes("--dry-run");
  const applyOnly = process.argv.includes("--apply-only");
  const issueOverride = arg("--issue");
  const commands = collectCommands({ root, event: forge.readEvent(), name: forge.eventName(), issueOverride });
  if (!commands.length) {
    console.log("no /assign or /unassign command to handle");
    return;
  }
  const signer = loadSigner() || (dryRun ? throwawaySigner() : null);
  const { pending, changed } = applyCommands({ root, commands, signer, dryRun });
  if (dryRun) {
    for (const entry of pending) {
      console.log(`would reply on #${entry.number}: ${entry.preview ?? replyFor(root, entry)}`);
    }
    return;
  }
  if (applyOnly) return;
  if (changed.length) {
    const numbers = [...new Set(pending.map((p) => `#${p.number}`))].join(", ");
    forge.commitBack({
      cwd: root,
      message: `blt-action: /assign and /unassign on ${numbers}`,
      paths: [".forkmesh/issues"],
      rebuild: "node blt-action/forge/assign.mjs --apply-only",
    });
  }
  for (const entry of pending) {
    const body = replyFor(root, entry);
    if (!body) continue;
    await forge.comment(entry.number, body);
    console.log(`replied on #${entry.number}`);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) forge.run(main);
