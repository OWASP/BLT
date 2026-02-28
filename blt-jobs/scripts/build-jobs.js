#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const matter = require("gray-matter");

const JOBS_DIR = path.join(__dirname, "..", "jobs");
const OUT_FILE = path.join(__dirname, "..", "data", "jobs.json");
const SEEKERS_DIR = path.join(__dirname, "..", "seekers");
const SEEKERS_OUT_FILE = path.join(__dirname, "..", "data", "seekers.json");

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
    added_by: get("added_by") || null,
  };
}

function mdToSeeker(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  const stem = path.basename(filePath, ".md");
  const { data: fm, content: body } = matter(content);
  const get = (k, def = null) => (fm[k] !== undefined && fm[k] !== "" ? fm[k] : def);
  return {
    id: stem,
    name: get("name", "Anonymous"),
    headline: get("headline", ""),
    location: get("location", ""),
    skills: get("skills", ""),
    experience_summary: get("experience_summary", ""),
    profile_url: get("profile_url", ""),
    availability: get("availability", ""),
    created_at: get("created_at") || new Date().toISOString(),
    about: (body || "").trim(),
  };
}

function detectDuplicates(jobs) {
  const seen = new Map();
  const duplicates = [];

  for (const job of jobs) {
    const fingerprint = [
      (job.title || "").toLowerCase().trim(),
      (job.organization_name || "").toLowerCase().trim(),
      (job.location || "").toLowerCase().trim(),
    ].join("|");

    if (seen.has(fingerprint)) {
      duplicates.push({
        duplicate: job.id,
        original: seen.get(fingerprint),
        fingerprint,
      });
    } else {
      seen.set(fingerprint, job.id);
    }
  }

  return duplicates;
}

function buildJobs() {
  if (!fs.existsSync(JOBS_DIR)) {
    fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true });
    fs.writeFileSync(
      OUT_FILE,
      JSON.stringify({ jobs: [], count: 0, generated_at: new Date().toISOString() }, null, 2)
    );
  } else {
    const files = fs
      .readdirSync(JOBS_DIR)
      .filter((f) => f.endsWith(".md") && f !== "README.md");
    const jobs = files.map((f) => mdToJob(path.join(JOBS_DIR, f)));

    const duplicates = detectDuplicates(jobs);
    if (duplicates.length > 0) {
      console.warn("\nDuplicate jobs detected:");
      duplicates.forEach((dup) => {
        console.warn(`  ${dup.duplicate} is a duplicate of ${dup.original}`);
      });
      console.warn("  Consider removing duplicate job files.\n");
    }

    const now = new Date();
    const activeJobs = jobs.filter((job) => {
      if (!job.expires_at) return true;
      try {
        const expiryDate = new Date(job.expires_at);
        return expiryDate > now;
      } catch (e) {
        return true;
      }
    });

    const expiredCount = jobs.length - activeJobs.length;
    if (expiredCount > 0) {
      console.log(`Filtered out ${expiredCount} expired job(s)`);
    }

    const out = {
      jobs: activeJobs,
      count: activeJobs.length,
      generated_at: new Date().toISOString(),
    };
    fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true });
    fs.writeFileSync(OUT_FILE, JSON.stringify(out, null, 2));
  }
}

function buildSeekers() {
  if (!fs.existsSync(SEEKERS_DIR)) {
    // If there are no seekers yet, still write an empty JSON so the frontend has a stable shape.
    fs.mkdirSync(path.dirname(SEEKERS_OUT_FILE), { recursive: true });
    fs.writeFileSync(
      SEEKERS_OUT_FILE,
      JSON.stringify({ seekers: [], count: 0, generated_at: new Date().toISOString() }, null, 2)
    );
    return;
  }

  const files = fs
    .readdirSync(SEEKERS_DIR)
    .filter((f) => f.endsWith(".md") && f !== "README.md");
  const seekers = files.map((f) => mdToSeeker(path.join(SEEKERS_DIR, f)));
  const out = {
    seekers,
    count: seekers.length,
    generated_at: new Date().toISOString(),
  };
  fs.mkdirSync(path.dirname(SEEKERS_OUT_FILE), { recursive: true });
  fs.writeFileSync(SEEKERS_OUT_FILE, JSON.stringify(out, null, 2));
}

function main() {
  buildJobs();
  buildSeekers();
}

main();
