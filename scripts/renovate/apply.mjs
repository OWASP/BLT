// Turn a Renovate report into forge pull requests and the Dependency Dashboard issue.
//
//   node scripts/renovate/apply.mjs --report <report.json>... [--failed <folder>]...
//                                   [--pulls | --report-only | --dry-run] [--work <dir>]
//
// Renovate's `local` platform (scripts/renovate/run.sh) only looks updates up: it cannot push branches
// or open pull requests on ForkMesh. This script reads its report (reportType=file) and, per update
// group (renovate.json packageRules, `branchName` in the report):
// - applies npm, pep621 and pip_requirements updates in a scratch worktree, regenerates
//   package-lock.json (npm) and uv.lock (uv) for the folders it touched, and commits the result;
// - opens one pull request per group, signed by the blt-renovate key (forge-pulls.mjs), or sends a
//   revision when the group's open pull request lists a different set of updates. At most
//   MAX_OPEN_PULLS of the bot's pull requests are open at once; groups beyond that wait;
// - Flutter (pub) and Rust (cargo) groups are never applied (no toolchain on the runner).
// Every run (except --dry-run) refreshes the Dependency Dashboard issue through the job API, with a
// comment only when its content changed. Nothing is merged. Rules: docs/renovate.md.
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import * as forge from "../actions/forge.mjs";
import { BOT_NAME, FORGE_URL, makePullSigner, readBotPulls, submit } from "./forge-pulls.mjs";

export const MAX_OPEN_PULLS = 5;
export const MIN_RELEASE_AGE_DAYS = 3; // also renovate.json minimumReleaseAge
export const APPLIED_MANAGERS = new Set(["npm", "pep621", "pip_requirements"]);
export const DASHBOARD_TITLE = "Dependency Dashboard";
export const DASHBOARD_LABELS = ["dependencies"];
const BRANCH_PREFIX = "renovate/";
const GROUP_TITLES = {
  "npm-minor": "npm non-major dependencies",
  "python-minor": "Python non-major dependencies",
  wrangler: "wrangler",
  "major-wrangler": "wrangler (major)",
  pytest: "pytest and pytest-asyncio",
};
const GROUP_ORDER = ["npm-minor", "python-minor", "wrangler", "major-wrangler"];
const COMMIT_NAME = BOT_NAME;
const COMMIT_EMAIL = `${BOT_NAME}@users.noreply.git.owaspblt.org`;

// ---- the report ---------------------------------------------------------------------------------

/** Every proposed update in a Renovate file report, flattened. */
export function readUpdates(report) {
  const repos = Object.values(report?.repositories || {});
  const updates = [];
  for (const repo of repos) {
    for (const [manager, files] of Object.entries(repo.packageFiles || {})) {
      for (const file of files || []) {
        for (const dep of file.deps || []) {
          if (dep.skipReason) continue;
          for (const u of dep.updates || []) {
            if (!u.branchName?.startsWith(BRANCH_PREFIX)) continue;
            if (Number.isFinite(u.newVersionAgeInDays) && u.newVersionAgeInDays < MIN_RELEASE_AGE_DAYS) continue;
            updates.push({
              manager,
              packageFile: file.packageFile,
              lockFiles: file.lockFiles || [],
              depType: dep.depType || "",
              depName: dep.depName,
              currentValue: dep.currentValue ?? "",
              currentVersion: dep.currentVersion ?? dep.lockedVersion ?? "",
              newValue: u.newValue ?? "",
              newVersion: u.newVersion ?? "",
              updateType: u.updateType || "",
              lockOnly: Boolean(u.isLockfileUpdate) || (u.newValue ?? "") === (dep.currentValue ?? ""),
              group: u.branchName.slice(BRANCH_PREFIX.length),
            });
          }
        }
      }
    }
  }
  return updates;
}

