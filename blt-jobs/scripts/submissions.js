// Turns one job / job-seeker / flag issue into files under jobs/ or seekers/ (or removes a flagged
// job). scripts/actions/process-submission.mjs calls createFromIssue() for each forge issue event,
// then builds, commits, comments and closes the issue. The issue is GitLab-shaped
// ({iid, title, description, labels, author: {username, web_url}, web_url}) for historical reasons.
const fs = require("fs");
const path = require("path");
const { execFileSync, spawnSync } = require("child_process");

const root = path.join(__dirname, "..");
const projectUrl = "https://git.owaspblt.org/BLT";

function run(command, args, options = {}) {
  return execFileSync(command, args, { cwd: root, encoding: "utf8", ...options }).trim();
}

function issueEnv(issue) {
  return {
    ...process.env,
    ISSUE_USER: issue.author?.username || "",
    ISSUE_USER_URL: issue.author?.web_url || "",
    ISSUE_URL: issue.web_url || `${projectUrl}/issues/${issue.iid}`,
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

module.exports = {
  createFromIssue,
  extractJobId,
  extractJobUrl,
  labels,
};
