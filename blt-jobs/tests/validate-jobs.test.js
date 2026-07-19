const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { validateJobsData } = require("../scripts/validate-jobs");

function tempFile(data) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "blt-jobs-validate-"));
  const file = path.join(dir, "jobs.json");
  fs.writeFileSync(file, JSON.stringify(data, null, 2), "utf8");
  return file;
}

test("validateJobsData accepts generated Git-native job metadata", () => {
  const result = validateJobsData({
    jobs: [
      {
        id: "acme-security-engineer",
        title: "Security Engineer",
        organization_name: "Acme",
        application_url: "https://acme.example/jobs/security-engineer",
        needs_manual_review: false,
        source_platform: "gitlab",
        source_file_path: "jobs/acme-security-engineer.md",
        source_file_url: "https://gitlab.com/owasp-blt/blt-jobs/-/blob/main/jobs/acme-security-engineer.md",
        review_status: "published",
        application_mode: "external_url",
        public_contact_policy: "external_apply",
      },
    ],
  });

  assert.deepEqual(result.errors, []);
});

test("validateJobsData rejects invalid source/review/contact contract", () => {
  const result = validateJobsData({
    jobs: [
      {
        id: "bad-job",
        title: "Bad Job",
        organization_name: "Acme",
        application_email: "jobs@example.com",
        needs_manual_review: false,
        source_platform: "unknown",
        source_file_path: "bad-job.md",
        source_file_url: "not-a-url",
        review_status: "done",
        application_mode: "email",
        public_contact_policy: "external_apply",
      },
    ],
  });

  assert(result.errors.some((error) => error.includes("source_platform")));
  assert(result.errors.some((error) => error.includes("source_file_path")));
  assert(result.errors.some((error) => error.includes("source_file_url")));
  assert(result.errors.some((error) => error.includes("review_status")));
  assert(result.errors.some((error) => error.includes("public_contact_policy")));
});
