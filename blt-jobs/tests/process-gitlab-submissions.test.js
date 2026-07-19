const assert = require("node:assert/strict");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const submissions = require("../scripts/process-gitlab-submissions");
const root = path.join(__dirname, "..");

test("process-gitlab-submissions exposes pure helpers without requiring a token", () => {
  assert.equal(typeof submissions.extractJobId, "function");
  assert.equal(typeof submissions.extractJobUrl, "function");
});

test("extractJobId supports GitLab issue-template headings and strips unsafe path characters", () => {
  const body = `### Job ID
acme-security-engineer/../../secret
`;

  assert.equal(submissions.extractJobId(body), "acme-security-engineersecret");
});

test("extractJobUrl prefers the GitLab template body URL over the issue title", () => {
  const issue = {
    title: "https://fallback.example/job",
    description: `## Job Posting URL
https://jobs.example/security-engineer
`,
  };

  assert.equal(submissions.extractJobUrl(issue), "https://jobs.example/security-engineer");
});

test("direct GitLab submission processing still requires a token", () => {
  const env = { ...process.env };
  delete env.GITLAB_TOKEN;

  const result = spawnSync(process.execPath, ["scripts/process-gitlab-submissions.js"], {
    cwd: root,
    env,
    encoding: "utf8",
  });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /GITLAB_TOKEN is required\./);
});
