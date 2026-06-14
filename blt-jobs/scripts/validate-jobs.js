#!/usr/bin/env node
/**
 * Validate job listings and report any that need manual review.
 * Exit with code 1 if any jobs need review (useful for CI/CD).
 */
const fs = require("fs");
const path = require("path");

const JOBS_JSON = process.env.BLT_JOBS_JSON || path.join(__dirname, "..", "public", "data", "jobs.json");

const VALID_SOURCE_PLATFORMS = new Set([
  "gitlab",
  "github",
  "gitea",
  "forgejo",
  "codeberg",
  "bitbucket",
  "generic-git",
  "manual",
]);

const VALID_REVIEW_STATUSES = new Set([
  "submitted",
  "needs-info",
  "approved",
  "published",
  "rejected",
  "expired",
  "flagged",
]);

const VALID_APPLICATION_MODES = new Set([
  "external_url",
  "email",
  "git_issue",
  "git_mr",
  "repo_application",
  "instructions",
  "not_provided",
]);

const VALID_PUBLIC_CONTACT_POLICIES = new Set([
  "external_apply",
  "public_email",
  "application_instructions",
  "not_provided",
]);

function isValidUrl(value) {
  if (!value) return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch (error) {
    return false;
  }
}

function validateJobsData(data) {
  const jobs = Array.isArray(data.jobs) ? data.jobs : [];
  const errors = [];
  const needsReview = jobs.filter((j) => j.needs_manual_review);

  for (const job of jobs) {
    const id = job.id || "(missing id)";

    if (!VALID_SOURCE_PLATFORMS.has(job.source_platform)) {
      errors.push(`${id}: source_platform must be one of ${Array.from(VALID_SOURCE_PLATFORMS).join(", ")}`);
    }

    if (!job.source_file_path || !/^jobs\/[^/]+\.md$/.test(String(job.source_file_path))) {
      errors.push(`${id}: source_file_path must point to jobs/<id>.md`);
    }

    if (!isValidUrl(job.source_file_url)) {
      errors.push(`${id}: source_file_url must be an absolute http(s) URL`);
    }

    if (!VALID_REVIEW_STATUSES.has(job.review_status)) {
      errors.push(`${id}: review_status must be one of ${Array.from(VALID_REVIEW_STATUSES).join(", ")}`);
    }

    if (!VALID_APPLICATION_MODES.has(job.application_mode)) {
      errors.push(`${id}: application_mode must be one of ${Array.from(VALID_APPLICATION_MODES).join(", ")}`);
    }

    if (!VALID_PUBLIC_CONTACT_POLICIES.has(job.public_contact_policy)) {
      errors.push(
        `${id}: public_contact_policy must be one of ${Array.from(VALID_PUBLIC_CONTACT_POLICIES).join(", ")}`
      );
    }

    if (job.application_email && job.public_contact_policy !== "public_email") {
      errors.push(`${id}: public_contact_policy must be public_email when application_email is published`);
    }

    if (job.application_url && job.application_mode === "not_provided") {
      errors.push(`${id}: application_mode cannot be not_provided when application_url is set`);
    }
  }

  return { errors, jobs, needsReview };
}

function loadJobsData(filePath = JOBS_JSON) {
  if (!fs.existsSync(filePath)) {
    throw new Error("jobs.json not found. Run build-jobs.js first.");
  }
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function main() {
  let data;
  try {
    data = loadJobsData();
  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    process.exit(1);
  }

  const { errors, needsReview } = validateJobsData(data);

  if (errors.length === 0 && needsReview.length === 0) {
    console.log("✅ All jobs validated successfully. No manual review needed.");
    process.exit(0);
  }

  if (errors.length > 0) {
    console.error("\n⚠️  WARNING: The following jobs violate the Git-native data contract:\n");
    errors.forEach((error) => console.error(`   - ${error}`));
    console.error("");
  }

  if (needsReview.length > 0) {
    console.error("\n⚠️  WARNING: The following jobs need manual review:\n");
    needsReview.forEach(job => {
      console.error(`   Job ID: ${job.id}`);
      console.error(`   Title: ${job.title}`);
      console.error(`   Organization: ${job.organization_name}`);
      console.error(`   URL: ${job.application_url}`);
      console.error(`   Reason: Possible scrape failure detected`);
      console.error("");
    });

    console.error(`Total: ${needsReview.length} job(s) need manual review\n`);
    console.error("Action required:");
    console.error("1. Visit the application URL to verify the job details");
    console.error("2. Manually update the job markdown file in jobs/ directory");
    console.error("3. Set 'needs_manual_review: false' once verified\n");
  }

  process.exit(1);
}

if (require.main === module) {
  main();
}

module.exports = {
  VALID_APPLICATION_MODES,
  VALID_PUBLIC_CONTACT_POLICIES,
  VALID_REVIEW_STATUSES,
  VALID_SOURCE_PLATFORMS,
  loadJobsData,
  validateJobsData,
};
