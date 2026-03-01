#!/usr/bin/env node
/**
 * Validate job listings and report any that need manual review.
 * Exit with code 1 if any jobs need review (useful for CI/CD).
 */
const fs = require("fs");
const path = require("path");

const JOBS_JSON = path.join(__dirname, "..", "data", "jobs.json");

function main() {
  if (!fs.existsSync(JOBS_JSON)) {
    console.error("❌ Error: jobs.json not found. Run build-jobs.js first.");
    process.exit(1);
  }

  const data = JSON.parse(fs.readFileSync(JOBS_JSON, "utf8"));
  const needsReview = data.jobs.filter(j => j.needs_manual_review);

  if (needsReview.length === 0) {
    console.log("✅ All jobs validated successfully. No manual review needed.");
    process.exit(0);
  }

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

  process.exit(1);
}

main();