/** Updates by group, groups in the order they get pull request slots. */
export function groupUpdates(updates) {
  const groups = new Map();
  for (const u of updates) {
    if (!groups.has(u.group)) groups.set(u.group, []);
    groups.get(u.group).push(u);
  }
  const rank = (slug) => (GROUP_ORDER.includes(slug) ? GROUP_ORDER.indexOf(slug) : GROUP_ORDER.length);
  return [...groups.entries()]
    .map(([slug, list]) => ({
      slug,
      head: BRANCH_PREFIX + slug,
      updates: list.sort((a, b) => a.packageFile.localeCompare(b.packageFile) || a.depName.localeCompare(b.depName)),
      applicable: list.every((u) => APPLIED_MANAGERS.has(u.manager)),
    }))
    .sort((a, b) => rank(a.slug) - rank(b.slug) || a.slug.localeCompare(b.slug));
}

export function groupTitle(group) {
  if (GROUP_TITLES[group.slug]) return GROUP_TITLES[group.slug];
  const names = [...new Set(group.updates.map((u) => u.depName))];
  const versions = [...new Set(group.updates.map((u) => u.newVersion))];
  if (names.length === 1) return `${names[0]} to ${versions.length === 1 ? versions[0] : "the next major"}`;
  return group.slug;
}

export const pullTitle = (group) => `deps: update ${groupTitle(group)}`;

/** A stable fingerprint of what a group proposes (not of the patch, which moves with main). */
export function groupKey(group) {
  const lines = group.updates.map((u) => `${u.packageFile}\t${u.depName}\t${u.newValue}\t${u.newVersion}`).sort();
  return createHash("sha256").update(lines.join("\n")).digest("hex").slice(0, 16);
}

export const pullMarker = (group) => `<!-- blt-renovate:${group.head}:${groupKey(group)} -->`;

/** Text from a manifest, safe in Markdown (also in a table cell). */
const md = (text) => String(text).replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[c]).replace(/[|`]/g, "\\$&");
/** A version or path as inline code: nothing is escaped inside it except the table cell pipe. */
const code = (text) => `\`${String(text).replace(/`/g, "'").replace(/\|/g, "\\|")}\``;
const change = (u) =>
  u.lockOnly ? `${code(u.currentVersion || u.currentValue)} → ${code(u.newVersion)} (lockfile)` : `${code(u.currentValue)} → ${code(u.newValue)}`;

export function pullDescription(group, { skipped = [] } = {}) {
  const rows = group.updates
    .filter((u) => !skipped.includes(u.packageFile))
    .map((u) => `| ${md(u.depName)} | ${md(u.updateType)} | ${change(u)} | ${code(u.packageFile)} |`);
  const lines = [
    `Renovate found these updates (weekly run, versions at least ${MIN_RELEASE_AGE_DAYS} days old).`,
    "",
    "| Package | Update | Change | File |",
    "| --- | --- | --- | --- |",
    ...rows,
    "",
  ];
  if (skipped.length) {
    lines.push(`Left out because their lockfile could not be regenerated here: ${skipped.map(code).join(", ")}.`, "");
  }
  lines.push(
    "Nothing here merges on its own. Check the changelogs, and that CI tested every project this touches",
    "(a project CI skips, or one with no tests in `scripts/ci/tests.tsv`, needs a local run).",
    "This pull request is updated in place by the next weekly run; close it to skip these versions until",
    "newer ones appear. Rules: `docs/renovate.md`.",
    "",
    "AI model: None",
    "",
    pullMarker(group),
  );
  return lines.join("\n");
}

// ---- applying updates ---------------------------------------------------------------------------

const escapeRe = (text) => String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
/** PEP 503 name normalization. */
export const pyName = (name) => String(name).toLowerCase().replace(/[-_.]+/g, "-");

/** package.json with `depName` in `depType` changed from currentValue to newValue, or null. */
export function updatePackageJson(text, { depType, depName, currentValue, newValue }) {
  const data = JSON.parse(text);
  if (data?.[depType]?.[depName] !== currentValue) return null;
  const re = new RegExp(`("${escapeRe(depName)}"\\s*:\\s*")${escapeRe(currentValue)}(")`, "g");
  const updated = text.replace(re, (_, a, b) => `${a}${newValue}${b}`);
  return updated === text ? null : updated;
}

