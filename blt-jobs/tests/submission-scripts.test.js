const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const test = require("node:test");

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "blt-jobs-submit-"));
}

function runNode(script, input, env) {
  return execFileSync(process.execPath, [script, input], {
    cwd: path.join(__dirname, ".."),
    env: { ...process.env, ...env },
    encoding: "utf8",
  }).trim();
}

function readOutputFile(root, relativeFile) {
  return fs.readFileSync(path.join(root, relativeFile), "utf8");
}

test("issue-form-to-job writes GitLab source and public contact metadata", () => {
  const root = tempDir();
  const body = `## Company Name
Acme

## Company Website
https://acme.example

## Job Title
Security Engineer

## Location
Remote

## Job Type
Full-time

## How to Apply
Apply at https://acme.example/jobs/security-engineer
`;

  const relativeFile = runNode("scripts/issue-form-to-job.js", body, {
    BLT_JOBS_DIR: path.join(root, "jobs"),
    ISSUE_USER: "janedoe",
    ISSUE_USER_URL: "https://gitlab.com/janedoe",
    ISSUE_URL: "https://gitlab.com/owasp-blt/blt-jobs/-/issues/123",
  });

  const output = readOutputFile(root, relativeFile);
  assert.match(output, /source_platform: "gitlab"/);
  assert.match(output, /source_issue_url: "https:\/\/gitlab\.com\/owasp-blt\/blt-jobs\/-\/issues\/123"/);
  assert.match(output, /submission_type: "issue"/);
  assert.match(output, /review_status: "submitted"/);
  assert.match(output, /application_mode: "external_url"/);
  assert.match(output, /public_contact_policy: "external_apply"/);
});

test("issue-form-to-seeker writes GitLab source and public email metadata", () => {
  const root = tempDir();
  const body = `## Personal Information
**Name:** Jane Doe
**Location:** Remote
**Preferred Job Type:** Full-time

## Professional Information
**Current Title/Role:** Security Researcher
**Years of Experience:** 5
**Availability:** Open

## Contact & Links
**GitLab:** https://gitlab.com/janedoe
**Email:** jane@example.com
`;

  const relativeFile = runNode("scripts/issue-form-to-seeker.js", body, {
    BLT_SEEKERS_DIR: path.join(root, "seekers"),
    ISSUE_URL: "https://gitlab.com/owasp-blt/blt-jobs/-/issues/456",
  });

  const output = readOutputFile(root, relativeFile);
  assert.match(output, /source_platform: "gitlab"/);
  assert.match(output, /source_issue_url: "https:\/\/gitlab\.com\/owasp-blt\/blt-jobs\/-\/issues\/456"/);
  assert.match(output, /submission_type: "issue"/);
  assert.match(output, /review_status: "submitted"/);
  assert.match(output, /contact_method: "email"/);
  assert.match(output, /public_contact_policy: "public_email"/);
});
