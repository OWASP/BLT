const assert = require("node:assert/strict");
const test = require("node:test");

const submissions = require("../scripts/submissions");

test("submissions exposes pure helpers", () => {
  assert.equal(typeof submissions.extractJobId, "function");
  assert.equal(typeof submissions.extractJobUrl, "function");
});

test("extractJobId supports issue-template headings and strips unsafe path characters", () => {
  const body = `### Job ID
acme-security-engineer/../../secret
`;

  assert.equal(submissions.extractJobId(body), "acme-security-engineersecret");
});

test("extractJobUrl prefers the template body URL over the issue title", () => {
  const issue = {
    title: "https://fallback.example/job",
    description: `## Job Posting URL
https://jobs.example/security-engineer
`,
  };

  assert.equal(submissions.extractJobUrl(issue), "https://jobs.example/security-engineer");
});
