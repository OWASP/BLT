#!/usr/bin/env node
// Keeps public/data/profiles.json in sync with open issues labelled `profile`.
// Run by .forkmesh/blt-ossh--update-profiles.yml (ported from the GitHub workflow update-profiles.yml).
//
// The job API cannot list issues, so instead of rebuilding the file from every open `profile` issue:
//   - an `issues` event adds, updates or removes the profile of that one issue;
//   - `schedule` / `workflow_dispatch` re-reads every issue already in the file (GET /issues/<n>) and
//     drops the ones that were closed or lost the label. Issue numbers can also be passed as arguments
//     (or the PROFILE_ISSUES input) to import existing profile issues.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { readEvent, eventName, getIssue, labelNames, issueUrl, commitBack, run } from "../../../scripts/actions/forge.mjs";

const PROJECT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const DATA = "public/data/profiles.json";

export function extractField(body, fieldName) {
  const match = body.match(new RegExp(`### ${fieldName}\\s*\\n\\s*(.+?)(?=\\n###|$)`, "s"));
  if (!match) return null;
  const value = match[1].trim();
  return value === "_No response_" || value === "" ? null : value;
}

export function extractCheckboxes(body, fieldName) {
  const section = body.match(new RegExp(`### ${fieldName}[\\s\\S]*?(?=\\n###|$)`, "s"));
  if (!section) return [];
  const checked = [];
  for (const line of section[0].split("\n")) {
    const match = line.match(/- \[x\]\s*(.+)/i);
    if (match) checked.push(match[1].trim());
  }
  return checked;
}

/** Profile for an issue, or null when the issue is not an open, valid profile. */
export function toProfile(issue, previous = {}) {
  if (!issue || issue.state !== "open" || !labelNames(issue).includes("profile")) return null;
  const body = issue.body || "";
  const githubUsername = extractField(body, "GitHub Username");
  if (!githubUsername) return null;
  const now = new Date().toISOString();
  return {
    id: issue.number,
    github_username: githubUsername,
    display_name: extractField(body, "Display Name") || githubUsername,
    bio: extractField(body, "Bio"),
    avatar_url: `https://github.com/${githubUsername}.png`,
    experience_level: extractField(body, "Experience Level"),
    interests: extractCheckboxes(body, "Areas of Interest"),
    skills: (extractField(body, "Skills & Technologies") || "").split(",").map((s) => s.trim()).filter(Boolean),
    looking_for: extractField(body, "What are you looking for\\?"),
    location: extractField(body, "Location \\(Optional\\)"),
    website: extractField(body, "Website/Portfolio \\(Optional\\)"),
    twitter: extractField(body, "Twitter/X Handle \\(Optional\\)"),
    linkedin: extractField(body, "LinkedIn Profile \\(Optional\\)"),
    recommended_projects: extractField(body, "Recommended Projects \\(Optional\\)"),
    recommended_communities: extractField(body, "Recommended Communities \\(Optional\\)"),
    recommended_reading: extractField(body, "Recommended Reading \\(Optional\\)"),
    created_at: issue.created_at || previous.created_at || now,
    updated_at: issue.updated_at || previous.updated_at || now,
    url: issueUrl(issue.number),
  };
}

const comparable = (p) => JSON.stringify({ ...p, updated_at: undefined });

/** Applies `issues` (number -> issue or null) to the profile list. Returns the new list and whether it changed. */
export function applyIssues(profiles, issues) {
  const byId = new Map(profiles.map((p) => [p.id, p]));
  let changed = false;
  for (const [id, issue] of issues) {
    const previous = byId.get(id);
    const next = toProfile(issue, previous);
    if (!next) {
      if (previous) { byId.delete(id); changed = true; }
      continue;
    }
    if (previous && comparable(previous) === comparable(next)) continue;
    if (previous && !issue.updated_at) next.updated_at = new Date().toISOString();
    byId.set(id, next);
    changed = true;
  }
  const list = [...byId.values()].sort((a, b) => a.id - b.id);
  return { profiles: list, changed };
}

async function main() {
  const path = join(PROJECT, DATA);
  const current = existsSync(path) ? JSON.parse(readFileSync(path, "utf8")) : { profiles: [] };
  const issues = new Map();

  if (eventName() === "issues") {
    const issue = readEvent().issue;
    if (issue) issues.set(issue.number, issue);
  } else {
    const extra = [...process.argv.slice(2), ...(process.env.PROFILE_ISSUES || "").split(/[\s,]+/)]
      .map(Number).filter((n) => Number.isInteger(n) && n > 0);
    const numbers = new Set([...current.profiles.map((p) => p.id), ...extra]);
    for (const n of numbers) {
      try {
        issues.set(n, await getIssue(n));
      } catch (error) {
        console.warn(`issue #${n}: ${error.message}`);
        if (/HTTP 404/.test(error.message)) issues.set(n, null);
      }
    }
  }

  const { profiles, changed } = applyIssues(current.profiles || [], issues);
  if (!changed) {
    console.log(`Profiles unchanged: ${profiles.length} developer profiles`);
    return;
  }
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify({ updated_at: new Date().toISOString(), total_profiles: profiles.length, profiles }, null, 2) + "\n");
  console.log(`Profiles updated: ${profiles.length} developer profiles`);
  if (process.env.COMMIT !== "0") {
    commitBack({ cwd: PROJECT, message: "blt-ossh: update profiles data", paths: [DATA], deploy: "blt-ossh" });
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) run(main);
