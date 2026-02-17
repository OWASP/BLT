#!/usr/bin/env node
/**
 * Build data/jobs.json from _jobs/*.md (frontmatter + body).
 * Each job gets id = filename stem (e.g. company-slug-job-title-slug).
 * Output shape: { jobs: [...], count: N, generated_at: "<iso8601>" }
 */

const fs = require("fs");
const path = require("path");
const matter = require("gray-matter");

const JOBS_DIR = path.join(__dirname, "..", "_jobs");
const OUT_FILE = path.join(__dirname, "..", "data", "jobs.json");

function mdToJob(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  const stem = path.basename(filePath, ".md");
  const { data: fm, content: body } = matter(content);
  const get = (k, def = null) => (fm[k] !== undefined && fm[k] !== "" ? fm[k] : def);
  return {
    id: stem,
    organization_name: get("organization_name", "Unknown organization"),
    organization_logo: get("organization_logo") || null,
    title: get("title", "Untitled"),
    description: (body || get("description") || "").trim(),
    requirements: get("requirements") || null,
    location: get("location") || null,
    job_type: get("job_type", "full-time"),
    salary_range: get("salary_range") || null,
    expires_at: get("expires_at") || null,
    application_email: get("application_email") || null,
    application_url: get("application_url") || null,
    application_instructions: get("application_instructions") || null,
    created_at: get("created_at") || new Date().toISOString(),
    views_count: parseInt(get("views_count"), 10) || 0,
  };
}

function main() {
  if (!fs.existsSync(JOBS_DIR)) {
    fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true });
    fs.writeFileSync(
      OUT_FILE,
      JSON.stringify({ jobs: [], count: 0, generated_at: new Date().toISOString() }, null, 2)
    );
    return;
  }
  const files = fs
    .readdirSync(JOBS_DIR)
    .filter((f) => f.endsWith(".md") && f !== "README.md");
  const jobs = files.map((f) => mdToJob(path.join(JOBS_DIR, f)));
  const out = {
    jobs,
    count: jobs.length,
    generated_at: new Date().toISOString(),
  };
  fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true });
  fs.writeFileSync(OUT_FILE, JSON.stringify(out, null, 2));
}

main();
