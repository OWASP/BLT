// `/mentor`, `/rematch` and `/unmentor` for BLT forge issues (git.owaspblt.org/BLT): the mentor pool
// at pool.owaspblt.org, answered on the forge. Run by .forkmesh/blt-pool--mentor.yml.
//
//   node blt-pool/forge/mentor.mjs                 issue_comment event, or workflow_dispatch input `issue`
//   node blt-pool/forge/mentor.mjs --issue 27      process the mentor commands already in #27's ledger
//   ... --dry-run                                  print what would happen; post nothing
//
// The pool comes from GET <BLT_POOL_URL>/api/mentors (published mentors only). A mentor is matched only
// when they gave a git.owaspblt.org account (`forge_username`), so the `@name` in the reply reaches them
// as a forge notification. Matching prefers mentors whose specialties match the issue labels, then the
// fewest open mentored issues (under their max_mentees cap), then the name.
//
// The match lives in the ledger: the reply carries `<!-- blt-mentor-match:<mentor>:<requester> -->` or
// `<!-- blt-mentor-clear -->`, and only verified bot comments count, so the current mentor of every open
// issue (and so each mentor's load) is read back from .forkmesh/issues. `<!-- blt-mentor:<key> -->`
// marks a command answered, keyed like blt-action/forge/assign.mjs, so reruns do nothing twice. The
// `mentor-assigned` label follows the match (best effort). Every reply asks the reader to refer a mentor.
import * as forge from "../../scripts/actions/forge.mjs";
import {
  accountName,
  commandKey,
  isBot,
  isOpen,
  ledgerComments,
  loadIssue,
  mention,
  verifiedName,
} from "../../blt-action/forge/assign.mjs";
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";

export const POOL_URL = "https://pool.owaspblt.org";
export const MENTOR_LABEL = "mentor-assigned";
// Issues with these labels go to the maintainers, not the pool (as the GitHub App's SECURITY_BYPASS_LABELS).
export const SECURITY_LABELS = new Set(["security", "vulnerability", "security-sensitive", "private-security"]);
export const MAX_COMMANDS_PER_RUN = 10;
const MAX_SCAN_BYTES = 64 * 1024;
const MAX_SCAN_LINES = 200;
const MARK_RE = /<!-- blt-mentor-(match|clear)(?::([a-z0-9-]+):([a-z0-9-]*))? -->/g;

// ---- parsing -----------------------------------------------------------------------------------

/** "mentor" | "rematch" | "unmentor" | null: the first such command at the start of a line, outside code. */
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
    if (raw.startsWith("    ") || raw.startsWith("\t")) continue;
    const match = line.match(/^\/(mentor|rematch|unmentor)(?=$|\s|[.!,;:])/i);
    if (match) return match[1].toLowerCase();
  }
  return null;
}

export const replyMarker = (key) => `<!-- blt-mentor:${key} -->`;
export const matchMarker = (mentor, requester) => `<!-- blt-mentor-match:${mentor}:${requester} -->`;
export const clearMarker = () => "<!-- blt-mentor-clear -->";
export const referralLink = (name, base = POOL_URL) =>
  `${base}/?ref=${encodeURIComponent(name)}#join-mentor`;

const fromBot = (c) => c.authorVerified === true && isBot(c.authorName);

/** The issue's current match {mentor, requester}, or null, from the verified bot replies in its ledger. */
export function currentMatch(record) {
  let match = null;
  for (const c of ledgerComments(record)) {
    if (!fromBot(c)) continue;
    for (const m of String(c.body || "").matchAll(MARK_RE)) {
      match = m[1] === "match" && m[2] ? { mentor: m[2], requester: m[3] || "" } : null;
    }
  }
  return match;
}

export const replied = (record, key) =>
  ledgerComments(record).some((c) => fromBot(c) && String(c.body || "").includes(replyMarker(key)));

