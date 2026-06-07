const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { buildAll } = require("../scripts/build-jobs");

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "blt-jobs-build-"));
}

function writeFile(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

test("buildAll emits GitLab source traceability and review metadata for jobs", () => {
  const root = tempDir();
  const jobsDir = path.join(root, "jobs");
  const seekersDir = path.join(root, "seekers");
  const jobsOutFile = path.join(root, "public", "data", "jobs.json");
  const seekersOutFile = path.join(root, "public", "data", "seekers.json");

  writeFile(
    path.join(jobsDir, "acme-security-engineer.md"),
    `---
title: "Security Engineer"
organization_name: "Acme"
location: "Remote"
job_type: "full-time"
application_url: "https://acme.example/jobs/security-engineer"
source_issue_url: "https://gitlab.com/owasp-blt/blt-jobs/-/issues/123"
created_at: "2026-01-02T00:00:00Z"
expires_at: "2099-01-02T00:00:00Z"
---

Build secure systems.
`
  );

  buildAll({
    jobsDir,
    seekersDir,
    jobsOutFile,
    seekersOutFile,
    repositoryUrl: "https://gitlab.com/owasp-blt/blt-jobs",
    sourceRef: "main",
  });

  const data = JSON.parse(fs.readFileSync(jobsOutFile, "utf8"));
  assert.equal(data.count, 1);
  assert.equal(data.source.provider.id, "gitlab");

  const job = data.jobs[0];
  assert.equal(job.source_platform, "gitlab");
  assert.equal(job.source_file_path, "jobs/acme-security-engineer.md");
  assert.equal(
    job.source_file_url,
    "https://gitlab.com/owasp-blt/blt-jobs/-/blob/main/jobs/acme-security-engineer.md"
  );
  assert.equal(job.source_issue_url, "https://gitlab.com/owasp-blt/blt-jobs/-/issues/123");
  assert.equal(job.review_status, "published");
  assert.equal(job.application_mode, "external_url");
  assert.equal(job.public_contact_policy, "external_apply");
});

test("buildAll emits GitLab source traceability and privacy defaults for seekers", () => {
  const root = tempDir();
  const jobsDir = path.join(root, "jobs");
  const seekersDir = path.join(root, "seekers");
  const jobsOutFile = path.join(root, "public", "data", "jobs.json");
  const seekersOutFile = path.join(root, "public", "data", "seekers.json");

  writeFile(
    path.join(seekersDir, "jane-doe.md"),
    `---
name: "Jane Doe"
headline: "Security researcher"
gitlab: "https://gitlab.com/janedoe"
email: "jane@example.com"
source_issue_url: "https://gitlab.com/owasp-blt/blt-jobs/-/issues/456"
created_at: "2026-01-03T00:00:00Z"
---

## About Me

I test software.
`
  );

  buildAll({
    jobsDir,
    seekersDir,
    jobsOutFile,
    seekersOutFile,
    repositoryUrl: "https://gitlab.com/owasp-blt/blt-jobs",
    sourceRef: "main",
  });

  const data = JSON.parse(fs.readFileSync(seekersOutFile, "utf8"));
  assert.equal(data.count, 1);
  assert.equal(data.source.provider.id, "gitlab");

  const seeker = data.seekers[0];
  assert.equal(seeker.source_platform, "gitlab");
  assert.equal(seeker.source_file_path, "seekers/jane-doe.md");
  assert.equal(
    seeker.source_file_url,
    "https://gitlab.com/owasp-blt/blt-jobs/-/blob/main/seekers/jane-doe.md"
  );
  assert.equal(seeker.source_issue_url, "https://gitlab.com/owasp-blt/blt-jobs/-/issues/456");
  assert.equal(seeker.review_status, "published");
  assert.equal(seeker.contact_method, "email");
  assert.equal(seeker.public_contact_policy, "public_email");
});
