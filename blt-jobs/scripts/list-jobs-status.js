#!/usr/bin/env node
/**
 * List all jobs with their review status.
 * Useful for getting an overview of the job board.
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
  
  console.log(`\n📋 Job Board Status (${data.count} total jobs)\n`);
  console.log("=" .repeat(80));
  
  data.jobs.forEach((job, index) => {
    const status = job.needs_manual_review ? "⚠️  NEEDS REVIEW" : "✅ Validated";
    console.log(`\n${index + 1}. ${status}`);
    console.log(`   ID: ${job.id}`);
    console.log(`   Title: ${job.title}`);
    console.log(`   Organization: ${job.organization_name}`);
    console.log(`   Location: ${job.location || "Not specified"}`);
    console.log(`   Type: ${job.job_type}`);
    console.log(`   URL: ${job.application_url || "Not specified"}`);
  });
  
  console.log("\n" + "=".repeat(80));
  
  const needsReview = data.jobs.filter(j => j.needs_manual_review).length;
  const validated = data.count - needsReview;
  
  console.log(`\nSummary: ${validated} validated, ${needsReview} need review\n`);
}

main();
