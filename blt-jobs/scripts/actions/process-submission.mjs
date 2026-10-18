#!/usr/bin/env node
// Turns a job / job-seeker / flag issue into a commit on main, then comments and closes the issue.
// Run by .forkmesh/blt-jobs--process-submissions.yml for `issues` events, or for one issue number
// with workflow_dispatch (input `issue`). Replaces the GitLab-only scripts/process-gitlab-submissions.js,
// reusing its createFromIssue(): the job API cannot list issues, so each issue is processed on its own event.
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  readEvent, eventName, getIssue, comment, closeIssue, labelNames, authorLogin, issueUrl, commitBack, run,
} from "../../../scripts/actions/forge.mjs";

const require = createRequire(import.meta.url);
const PROJECT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

/** The GitLab-shaped issue createFromIssue() expects. */
export function toGitlabIssue(issue) {
  const login = authorLogin(issue);
  return {
    iid: issue.number,
    title: issue.title || "",
    description: issue.body || "",
    labels: labelNames(issue),
    author: { username: login, web_url: login ? `${(process.env.FORKMESH_API_URL || "").replace(/\/+$/, "")}/${login}` : "" },
    web_url: issueUrl(issue.number),
    state: issue.state,
  };
}

async function loadIssue() {
  if (eventName() === "workflow_dispatch") {
    const n = Number(process.env.INPUT_ISSUE || readEvent().inputs?.issue);
    if (!Number.isInteger(n) || n <= 0) throw new Error("workflow_dispatch needs the `issue` input");
    return { number: n, ...(await getIssue(n)) };
  }
  const issue = readEvent().issue;
  if (!issue) throw new Error("no issue in the event payload");
  return issue;
}

async function main() {
  const issue = await loadIssue();
  if (issue.state && issue.state !== "open") {
    console.log(`Issue #${issue.number} is ${issue.state}; nothing to do.`);
    return;
  }
  const { createFromIssue } = require("../process-gitlab-submissions.js");
  let result;
  try {
    result = createFromIssue(toGitlabIssue(issue));
  } catch (error) {
    console.error(`Issue #${issue.number}: ${error.message}`);
    await comment(issue.number, `Could not process this submission: ${error.message}`);
    process.exit(1);
  }
  if (!result) {
    console.log(`Issue #${issue.number} is not a job, job-seeker or flag submission.`);
    return;
  }

  execFileSync("npm", ["run", "build:jobs"], { cwd: PROJECT, stdio: "inherit" });
  commitBack({
    cwd: PROJECT,
    message: `blt-jobs: process submission from issue #${issue.number} (${result.kind})`,
    paths: ["jobs", "seekers", "public/data/jobs.json", "public/data/seekers.json"],
    deploy: "blt-jobs",
  });

  const destination = result.kind === "seeker" ? "seekers.html" : "jobs.html";
  await comment(issue.number, `Processed and published: [view on the job board](https://jobs.owaspblt.org/${destination}).`);
  await closeIssue(issue.number);
  console.log(`Processed issue #${issue.number} (${result.kind}: ${result.file}).`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) run(main);