/** Replace the version specifier of `depName` in one PEP 508 requirement string, or null. */
export function updateRequirement(requirement, { depName, currentValue, newValue }) {
  const m = /^(\s*)([A-Za-z0-9][A-Za-z0-9._-]*)(\s*\[[^\]]*\])?(\s*)([^;#]*?)(\s*(?:[;#].*)?)$/.exec(requirement);
  if (!m || pyName(m[2]) !== pyName(depName)) return null;
  const spec = m[5];
  let next;
  if (spec.includes(currentValue)) next = spec.replace(currentValue, newValue);
  else if (spec.replace(/\s+/g, "") === String(currentValue).replace(/\s+/g, "")) next = newValue;
  else return null;
  return m[1] + m[2] + (m[3] || "") + m[4] + next + m[6];
}

/** pyproject.toml with the requirement string for depName updated, or null. */
export function updatePyproject(text, update) {
  let changed = false;
  const updated = text.replace(/(["'])([^"'\n]+)\1/g, (whole, quote, inner) => {
    if (changed) return whole;
    const next = updateRequirement(inner, update);
    if (next === null || next === inner) return whole;
    changed = true;
    return quote + next + quote;
  });
  return changed ? updated : null;
}

/** requirements.txt with the line for depName updated, or null. */
export function updateRequirementsTxt(text, update) {
  let changed = false;
  const lines = text.split("\n").map((line) => {
    if (changed || /^\s*(#|-)/.test(line)) return line;
    const next = updateRequirement(line, update);
    if (next === null || next === line) return line;
    changed = true;
    return next;
  });
  return changed ? lines.join("\n") : null;
}

const EDITORS = { npm: updatePackageJson, pep621: updatePyproject, pip_requirements: updateRequirementsTxt };

function run(cmd, args, { cwd, env = {}, log }) {
  const result = spawnSync(cmd, args, { cwd, encoding: "utf8", env: { ...process.env, ...env }, maxBuffer: 64 * 1024 * 1024 });
  if (result.status !== 0) {
    const tail = `${result.stdout || ""}${result.stderr || ""}`.trim().split("\n").slice(-12).join("\n");
    log?.(`  ${cmd} ${args.join(" ")} failed in ${cwd}:\n${tail}`);
    return false;
  }
  return true;
}

function git(cwd, args) {
  const result = spawnSync("git", args, { cwd, encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });
  if (result.status !== 0) throw new Error(`git ${args.join(" ")}: ${result.stderr.trim()}`);
  return result.stdout;
}

/** Regenerate the lockfiles next to `packageFile` for the updates applied to it. */
function relock(tree, packageFile, applied, { uv, log }) {
  const dir = join(tree, dirname(packageFile));
  if (packageFile.endsWith("package.json") && existsSync(join(dir, "package-lock.json"))) {
    const npmArgs = ["--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund", "--engine-strict=false"];
    const wanted = readFileSync(join(dir, "package.json"), "utf8");
    // `npm install name@version` pins the exact version Renovate picked (a lockfile-only update keeps
    // its range) but also rewrites package.json; put ours back and sync the lockfile to it.
    const pins = applied.map((u) => `${u.depName}@${u.newVersion}`);
    if (!run("npm", ["install", ...npmArgs, ...pins], { cwd: dir, log })) return false;
    writeFileSync(join(dir, "package.json"), wanted);
    return run("npm", ["install", ...npmArgs], { cwd: dir, log });
  }
  if (packageFile.endsWith("pyproject.toml") && existsSync(join(dir, "uv.lock"))) {
    if (!uv) {
      log?.(`  no uv: cannot regenerate ${dirname(packageFile)}/uv.lock`);
      return false;
    }
    const pins = applied.flatMap((u) => ["--upgrade-package", `${u.depName}==${u.newVersion}`]);
    return run(uv, ["lock", ...pins], { cwd: dir, env: { UV_NO_PROGRESS: "1" }, log });
  }
  return true;
}

/**
 * Apply `group` on a detached worktree of `base` under `work` and commit it. Returns
 * {patch, commits, baseOid, skipped} or null when nothing changed.
 */
export function buildGroup(root, group, { work, base = "HEAD", uv = "", log = console.log }) {
  const tree = mkdtempSync(join(work, `${group.slug.replace(/[^\w.-]+/g, "_")}-`));
  rmSync(tree, { recursive: true, force: true });
  git(root, ["worktree", "add", "--detach", "--quiet", tree, base]);
  try {
    const baseOid = git(tree, ["rev-parse", "HEAD"]).trim();
    const byFile = new Map();
    for (const u of group.updates) {
      if (!byFile.has(u.packageFile)) byFile.set(u.packageFile, []);
      byFile.get(u.packageFile).push(u);
    }
    const skipped = [];
    for (const [packageFile, updates] of byFile) {
      const path = join(tree, packageFile);
      if (!existsSync(path)) continue;
      let text = readFileSync(path, "utf8");
      const applied = [];
      for (const u of updates) {
        if (u.lockOnly) {
          applied.push(u);
          continue;
        }
        const next = EDITORS[u.manager]?.(text, u);
        if (next === null || next === undefined) {
          log(`  ${packageFile}: could not find ${u.depName} ${u.currentValue}; left out`);
          continue;
        }
        text = next;
        applied.push(u);
      }
      if (!applied.length) continue;
      writeFileSync(path, text);
      const needsLock = applied.some((u) => u.lockOnly) || updates[0].lockFiles.length > 0;
      if (needsLock && !relock(tree, packageFile, applied, { uv, log })) {
        git(tree, ["checkout", "--quiet", "--", dirname(packageFile) === "." ? packageFile : dirname(packageFile)]);
        git(tree, ["clean", "-fdq", "--", dirname(packageFile)]);
        skipped.push(packageFile);
      }
    }
    git(tree, ["add", "-A", "--", ...[...byFile.keys()].map((f) => dirname(f))]);
    if (!git(tree, ["diff", "--cached", "--name-only"]).trim()) return null;
    const subject = pullTitle(group);
    git(tree, [
      "-c", `user.name=${COMMIT_NAME}`, "-c", `user.email=${COMMIT_EMAIL}`, "-c", "commit.gpgsign=false",
      "commit", "--quiet", "--no-verify", "-m", subject, "-m", `Renovate group ${group.head} (${groupKey(group)}).`,
    ]);
    const patch = git(tree, ["diff", "--no-color", "--no-ext-diff", `${baseOid}..HEAD`]);
    const commits = git(tree, ["format-patch", "--stdout", "--no-signature", "--no-color", `${baseOid}..HEAD`]);
    return { patch, commits, baseOid, skipped };
  } finally {
    spawnSync("git", ["worktree", "remove", "--force", tree], { cwd: root });
    rmSync(tree, { recursive: true, force: true });
  }
}

// ---- planning -----------------------------------------------------------------------------------

/**
 * What to do with each group, given the bot's pull requests (any status): "update" (its open pull
 * request lists other updates), "current" (it lists these), "declined" (a closed pull request
 * listed exactly these: wait for newer versions), "open" (new pull request, a slot is free), "wait"
 * (no slot) or "report" (not applied).
 */
export function plan(groups, pulls, { max = MAX_OPEN_PULLS } = {}) {
  const open = pulls.filter((p) => p.status === "open");
  const byHead = new Map(open.map((p) => [p.head, p]));
  let slots = max - open.length;
  return groups.map((group) => {
    if (!group.applicable) return { group, action: "report" };
    const marker = pullMarker(group);
    const pull = byHead.get(group.head);
    if (pull) return { group, pull, action: pull.body.includes(marker) ? "current" : "update" };
    if (pulls.some((p) => p.status !== "open" && p.body.includes(marker))) return { group, action: "declined" };
    if (slots > 0) {
      slots -= 1;
      return { group, action: "open" };
    }
    return { group, action: "wait" };
  });
}

// ---- the dashboard ------------------------------------------------------------------------------

export function dashboardBody(steps, { problems = [], url = FORGE_URL } = {}) {
  const pullLink = (n) => `[#${n}](${url}/BLT/pulls/${n})`;
  const list = (u) => `${md(u.depName)} ${change(u)} in ${code(u.packageFile)}`;
  const section = (title, items) => (items.length ? [`## ${title}`, "", ...items, ""] : []);
  const open = steps.filter((s) => s.number);
  const waiting = steps.filter((s) => s.action === "wait" || (["open", "update"].includes(s.action) && !s.number));
  const report = steps.filter((s) => s.action === "report");
  const declined = steps.filter((s) => s.action === "declined");
  const lines = [
    "This issue lists the dependency updates Renovate found in the weekly run (`.forkmesh/renovate.yml`).",
    `At most ${MAX_OPEN_PULLS} update pull requests are open at a time; nothing merges on its own. Rules: \`docs/renovate.md\`.`,
    "",
    ...section("Open pull requests", open.map((s) => `- ${pullLink(s.number)} ${md(pullTitle(s.group))} (${s.group.updates.length} updates)`)),
    ...section(
      "Waiting for a free slot",
      waiting.map((s) => `- ${md(pullTitle(s.group))}: ${s.group.updates.map(list).join("; ")}`),
    ),
    ...section(
      "Closed without merging (proposed again once newer versions appear)",
      declined.map((s) => `- ${md(pullTitle(s.group))}`),
    ),
    ...section(
      "Listed only (no Flutter or Rust toolchain on the runner; update these by hand)",
      report.flatMap((s) => s.group.updates.map((u) => `- ${list(u)} (${u.updateType})`)),
    ),
    ...section("Problems", problems.map((p) => `- ${p}`)),
  ];
  if (!open.length && !waiting.length && !report.length && !declined.length) lines.push("Everything is up to date.", "");
  return lines.join("\n").trimEnd();
}

export const dashboardMarker = (body) =>
  `<!-- blt-renovate-dashboard:${createHash("sha256").update(body).digest("hex").slice(0, 16)} -->`;

/** The open dashboard issue in this checkout's issue ledger, as {number, lastMarker}, or null. */
export function findDashboard(root) {
  const dir = join(root, ".forkmesh", "issues", "open");
  if (!existsSync(dir)) return null;
  const found = [];
  for (const n of readdirSync(dir)) {
    const file = join(dir, n, `issue-${n}.json`);
    if (!existsSync(file)) continue;
    let record;
    try {
      record = JSON.parse(readFileSync(file, "utf8"));
    } catch {
      continue;
    }
    if (record.title !== DASHBOARD_TITLE || !/-actions$/.test(String(record.authorName || ""))) continue;
    const markers = [];
    for (const e of record.events || []) {
      if (e?.type !== "comment" && e?.type !== "open") continue;
      if (e.type === "comment" && !/-actions$/.test(String(e.authorName || ""))) continue;
      const m = String(e.body || "").match(/<!-- blt-renovate-dashboard:[0-9a-f]+ -->/);
      if (m) markers.push(m[0]);
    }
    found.push({ number: Number(n), lastMarker: markers.at(-1) || "" });
  }
  return found.sort((a, b) => a.number - b.number)[0] || null;
}

// ---- main ---------------------------------------------------------------------------------------

function parseArgs(argv) {
  const args = { mode: "pulls", reports: [], failed: [], work: "" };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--report") args.reports.push(argv[++i]);
    else if (a === "--failed") args.failed.push(argv[++i]);
    else if (a === "--work") args.work = argv[++i];
    else if (a === "--pulls") args.mode = "pulls";
    else if (a === "--report-only") args.mode = "report";
    else if (a === "--dry-run") args.mode = "dry-run";
    else throw new Error(`unknown argument: ${a}`);
  }
  if (!args.reports.length) throw new Error("--report <file> is required");
  return args;
}

async function getJson(url) {
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
  const args = parseArgs(process.argv.slice(2));
  const root = forge.ROOT;
  const url = (process.env.BLT_FORGE_URL || FORGE_URL).replace(/\/+$/, "");
  // scripts/renovate/run.sh runs Renovate once per project folder: one report each.
  const reports = args.reports.map((file) => JSON.parse(readFileSync(file, "utf8")));
  const problems = args.failed.map((folder) => `Renovate failed for \`${folder}\`; its updates are missing from this run.`);
  for (const report of reports) {
    for (const repo of Object.values(report.repositories || {})) {
      for (const p of repo.problems || []) if (p.level >= 50) problems.push(`Renovate: ${md(p.msg)}`);
    }
  }
  const groups = groupUpdates(reports.flatMap(readUpdates));
  console.log(`${groups.length} update groups: ${groups.map((g) => `${g.head} (${g.updates.length})`).join(", ") || "none"}`);

  const seed = process.env.BLT_RENOVATE_SEED || "";
  let signer = null;
  if (seed) signer = makePullSigner(seed);
  else if (args.mode === "pulls") {
    console.log("BLT_RENOVATE_SEED is not set: no pull requests this run (dashboard only)");
    problems.push("BLT_RENOVATE_SEED is not set, so no pull requests were opened.");
    args.mode = "report";
  }
  const pulls = signer
    ? (await readBotPulls(getJson, signer.author, { url })).filter((p) => p.head.startsWith(BRANCH_PREFIX))
    : [];
  if (signer) console.log(`bot key ${signer.author}: ${pulls.filter((p) => p.status === "open").length} open pull requests`);
  const steps = plan(groups, pulls);

  const work = args.work || mkdtempSync(join(process.env.RUNNER_TEMP || tmpdir(), "blt-renovate-"));
  const uv = process.env.UV_BIN || "";
  for (const step of steps) {
    const { group } = step;
    console.log(`${group.head}: ${step.action}${step.pull ? ` (#${step.pull.number})` : ""}`);
    if (step.pull) step.number = step.pull.number;
    if (!["open", "update"].includes(step.action) || args.mode === "report") continue;
    const built = buildGroup(root, group, { work, uv });
    if (!built) {
      console.log("  nothing to change on main");
      step.action = "current";
      continue;
    }
    console.log(`  patch ${built.patch.length} bytes${built.skipped.length ? `, left out ${built.skipped.join(", ")}` : ""}`);
    if (built.skipped.length) problems.push(`${group.head}: could not regenerate the lockfile for ${built.skipped.join(", ")}`);
    if (args.mode === "dry-run" || !signer) continue;
    const fields = {
      title: pullTitle(group),
      description: pullDescription(group, built),
      base: "main",
      head: group.head,
      patch: built.patch,
      commits: built.commits,
      baseOid: built.baseOid,
      ts: Math.floor(Date.now() / 1000),
    };
    try {
      if (step.action === "update") {
        await submit({ number: step.number, revision: signer.revision(step.number, fields) }, { url });
        console.log(`  sent a revision of #${step.number}`);
      } else {
        const result = await submit({ pull: signer.pull(fields) }, { url });
        step.number = result.number || 0;
        console.log(`  opened #${step.number || "?"}`);
      }
    } catch (error) {
      console.log(`  ${error.message}`);
      problems.push(`${group.head}: ${md(error.message)}`);
    }
  }

  const body = dashboardBody(steps, { problems, url });
  const marker = dashboardMarker(body);
  if (args.mode === "dry-run") {
    console.log(`\n--- dashboard ---\n${body}`);
    return;
  }
  const dashboard = findDashboard(root);
  if (!dashboard) {
    const issue = await forge.createIssue({ title: DASHBOARD_TITLE, body: `${body}\n\n${marker}`, labels: DASHBOARD_LABELS });
    console.log(`opened the dashboard issue #${issue?.number ?? "?"}`);
  } else if (dashboard.lastMarker === marker) {
    console.log(`dashboard #${dashboard.number} is current`);
  } else {
    await forge.comment(dashboard.number, `${body}\n\n${marker}`);
    console.log(`updated the dashboard #${dashboard.number}`);
  }
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) forge.run(main);