/** {forge account: open issues it currently mentors} over the open issues in the ledger. */
export function mentorLoads(root) {
  const loads = new Map();
  const dir = join(root, ".forkmesh", "issues", "open");
  if (!existsSync(dir)) return loads;
  for (const entry of readdirSync(dir)) {
    if (!/^\d+$/.test(entry)) continue;
    const issue = loadIssue(root, Number(entry));
    const match = issue && isOpen(issue) ? currentMatch(issue.record) : null;
    if (match) loads.set(match.mentor, (loads.get(match.mentor) || 0) + 1);
  }
  return loads;
}

// ---- matching ----------------------------------------------------------------------------------

/** Pool entries that can be matched on the forge: a valid forge account, deduplicated. */
export function reachable(mentors) {
  const seen = new Set();
  const out = [];
  for (const m of mentors || []) {
    const name = accountName(m?.forge_username);
    if (!name || seen.has(name)) continue;
    seen.add(name);
    out.push({ ...m, forge: name, specialties: (m.specialties || []).map((s) => String(s).toLowerCase()) });
  }
  return out;
}

/** The mentor to match, or null: specialty match first, then the lowest load under the cap, then name. */
export function selectMentor({ mentors, labels = [], loads = new Map(), exclude = [] }) {
  const skip = new Set(exclude.map((n) => String(n).toLowerCase()));
  const open = reachable(mentors).filter(
    (m) => !skip.has(m.forge) && (loads.get(m.forge) || 0) < Math.max(1, Number(m.max_mentees) || 3),
  );
  if (!open.length) return null;
  const wanted = new Set(labels.map((l) => String(l).toLowerCase()));
  const matching = open.filter((m) => m.specialties.some((s) => wanted.has(s)));
  const pool = matching.length ? matching : open;
  pool.sort((a, b) => (loads.get(a.forge) || 0) - (loads.get(b.forge) || 0) || a.forge.localeCompare(b.forge));
  return pool[0];
}

// ---- replies -----------------------------------------------------------------------------------

function referralNudge(name, base) {
  return (
    `\n\n---\nKnow someone who would make a good mentor (a maintainer, teacher, coworker or senior student)? ` +
    `Send them your referral link: ${referralLink(name, base)}. You are credited on the pool's referral leaderboard when they join.`
  );
}

function noMentorReply(who, base, rematch) {
  return (
    `${who} ${rematch ? "there is no other mentor" : "no mentor"} with a git.owaspblt.org account has room right now, ` +
    `so nobody was matched. Ask again later, or ask in the issue for help in the meantime. ` +
    `Mentors: add your git.owaspblt.org account to your profile at ${base} so requests reach you here.`
  );
}

function matchedReply({ who, mentor, rematch }) {
  const m = mention(mentor.forge);
  const skills = mentor.specialties.length ? ` (specialties: ${mentor.specialties.join(", ")})` : "";
  const tz = mentor.timezone ? `, timezone ${mentor.timezone}` : "";
  return (
    `${who} ${rematch ? "you have a new mentor" : "you're matched with a mentor"}: ${m}${skills}${tz}.\n\n` +
    `${m}: please say hello and help ${who} through this issue. Comment \`/rematch\` to hand it to another mentor.\n\n` +
    `${who}: ask your questions right here. \`/rematch\` asks for a different mentor and \`/unmentor\` cancels. ` +
    `Asking for a mentor does not assign you: comment \`/assign\` when you start working on it.`
  );
}

/**
 * Decide one command against the issue as it is now.
 * Returns {reply, match: undefined | null | {mentor, requester}} (undefined: the match is unchanged).
 */
