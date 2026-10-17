#!/usr/bin/env node
/**
 * Parse GitLab issue template body (### Label\n\nvalue) and write jobs/<slug>.md with YAML frontmatter.
 * Reads issue body from stdin or FIRST argument.
 */
const fs = require("fs");
const path = require("path");

const JOBS_DIR = process.env.BLT_JOBS_DIR || path.join(__dirname, "..", "jobs");

function parseFormBody(body) {
  const data = {};
  const sections = body.split(/\n##+ /).filter(Boolean);
  for (const section of sections) {
    const firstNewline = section.indexOf("\n");
    let label = (firstNewline === -1 ? section : section.slice(0, firstNewline)).trim().replace(/\s*\(Optional\)\s*$/, "");
    label = label.replace(/^#+\s*/, "").trim();
    let value = firstNewline === -1 ? "" : section.slice(firstNewline).replace(/^\n+/, "");
    value = value.split(/\n\n##+/)[0].trim();
    data[label] = value;
  }
  return data;
}

function slugify(s) {
  return (s || "")
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/[-\s]+/g, "-")
    .replace(/^-|-$/g, "")
    || "job";
}

function extractFirstUrl(value) {
  const match = String(value || "").match(/https?:\/\/[^\s)>\]]+/i);
  return match ? match[0].replace(/[.,]+$/, "") : "";
}

function extractFirstEmail(value) {
  const match = String(value || "").match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  return match ? match[0].replace(/[.,]+$/, "") : "";
}

function inferApplicationMode(applicationUrl, applicationEmail, instructions) {
  if (applicationUrl) return "external_url";
  if (applicationEmail) return "email";
  if (instructions) return "instructions";
  return "not_provided";
}

function inferPublicContactPolicy(applicationUrl, applicationEmail, instructions) {
  if (applicationEmail) return "public_email";
  if (applicationUrl) return "external_apply";
  if (instructions) return "application_instructions";
  return "not_provided";
}

function outputRelativePath(filePath) {
  return path.relative(path.dirname(JOBS_DIR), filePath);
}

function main() {
  const body = process.argv[2] || fs.readFileSync(0, "utf8");
  const d = parseFormBody(body);

  const company = (d["Company Name"] || d["Company"] || "").trim();
  const title = (d["Job Title"] || d["Title"] || "Untitled").trim();
  const location = (d["Location"] || "").trim();
  const jobType = ((d["Job Type"] || "Full-time").trim()).toLowerCase().replace(/\s+/, "-");
  const salaryRange = (d["Salary Range"] || d["Salary"] || "").trim();
  const description = (d["Job Description"] || d["Description"] || "").trim();
  const requirements = (d["Requirements"] || "").trim();
  const howToApply = (d["How to Apply"] || "").trim();
  const website = (d["Company Website"] || d["Website"] || "").trim();
  const additionalInfo = (d["Additional Information"] || "").trim();

  const orgSlug = slugify(company) || "company";
  const titleSlug = slugify(title).slice(0, 50) || "job";
  let filename = `${orgSlug}-${titleSlug}.md`;
  let outPath = path.join(JOBS_DIR, filename);
  let n = 0;
  while (fs.existsSync(outPath)) {
    n++;
    outPath = path.join(JOBS_DIR, `${orgSlug}-${titleSlug}-${n}.md`);
  }
  filename = path.basename(outPath);

  const created = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  const addedBy = (process.env.ISSUE_USER || "").trim();
  const applicationUrl = extractFirstUrl(howToApply) || website || "";
  const applicationEmail = extractFirstEmail(howToApply);

  const descriptionBody = [description, requirements ? `## Requirements\n\n${requirements}` : "", howToApply ? `## How to Apply\n\n${howToApply}` : "", additionalInfo ? `## Additional Information\n\n${additionalInfo}` : ""].filter(Boolean).join("\n\n");

  const frontmatter = {
    title: title || "Untitled",
    organization_name: company || "Company",
    organization_logo: "",
    location: location || "",
    job_type: jobType || "full-time",
    salary_range: salaryRange || "",
    date_posted: created,
    expires_at: "",
    application_mode: inferApplicationMode(applicationUrl, applicationEmail, howToApply),
    application_email: applicationEmail || "",
    application_url: applicationUrl || "",
    application_instructions: howToApply || "",
    public_contact_policy: inferPublicContactPolicy(applicationUrl, applicationEmail, howToApply),
    requirements: requirements || "",
    created_at: created,
    updated_at: "",
    last_verified_at: "",
    views_count: 0,
    added_by: addedBy || "",
    added_by_url: (process.env.ISSUE_USER_URL || "").trim(),
    source_platform: "gitlab",
    source_issue_url: (process.env.ISSUE_URL || process.env.CI_JOB_URL || "").trim(),
    source_merge_request_url: "",
    source_commit_url: "",
    submission_type: "issue",
    review_status: "submitted",
    reviewed_by: "",
    needs_manual_review: false,
  };

  const lines = ["---"];
  for (const [k, v] of Object.entries(frontmatter)) {
    const s = String(v).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, " ");
    lines.push(`${k}: "${s}"`);
  }
  lines.push("---", "", descriptionBody);

  fs.mkdirSync(JOBS_DIR, { recursive: true });
  fs.writeFileSync(outPath, lines.join("\n"), "utf8");
  console.log(outputRelativePath(outPath));
}

if (require.main === module) {
  main();
}

module.exports = {
  extractFirstEmail,
  extractFirstUrl,
  inferApplicationMode,
  inferPublicContactPolicy,
  parseFormBody,
  slugify,
};
