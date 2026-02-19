#!/usr/bin/env node
/**
 * Parse GitHub issue form body (### Label\n\nvalue) and write jobs/<slug>.md with YAML frontmatter.
 * Used by process-submissions.yml for [JOB] form issues.
 * Reads issue body from stdin or FIRST argument.
 */
const fs = require("fs");
const path = require("path");

const JOBS_DIR = path.join(__dirname, "..", "jobs");

function parseFormBody(body) {
  const data = {};
  const sections = body.split(/\n### /).filter(Boolean);
  for (const section of sections) {
    const firstNewline = section.indexOf("\n");
    let label = (firstNewline === -1 ? section : section.slice(0, firstNewline)).trim().replace(/\s*\(Optional\)\s*$/, "");
    label = label.replace(/^#+\s*/, "").trim();
    let value = firstNewline === -1 ? "" : section.slice(firstNewline).replace(/^\n+/, "");
    value = value.split(/\n\n###/)[0].trim();
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
  const applicationUrl = website || "";

  const descriptionBody = [description, requirements ? `## Requirements\n\n${requirements}` : "", howToApply ? `## How to Apply\n\n${howToApply}` : "", additionalInfo ? `## Additional Information\n\n${additionalInfo}` : ""].filter(Boolean).join("\n\n");

  const frontmatter = {
    title: title || "Untitled",
    organization_name: company || "Company",
    organization_logo: "",
    location: location || "",
    job_type: jobType || "full-time",
    salary_range: salaryRange || "",
    expires_at: "",
    application_email: "",
    application_url: applicationUrl || "",
    application_instructions: howToApply || "",
    requirements: requirements || "",
    created_at: created,
    views_count: 0,
  };

  const lines = ["---"];
  for (const [k, v] of Object.entries(frontmatter)) {
    const s = String(v).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, " ");
    lines.push(`${k}: "${s}"`);
  }
  lines.push("---", "", descriptionBody);

  fs.mkdirSync(JOBS_DIR, { recursive: true });
  fs.writeFileSync(outPath, lines.join("\n"), "utf8");
  console.log(path.relative(process.cwd(), outPath));
}

main();
