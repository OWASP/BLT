// Releases stale `/assign` claims on BLT forge issues (git.owaspblt.org/BLT). Run daily by
// .forkmesh/blt-action--unassign-stale.yml. This is the forge port of the stale-assignment
// unassign that BLT-Action (blt-action/src/index.js) and BLT-Pool's 2-hourly GitHub sweep did; BLT-Pool
// no longer handles /assign at all (issue #38).
//
//   node blt-action/forge/stale.mjs              warn, then unassign, through the job API
//   node blt-action/forge/stale.mjs --dry-run    print what would happen; change nothing
//
// A claim is stale when the assignee has been quiet on the issue for STALE_HOURS (the clock starts at
// the claim and restarts with each verified comment the assignee posts there) and has no open pull
// request, nor one opened since the claim. After WARN_HOURS, the assignee gets one warning comment;
// the claim is released only once that warning is WARN_GRACE_MS old. Only self-claims are released:
// `/assign` (claims recorded by the -actions bot or blt-tasks[bot]) and the web "claim" button. An
// assignment a maintainer made for someone else is left alone.
//
// Pull requests are read anonymously from the forge's `forkmesh/pulls` ledger branch (no ledger yet
// means no pull requests). If the ledger can't be read, the run stops without changing anything.
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import * as forge from "../../scripts/actions/forge.mjs";
import { PR_HOURS, isBot, ledgerComments, loadIssue, isOpen, accountName, mention } from "./assign.mjs";

export const HOUR_MS = 60 * 60 * 1000;
export const STALE_HOURS = PR_HOURS;
export const WARN_HOURS = 18;
// The run is hourly; a released claim's warning is at least WARN_GRACE_MS old, which allows for a late runner.
export const WARN_GRACE_MS = 5 * HOUR_MS;
export const MAX_ACTIONS_PER_RUN = 10;
export const FORGE_URL = "https://git.owaspblt.org";
export const FORGE_REPO = "owasp-blt/BLT";
export const PULL_LEDGER = "forkmesh/pulls";
const BLOB_BATCH = 50;

const sameName = (a, b) => String(a ?? "").trim().toLowerCase() === String(b ?? "").trim().toLowerCase();
const toMs = (ts) => {
  const n = Number(ts || 0);
  return n > 1e12 ? n : n * 1000;
};

export const warningMarker = (name, since) => `<!-- blt-assign-stale-warning:${String(name).toLowerCase()}:${since} -->`;
export const releaseMarker = (name, since) => `<!-- blt-assign-stale:${String(name).toLowerCase()}:${since} -->`;

// ---- ledger -------------------------------------------------------------------------------------

/**
 * The event that gave `name` the issue, newest first: a `claim` (claimState "assigned") or a signed
 * `assignees` event listing them. Returns {ts, by, self} or null when the ledger doesn't say.
 */
export function assignment(record, name) {
  const events = (Array.isArray(record.events) ? record.events : []).slice().sort((a, b) => toMs(b?.ts) - toMs(a?.ts));
  for (const e of events) {
    if (e?.type === "claim" && sameName(e.assignee, name)) {
      if (String(e.claimState || "assigned") !== "assigned") return null; // released later, re-added another way
      const by = String(e.authorName || "");
      const self = (e.authorVerified === true && sameName(by, name)) || isBot(by);
      return { ts: toMs(e.ts), by, self };
    }
    if (e?.type === "assignees" && Array.isArray(e.assignees)) {
      if (!e.assignees.some((a) => sameName(a, name))) continue;
      const by = String(e.authorName || "");
      return { ts: toMs(e.ts), by, self: isBot(by) || String(e.id || "").startsWith("blt-assign-") };
    }
  }
  return null;
}

/** Newest verified comment `name` posted on the issue (ms), 0 if none. */
export function lastActivity(record, name) {
  let last = 0;
  for (const c of ledgerComments(record)) {
    if (c.authorVerified === true && sameName(c.authorName, name)) last = Math.max(last, toMs(c.ts));
  }
  return last;
}

/** When the stale warning for this claim period was posted by the -actions bot (ms), 0 if never. */
export function warnedAt(record, name, since) {
  const marker = warningMarker(name, since);
  let at = 0;
  for (const c of ledgerComments(record)) {
    if (c.authorVerified === true && isBot(c.authorName) && String(c.body || "").includes(marker)) at = Math.max(at, toMs(c.ts));
  }
  return at;
}

// ---- pull requests ------------------------------------------------------------------------------

