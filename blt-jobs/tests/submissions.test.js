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

test("a flag removes a job only when it comes from the account that added it", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const id = `zz-flag-test-${process.pid}`;
  const file = path.join(__dirname, "..", "jobs", `${id}.md`);
  fs.writeFileSync(file, `---\ntitle: "T"\nadded_by: "Alice"\n---\n\nbody\n`);
  try {
    const flag = (username) => submissions.createFromIssue({
      iid: 1,
      title: "[FLAG] remove",
      description: `### Job ID\n${id}\n`,
      labels: ["flag-job-posting"],
      author: { username },
    });
    assert.deepEqual(flag("mallory"), { kind: "flag-review", file: `jobs/${id}.md` });
    assert.ok(fs.existsSync(file));
    assert.deepEqual(flag("alice"), { kind: "flag", file: `jobs/${id}.md` });
    assert.ok(!fs.existsSync(file));
  } finally {
    fs.rmSync(file, { force: true });
  }
});
