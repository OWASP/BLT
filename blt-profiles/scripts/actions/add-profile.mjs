#!/usr/bin/env node
// Turns an "Add profile" issue (issue-templates/add-profile.md) into a commit on main:
// public/profiles/<username>.json and public/profiles/index.json, then comments and closes the issue.
// Run by .forkmesh/blt-profiles--add-profile.yml for `issues` events, or for one issue number with
// workflow_dispatch (input `issue`). Replaces the Worker's GitLab issue webhook (branch + MR).
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as forge from "../../../scripts/actions/forge.mjs";

const PROJECT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const PROFILES_DIR = join(PROJECT, "public", "profiles");
export const SITE_URL = "https://profiles.owaspblt.org";
export const FORGE_URL = "https://git.owaspblt.org";
export const TEMPLATE_URL = `${FORGE_URL}/BLT/blob/main/blt-profiles/issue-templates/add-profile.md`;

const LABELS = ["profile", "add-profile", "profile-submission"];
const TITLE_PREFIX = /^\s*\[blt-profiles\]/i;
const ROLE_SECTIONS = ["Leads", "Co-Leads", "Ambassadors", "Interns", "Contributors", "Mentors"];
// Paths the Worker serves itself (src/index.py RESERVED_PATHS) cannot be profile names.
const RESERVED = new Set(["api", "favicon.ico", "index.html", "profile.html", "profiles", "robots.txt", "webhooks", "index", "404.html"]);
const USERNAME = /^[a-z0-9][a-z0-9._-]{1,38}$/;

/** {heading: raw text} for every "## heading" section of the issue body. */
export function parseSections(body) {
  const sections = {};
  let current = null;
  for (const line of String(body || "").replace(/\r\n?/g, "\n").split("\n")) {
    const heading = /^##\s+(.+?)\s*$/.exec(line);
    if (heading) {
      current = heading[1].trim();
      sections[current] = [];
    } else if (current) {
      sections[current].push(line);
    }
  }
  return Object.fromEntries(Object.entries(sections).map(([k, v]) => [k, v.join("\n")]));
}

export function cleanValue(value) {
  return String(value || "")
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/^\s*- \[[ xX]\].*$/gm, "")
    .trim();
}

/** Cleaned field values plus `confirmed` (the Confirmation checkbox is ticked). */
export function parseIssueBody(body) {
  const sections = parseSections(body);
  const fields = Object.fromEntries(Object.entries(sections).map(([k, v]) => [k, cleanValue(v)]));
  fields.confirmed = /^\s*- \[[xX]\]/m.test(sections.Confirmation || "");
  return fields;
}

export function hasTemplate(body) {
  const sections = parseSections(body);
  return "Role Section" in sections && ("Display Name" in sections || "Username" in sections || "GitLab Username" in sections);
}

/** The issue looks like a profile submission: label, title prefix or the template headings. */
export function isProfileIssue(issue) {
  const labels = forge.labelNames(issue).map((l) => l.toLowerCase());
  return labels.some((l) => LABELS.includes(l)) || TITLE_PREFIX.test(issue?.title || "") || hasTemplate(issue?.body);
}

const text = (value) => String(value ?? "").trim();
const cleanUsername = (value) => text(value).replace(/^@+/, "").toLowerCase();
const cleanUrl = (value) => (/^https?:\/\//i.test(text(value)) ? text(value) : "");

export function normalizeRoleSection(value) {
  const raw = text(value).toLowerCase();
  return ROLE_SECTIONS.find((role) => role.toLowerCase() === raw) || "Contributors";
}

export function parseTags(value) {
  return text(value).split(/[,;]+/).map((t) => t.trim()).filter(Boolean).slice(0, 12);
}

export function truncate(value, max) {
  const s = text(value);
  if (s.length <= max) return s;
  let short = s.slice(0, max);
  const space = short.lastIndexOf(" ");
  if (space > 0) short = short.slice(0, space);
  return `${short.trim()}...`;
}

/** Validated profile name: the Username field, else the issue author's account name. */
export function profileUsername(fields, author) {
  const username = cleanUsername(fields.Username || author);
  if (!USERNAME.test(username)) {
    throw new Error("Username must be 2-39 characters using lowercase letters, numbers, dots, underscores or hyphens.");
  }
  if (RESERVED.has(username)) throw new Error(`"${username}" is reserved; choose another username.`);
  return username;
}

/** The profile JSON; keeps counters, badges and created_at of an existing profile. */
export function buildProfile(fields, { username, author, avatar = "", issueUrl = "", now, existing = null }) {
  const roleSection = normalizeRoleSection(fields["Role Section"]);
  const github = cleanUsername(fields["GitHub Username"]);
  const gitlab = cleanUsername(fields["GitLab Username"]);
  const editable = {
    username,
    name: text(fields["Display Name"]) || existing?.name || author || username,
    role: text(fields["Role / Title"]) || roleSection.replace(/s$/, ""),
    role_section: roleSection,
    avatar: avatar || existing?.avatar || "",
    forge: author ? `${FORGE_URL}/@${author}` : "",
    gitlab: gitlab ? `https://gitlab.com/${gitlab}` : "",
    github: github ? `https://github.com/${github}` : "",
    linkedin: cleanUrl(fields["LinkedIn Profile URL"]),
    website: cleanUrl(fields["Website URL"]),
    wallet: text(fields["Wallet / ID String"]),
    questions: {
      involvement: text(fields["Question 1: What is your involvement in cybersecurity?"]),
      evolution: text(fields["Question 2: How do you see cybersecurity evolving?"]),
      achievement: text(fields["Question 3: What is your most significant cybersecurity achievement or contribution?"]),
    },
    tags: parseTags(fields["Tags / Labels"]),
    submitted_by: author,
    source_issue: issueUrl,
  };
  if (existing) return { ...existing, ...editable, created_at: existing.created_at || now, updated_at: now };
  return {
    ...editable,
    bio: "",
    followers: 0,
    following: 0,
    public_repos: 0,
    streak: { current: 0, longest: 0, days_visited: 0, last_visit: "", last_checkin: "" },
    stats: { bugs_reported: 0, open_issues: 0, closed_issues: 0 },
    issue_stats: { general: 0, functional: 0, performance: 0, security: 0, typo: 0, design: 0 },
    bacon: { earned: 0, pending: 0, completed: 0 },
    prs: { total: 0, merged: 0, open: 0, closed: 0 },
    pr_list: [],
    badges: [],
    rank: "Newcomer",
    monthly_report: { top_finding: "" },
    created_at: now,
  };
}

export function upsertIndex(index, profile) {
  const entry = {
    username: profile.username,
    name: profile.name,
    role: profile.role,
    role_section: profile.role_section,
    avatar: profile.avatar,
    tags: profile.tags,
    stats: profile.stats,
    prs: profile.prs,
    questions: { involvement: truncate(profile.questions?.involvement, 200) },
    created_at: profile.created_at,
  };
  return [...(Array.isArray(index) ? index : []).filter((item) => item?.username !== profile.username), entry]
    .sort((a, b) => String(a.username || "").localeCompare(String(b.username || "")));
}

/** Only the account that created a profile (or, for older profiles, the same-named account) may change it. */
export function ownsProfile(existing, username, author) {
  if (!existing) return true;
  const owner = existing.submitted_by || username;
  return owner.toLowerCase() === String(author || "").toLowerCase();
}

function readJson(file, fallback) {
  if (!existsSync(file)) return fallback;
  return JSON.parse(readFileSync(file, "utf8"));
}

const writeJson = (file, value) => writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);