export function parseFrontMatter(text) {
  const lines = String(text ?? "").split("\n");
  if (!lines.length || lines[0].trim() !== "---") return {};
  const values = {};
  for (const line of lines.slice(1)) {
    if (line.trim() === "---") return values;
    const i = line.indexOf(":");
    if (i > 0) values[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return {};
}

function blobText(blob) {
  if (blob == null) return null;
  if (typeof blob === "string") return blob;
  const content = blob.content ?? blob.text ?? "";
  return blob.encoding === "base64" ? Buffer.from(content, "base64").toString("utf8") : content;
}

/**
 * Every pull request in the forge ledger as [{number, author, status, opened}]. `getJson(url)` returns
 * {status, data}. A 404 for the ledger means no pull requests yet; any other failure throws.
 */
export async function readPulls(getJson, { url = FORGE_URL, repo = FORGE_REPO } = {}) {
  const api = `${url.replace(/\/+$/, "")}/api/repo/${repo}`;
  const get = async (op, params) => {
    const query = new URLSearchParams(params).toString();
    const { status, data } = await getJson(`${api}/${op}?${query}`);
    if (status === 404) return null;
    if (status >= 400 || !data || typeof data !== "object") throw new Error(`forge ${op} answered ${status}`);
    return data;
  };
  const tree = await get("tree", [["path", ".forkmesh/pulls"], ["ref", PULL_LEDGER]]);
  if (!tree) return [];
  const numbers = (tree.entries || []).filter((e) => e?.type === "tree" && /^\d+$/.test(String(e.name))).map((e) => String(e.name));
  const pulls = [];
  for (let i = 0; i < numbers.length; i += BLOB_BATCH) {
    const chunk = numbers.slice(i, i + BLOB_BATCH);
    const paths = chunk.map((n) => `.forkmesh/pulls/${n}/pull.md`);
    const data = await get("blobs", [...paths.map((p) => ["path", p]), ["ref", PULL_LEDGER]]);
    const blobs = data?.blobs || {};
    chunk.forEach((n, j) => {
      const meta = parseFrontMatter(blobText(blobs[paths[j]]));
      if (!meta.authorName) return;
      pulls.push({
        number: Number(n),
        author: meta.authorName,
        status: String(meta.status || "open").toLowerCase(),
        opened: toMs(Number(meta.ts) || Date.parse(meta.ts) || 0),
      });
    });
  }
  return pulls;
}

/** True when `name` has an open pull request, or opened one at or after `since`. */
export function hasPull(pulls, name, since) {
  return pulls.some((p) => sameName(p.author, name) && (p.status === "open" || p.opened >= since));
}

// ---- rules --------------------------------------------------------------------------------------

/**
 * What to do for each assignee of the open issues under `root`: [{number, name, action, reply, since}]
 * where action is "warn" or "unassign". Assignees who are fine produce nothing.
 */
export function plan({ root, numbers, pulls, now = Date.now(), log = () => {} }) {
  const actions = [];
  for (const number of numbers) {
    const issue = loadIssue(root, number);
    if (!issue || !isOpen(issue)) continue;
    for (const assignee of issue.record.assignees || []) {
      const name = accountName(assignee);
      const label = `#${number} @${assignee}`;
      if (!name) {
        log(`${label}: not an account name, skipped`);
        continue;
      }
      const claim = assignment(issue.record, name);
      if (!claim) {
        log(`${label}: no claim event in the ledger, skipped`);
        continue;
      }
      if (!claim.self) {
        log(`${label}: assigned by ${claim.by || "someone else"}, left alone`);
        continue;
      }
      if (hasPull(pulls, name, claim.ts)) {
        log(`${label}: has a pull request, fine`);
        continue;
      }
      const since = Math.max(claim.ts, lastActivity(issue.record, name));
      const idle = now - since;
      if (idle < WARN_HOURS * HOUR_MS) continue;
      const warned = warnedAt(issue.record, name, since);
      if (!warned) {
        actions.push({
          number,
          name,
          since,
          action: "warn",
          reply:
            `${mention(name)} there's been no pull request or comment from you here for ${WARN_HOURS} hours. ` +
            `If you're still working on this issue, please comment with an update or open a pull request; ` +
            `otherwise you'll be unassigned in about 6 hours so someone else can pick it up. ${warningMarker(name, since)}`,
        });
        continue;
      }
      if (idle >= STALE_HOURS * HOUR_MS && now - warned >= WARN_GRACE_MS) {
        actions.push({
          number,
          name,
          since,
          action: "unassign",
          reply:
            `${mention(name)} you've been unassigned from this issue because there was no pull request or update ` +
            `for ${STALE_HOURS} hours. It's open for others now; comment \`/assign\` to take it again. ${releaseMarker(name, since)}`,
        });
      }
    }
  }
  return actions;
}

export function openIssueNumbers(root) {
  const dir = join(root, ".forkmesh", "issues", "open");
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((n) => /^\d+$/.test(n)).map(Number).sort((a, b) => a - b);
}

/** Carry out the plan through the job API. Returns the actions taken. */
export async function execute(actions, { client, log = console.log, max = MAX_ACTIONS_PER_RUN }) {
  const done = [];
  for (const a of actions.slice(0, max)) {
    if (a.action === "unassign") {
      try {
        await client.changeAssignees(a.number, { remove: [a.name] });
      } catch (error) {
        if (client.missingEndpoint?.(error)) {
          log("the job API has no assignees endpoint; stopping (no ledger fallback for stale releases)");
          return done;
        }
        throw error;
      }
    }
    await client.comment(a.number, a.reply);
    log(`#${a.number} @${a.name}: ${a.action}`);
    done.push(a);
  }
  if (actions.length > max) log(`${actions.length - max} more left for the next run`);
  return done;
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  return { status: response.status, data };
}

async function main() {
  const root = forge.ROOT;
  const dryRun = process.argv.includes("--dry-run");
  const pulls = await readPulls(fetchJson, { url: process.env.BLT_FORGE_URL || FORGE_URL });
  console.log(`${pulls.length} pull requests in the forge ledger`);
  const actions = plan({ root, numbers: openIssueNumbers(root), pulls, log: console.log });
  if (!actions.length) {
    console.log("no stale assignments");
    return;
  }
  if (dryRun) {
    for (const a of actions) console.log(`would ${a.action} @${a.name} on #${a.number}: ${a.reply}`);
    return;
  }
  await execute(actions, { client: forge });
}

if (import.meta.url === `file://${process.argv[1]}`) forge.run(main);
