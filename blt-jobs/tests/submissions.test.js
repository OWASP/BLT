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

test("leaderboard.html escapes quotes and links only https profiles", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const page = fs.readFileSync(path.join(__dirname, "..", "public", "leaderboard.html"), "utf8");
  const pick = (name) => page.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n        \\}`))[0];
  const { esc, httpsUrl } = new Function(`${pick("esc")}\n${pick("httpsUrl")}\nreturn { esc, httpsUrl };`)();
  assert.equal(esc(`a" onmouseover="x'`), "a&quot; onmouseover=&quot;x&#39;");
  assert.equal(httpsUrl("javascript:alert(1)"), "");
  assert.equal(httpsUrl("http://example.org/u"), "");
  assert.equal(httpsUrl('https://git.owaspblt.org/u" x="'), "");
  assert.equal(httpsUrl("https://git.owaspblt.org/alice"), "https://git.owaspblt.org/alice");
  assert.match(page, /profileUrls\[user\] = httpsUrl\(job\.added_by_url\)/);
});