export function decide({ command, name, issue, mentors, loads, base = POOL_URL }) {
  const who = mention(name);
  const labels = (issue.record.labels || []).map(String);
  const current = currentMatch(issue.record);
  const nudge = referralNudge(name, base);
  if (!isOpen(issue)) return { reply: `${who} this issue is closed, so mentor requests no longer apply.` };
  if (command === "mentor") {
    if (current) {
      return {
        reply: `${who} this issue already has a mentor: ${mention(current.mentor)}. Comment \`/rematch\` for a different one.`,
      };
    }
    if (labels.some((l) => SECURITY_LABELS.has(l.toLowerCase()))) {
      return {
        reply: `${who} security issues are handled by the BLT maintainers rather than the mentor pool, so no mentor was matched. A maintainer will follow up here.`,
      };
    }
    const mentor = selectMentor({ mentors, labels, loads, exclude: [name] });
    if (!mentor) return { reply: noMentorReply(who, base, false) + nudge };
    return { match: { mentor: mentor.forge, requester: name }, mentor, reply: matchedReply({ who, mentor }) + nudge };
  }
  const allowed = current && (name === current.mentor || name === current.requester);
  if (!current) return { reply: `${who} this issue has no mentor. Comment \`/mentor\` to ask for one.` };
  if (!allowed) {
    return {
      reply: `${who} only the person who asked for the mentor (${mention(current.requester)}) or the mentor (${mention(current.mentor)}) can change this match.`,
    };
  }
  if (command === "unmentor") {
    return {
      match: null,
      reply: `${who} the mentor match is cancelled. Thank you, ${mention(current.mentor)}! Comment \`/mentor\` to ask again.`,
    };
  }
  // rematch: the previous mentor is skipped; the original requester stays the mentee.
  const requester = current.requester || name;
  const mentor = selectMentor({ mentors, labels, loads, exclude: [current.mentor, requester] });
  if (!mentor) {
    return { reply: `${noMentorReply(who, base, true)} ${mention(current.mentor)} stays matched for now.${nudge}` };
  }
  return {
    match: { mentor: mentor.forge, requester },
    mentor,
    reply: `Thank you, ${mention(current.mentor)}! ` + matchedReply({ who: mention(requester), mentor, rematch: true }) + nudge,
  };
}

// ---- commands ------------------------------------------------------------------------------------

/** Commands to handle: [{number, commentId, login, verified, body}], at most MAX_COMMANDS_PER_RUN. */
export function collectCommands({ root, event, name, issueOverride }) {
  const dispatchIssue = Number(issueOverride || process.env.INPUT_ISSUE || event?.inputs?.issue || 0);
  if (name === "workflow_dispatch" || issueOverride) {
    if (!Number.isInteger(dispatchIssue) || dispatchIssue <= 0) throw new Error("workflow_dispatch needs the issue number");
    const issue = loadIssue(root, dispatchIssue);
    if (!issue) throw new Error(`issue #${dispatchIssue} has no ledger file`);
    return ledgerComments(issue.record)
      .map((c) => ({
        number: dispatchIssue,
        commentId: String(c.id),
        login: c.authorName || c.author || "",
        author: c.author || "",
        verified: c.authorVerified === true && Boolean(c.authorName),
        body: c.body,
      }))
      .filter((c) => parseCommand(c.body))
      .slice(0, MAX_COMMANDS_PER_RUN);
  }
  if (name !== "issue_comment" || event?.action !== "created") return [];
  const comment = event.comment || {};
  const number = Number(event.issue?.number || 0);
  if (!number || event.issue?.pull_request) return [];
  return [
    {
      number,
      commentId: String(comment.id || ""),
      login: comment.user?.login || "",
      author: "",
      verified: comment.user?.verified === true,
      body: comment.body,
    },
  ];
}

/**
 * Decide every command. Replies are appended to the in-memory ledger as verified bot comments, so later
 * commands in the same run (and the loads) see earlier matches. Returns [{number, body, match, mentor}].
 */