/**
 * Process one issue. Returns {status: "skipped" | "failed" | "added" | "updated", ...}.
 * `deps` injects the forge calls and the commit (tests replace them).
 */
export async function processIssue(issue, deps = {}) {
  const {
    dir = PROFILES_DIR,
    comment = forge.comment,
    closeIssue = forge.closeIssue,
    commit = () => true,
    issueUrl = forge.issueUrl,
    now = () => new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
  } = deps;
  const number = issue.number;
  if (issue.state && issue.state !== "open") return { status: "skipped", reason: `issue is ${issue.state}` };
  if (!isProfileIssue(issue)) return { status: "skipped", reason: "not a profile issue" };
  if (!hasTemplate(issue.body)) {
    const labelled = forge.labelNames(issue).some((l) => LABELS.includes(l.toLowerCase()));
    if (!labelled) return { status: "skipped", reason: "no profile template headings" };
  }

  const fail = async (message) => {
    await comment(number, `Could not add the profile: ${message}\n\nEdit the issue description to fix it (template: ${TEMPLATE_URL}); the workflow runs again on every edit.`);
    return { status: "failed", error: message };
  };

  if (!hasTemplate(issue.body)) return fail("the description does not contain the template headings.");
  const fields = parseIssueBody(issue.body);
  if (!fields.confirmed) return fail("tick the Confirmation checkbox (`- [x]`) to consent to publishing the profile.");
  const author = forge.authorLogin(issue);
  if (!author) return fail("the issue has no author.");

  let username;
  try {
    username = profileUsername(fields, author);
  } catch (error) {
    return fail(error.message);
  }
  const file = join(dir, `${username}.json`);
  const existing = readJson(file, null);
  if (!ownsProfile(existing, username, author)) {
    return fail(`the profile "${username}" belongs to another account.`);
  }

  const profile = buildProfile(fields, {
    username,
    author,
    avatar: issue.user?.avatar_url || "",
    issueUrl: issueUrl(number),
    now: now(),
    existing,
  });
  writeJson(file, profile);
  const indexFile = join(dir, "index.json");
  writeJson(indexFile, upsertIndex(readJson(indexFile, []), profile));

  const verb = existing ? "update" : "add";
  const pushed = commit({ message: `blt-profiles: ${verb} profile @${username} (issue #${number})`, username });
  const url = `${SITE_URL}/${username}`;
  await comment(number, pushed
    ? `Profile ${existing ? "updated" : "added"}: ${url} (it is live after the deploy finishes).`
    : `No changes: the profile at ${url} already has this content.`);
  await closeIssue(number);
  return { status: existing ? "updated" : "added", username, pushed };
}

async function loadIssue() {
  if (forge.eventName() === "workflow_dispatch") {
    const n = Number(process.env.INPUT_ISSUE || forge.readEvent().inputs?.issue);
    if (!Number.isInteger(n) || n <= 0) throw new Error("workflow_dispatch needs the `issue` input");
    return { number: n, ...(await forge.getIssue(n)) };
  }
  const issue = forge.readEvent().issue;
  if (!issue) throw new Error("no issue in the event payload");
  return issue;
}

async function main() {
  const issue = await loadIssue();
  const result = await processIssue(issue, {
    commit: ({ message }) => forge.commitBack({ cwd: PROJECT, message, paths: ["public/profiles"], deploy: "blt-profiles" }),
  });
  console.log(`Issue #${issue.number}: ${JSON.stringify(result)}`);
  if (result.status === "failed") process.exit(1);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) forge.run(main);
