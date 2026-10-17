#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { execFileSync, spawnSync } = require("child_process");

const root = path.join(__dirname, "..");
const apiBase = process.env.CI_API_V4_URL || "https://gitlab.com/api/v4";
const projectId = encodeURIComponent(process.env.CI_PROJECT_ID || "owasp-blt/blt-jobs");
const projectUrl = process.env.CI_PROJECT_URL || "https://gitlab.com/owasp-blt/blt-jobs";

async function api(endpoint, options = {}) {
  const token = process.env.GITLAB_TOKEN;
  if (!token) throw new Error("GITLAB_TOKEN is required.");

  const response = await fetch(`${apiBase}/projects/${projectId}${endpoint}`, {
    ...options,
    headers: {
      "PRIVATE-TOKEN": token,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) throw new Error(`${options.method || "GET"} ${endpoint}: ${response.status}`);
  if (response.status === 204) return null;
  return response.json();
}

function run(command, args, options = {}) {
  return execFileSync(command, args, { cwd: root, encoding: "utf8", ...options }).trim();
}

function issueEnv(issue) {
  return {
    ...process.env,
    ISSUE_USER: issue.author?.username || "",
    ISSUE_USER_URL: issue.author?.web_url || "",
    ISSUE_URL: issue.web_url || `${projectUrl}/-/issues/${issue.iid}`,
  };
}

function labels(issue) {
  return new Set(issue.labels || []);
}

function extractJobId(body) {
  return (body.match(/##[#]?\s+Job ID\s*\n+([^\n]+)/i)?.[1] || "").trim().replace(/[^a-zA-Z0-9_-]/g, "");
}

function extractJobUrl(issue) {
  const bodyUrl = (issue.description || "").match(/##[#]?\s+Job Posting URL\s*\n+([^\n]+)/i)?.[1]?.trim();
  const url = bodyUrl || issue.title.trim();
  if (!/^https?:\/\//i.test(url)) throw new Error("No valid Job Posting URL found.");
  return url;
}

function removeIfPresent(file) {
  if (file && fs.existsSync(path.join(root, file))) fs.rmSync(path.join(root, file));
}

function isDuplicate(file) {
  const result = spawnSync("node", ["scripts/check-duplicate.js", file], {
    cwd: root,
    encoding: "utf8",
  });
  return result.status !== 0;
}

function createFromIssue(issue) {
  const issueLabels = labels(issue);
  const env = issueEnv(issue);
  const body = issue.description || "";

  if (issueLabels.has("flag-job-posting") || (issue.title.startsWith("[FLAG]") && /##[#]?\s+Job ID/i.test(body))) {
    const id = extractJobId(body);
    const file = id && `jobs/${id}.md`;
    if (!file || !fs.existsSync(path.join(root, file))) throw new Error("The flagged job ID was not found.");
    fs.rmSync(path.join(root, file));
    return { kind: "flag", file };
  }

  if (issueLabels.has("job-posting-from-link") || /##[#]?\s+Job Posting URL/i.test(body)) {
    const url = extractJobUrl(issue);
    const output = run("python3", ["scripts/scrape-job-url.py", url], { env });
    const file = output.split("\n").pop();
    if (!file || !fs.existsSync(path.join(root, file))) throw new Error("The scraper did not create a job file.");
    if (isDuplicate(file)) {
      removeIfPresent(file);
      throw new Error("This appears to duplicate an existing job listing.");
    }
    return { kind: "job", file };
  }

  if (issueLabels.has("job-posting") || (/##[#]?\s+Company Name/i.test(body) && /##[#]?\s+Job Title/i.test(body))) {
    const file = run("node", ["scripts/issue-form-to-job.js", body], { env }).split("\n").pop();
    if (isDuplicate(file)) {
      removeIfPresent(file);
      throw new Error("This appears to duplicate an existing job listing.");
    }
    return { kind: "job", file };
  }

  if (issueLabels.has("job-seeker") || (/##\s+Personal Information/i.test(body) && /##\s+Professional Information/i.test(body))) {
    const file = run("node", ["scripts/issue-form-to-seeker.js", body], { env }).split("\n").pop();
    return { kind: "seeker", file };
  }

  return null;
}

async function addNote(issue, body) {
  await api(`/issues/${issue.iid}/notes`, { method: "POST", body: JSON.stringify({ body }) });
}

async function closeIssue(issue) {
  await api(`/issues/${issue.iid}`, { method: "PUT", body: JSON.stringify({ state_event: "close" }) });
}

async function main() {
  const issues = await api("/issues?state=opened&per_page=100&order_by=created_at&sort=asc");
  const processed = [];

  for (const issue of issues) {
    try {
      const result = createFromIssue(issue);
      if (result) processed.push({ issue, ...result });
    } catch (error) {
      console.error(`Issue #${issue.iid}: ${error.message}`);
      await addNote(issue, `Could not process this submission: ${error.message}`);
    }
  }

  if (!processed.length) {
    console.log("No labeled GitLab submissions to process.");
    return;
  }

  run("npm", ["run", "build:jobs"]);
  run("git", ["add", "jobs", "seekers", "public/data/jobs.json", "public/data/seekers.json"]);
  run("git", ["commit", "-m", `chore: process ${processed.length} GitLab submission(s)`]);
  run("git", ["push", "origin", "HEAD:main"]);

  for (const item of processed) {
    const destination = item.kind === "seeker" ? "seekers.html" : "jobs.html";
    await addNote(item.issue, `Processed and published: [view on the job board](https://jobs.owaspblt.org/${destination}).`);
    await closeIssue(item.issue);
  }

  console.log(`Processed ${processed.length} GitLab submission(s).`);
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}

module.exports = {
  createFromIssue,
  extractJobId,
  extractJobUrl,
  labels,
};