export function handleCommands({ root, commands, mentors, base = POOL_URL, loads = mentorLoads(root), log = console.log }) {
  const issues = new Map();
  const load = (n) => {
    if (!issues.has(n)) issues.set(n, loadIssue(root, n));
    return issues.get(n);
  };
  const out = [];
  for (const c of commands) {
    const command = parseCommand(c.body);
    if (!command) continue;
    const label = `#${c.number} comment ${c.commentId || "?"} by ${JSON.stringify(String(c.login).slice(0, 80))}`;
    if (isBot(c.login) || !c.commentId) {
      log(`${label}: ignored`);
      continue;
    }
    const issue = load(c.number);
    if (!issue) {
      log(`${label}: issue has no ledger file yet, skipped`);
      continue;
    }
    const key = commandKey(c.number, c.commentId, c.login);
    if (replied(issue.record, key)) {
      log(`${label}: /${command} already handled`);
      continue;
    }
    const name = verifiedName(c);
    let decision;
    if (!name) {
      decision = { reply: `Commands like \`/${command}\` need a signed-in account: sign in on git.owaspblt.org and comment again.` };
    } else {
      const before = currentMatch(issue.record);
      decision = decide({ command, name, issue, mentors, loads, base });
      if (decision.match !== undefined) {
        if (before) loads.set(before.mentor, Math.max(0, (loads.get(before.mentor) || 1) - 1));
        if (decision.match) loads.set(decision.match.mentor, (loads.get(decision.match.mentor) || 0) + 1);
      }
    }
    const state =
      decision.match === undefined ? "" : decision.match ? matchMarker(decision.match.mentor, decision.match.requester) : clearMarker();
    const body = `${decision.reply} ${state}${state ? " " : ""}${replyMarker(key)}`;
    issue.record.events = [
      ...(issue.record.events || []),
      { type: "comment", id: `pending-${key}`, authorName: "owasp-blt-actions", authorVerified: true, body, ts: Date.now() },
    ];
    log(`${label}: /${command} -> ${decision.match === undefined ? "no change" : decision.match ? `@${decision.match.mentor}` : "cleared"}`);
    out.push({ number: c.number, body, match: decision.match });
  }
  return out;
}

export async function fetchMentors(base = POOL_URL) {
  const response = await fetch(`${base.replace(/\/+$/, "")}/api/mentors`, {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error(`GET ${base}/api/mentors: HTTP ${response.status}`);
  const data = await response.json();
  return Array.isArray(data?.mentors) ? data.mentors : [];
}

function arg(name) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

async function main() {
  const root = forge.ROOT;
  const dryRun = process.argv.includes("--dry-run");
  const base = (process.env.BLT_POOL_URL || POOL_URL).replace(/\/+$/, "");
  const commands = collectCommands({ root, event: forge.readEvent(), name: forge.eventName(), issueOverride: arg("--issue") });
  if (!commands.length) {
    console.log("no /mentor, /rematch or /unmentor command to handle");
    return;
  }
  let mentors = [];
  try {
    mentors = await fetchMentors(base);
  } catch (error) {
    // Still answer: with an empty pool every request gets the "no mentor has room" reply.
    console.error(`could not read the mentor pool: ${error.message}`);
  }
  console.log(`${reachable(mentors).length} of ${mentors.length} published mentors have a git.owaspblt.org account`);
  const replies = handleCommands({ root, commands, mentors, base });
  for (const reply of replies) {
    if (dryRun) {
      console.log(`would reply on #${reply.number}: ${reply.body}`);
      continue;
    }
    await forge.comment(reply.number, reply.body);
    console.log(`replied on #${reply.number}`);
    if (reply.match === undefined) continue;
    try {
      await forge.changeLabels(reply.number, reply.match ? { add: [MENTOR_LABEL] } : { remove: [MENTOR_LABEL] });
    } catch (error) {
      console.error(`#${reply.number}: could not update the ${MENTOR_LABEL} label: ${error.message}`);
    }
  }
}

if (import.meta.url === `file://${process.argv[1]}`) forge.run(main);
