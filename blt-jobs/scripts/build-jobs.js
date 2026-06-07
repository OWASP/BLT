#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const matter = require("gray-matter");
const { extractSalary } = require("./extract-salary");
const { createProviderConfig } = require("./provider-config");

const DEFAULT_JOBS_DIR = path.join(__dirname, "..", "jobs");
const DEFAULT_OUT_FILE = path.join(__dirname, "..", "public", "data", "jobs.json");
const DEFAULT_SEEKERS_DIR = path.join(__dirname, "..", "seekers");
const DEFAULT_SEEKERS_OUT_FILE = path.join(__dirname, "..", "public", "data", "seekers.json");
const DEFAULT_EXPIRY_DAYS = 60;

function defaultOptions(options = {}) {
  return {
    jobsDir: options.jobsDir || process.env.BLT_JOBS_DIR || DEFAULT_JOBS_DIR,
    jobsOutFile: options.jobsOutFile || process.env.BLT_JOBS_OUT_FILE || DEFAULT_OUT_FILE,
    seekersDir: options.seekersDir || process.env.BLT_SEEKERS_DIR || DEFAULT_SEEKERS_DIR,
    seekersOutFile: options.seekersOutFile || process.env.BLT_SEEKERS_OUT_FILE || DEFAULT_SEEKERS_OUT_FILE,
    provider:
      options.provider ||
      createProviderConfig({
        providerId: options.providerId,
        providerName: options.providerName,
        repositoryUrl: options.repositoryUrl,
        sourceRef: options.sourceRef,
      }),
  };
}

function parseDate(value) {
  if (!value) return null;
  // Handle native Date objects (gray-matter parses YAML dates into Date)
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function addDays(date, days) {
  const d = new Date(date.getTime());
  d.setUTCDate(d.getUTCDate() + days);
  return d;
}

function resolveExpiry(frontmatter) {
  const explicitExpiry = parseDate(frontmatter.expires_at);
  if (explicitExpiry) return explicitExpiry;

  const postedAt =
    parseDate(frontmatter.date_posted) ||
    parseDate(frontmatter.created_at) ||
    parseDate(frontmatter.created) ||
    null;

  if (!postedAt) return null;
  return addDays(postedAt, DEFAULT_EXPIRY_DAYS);
}

function valueFrom(fm) {
  return (k, def = null) => (fm[k] !== undefined && fm[k] !== "" ? fm[k] : def);
}

function sourcePath(kind, filePath) {
  return path.posix.join(kind, path.basename(filePath));
}

function inferApplicationMode(frontmatter) {
  const get = valueFrom(frontmatter);
  const explicit = get("application_mode");
  if (explicit) return explicit;
  if (get("application_url")) return "external_url";
  if (get("application_email")) return "email";
  if (get("application_instructions")) return "instructions";
  return "not_provided";
}

function inferJobContactPolicy(frontmatter) {
  const get = valueFrom(frontmatter);
  const explicit = get("public_contact_policy");
  if (explicit) return explicit;
  if (get("application_email")) return "public_email";
  if (get("application_url")) return "external_apply";
  if (get("application_instructions")) return "application_instructions";
  return "not_provided";
}

function inferSeekerContactMethod(frontmatter) {
  const get = valueFrom(frontmatter);
  const explicit = get("contact_method");
  if (explicit) return explicit;
  if (get("email") || get("public_email")) return "email";
  if (get("profile_url") || get("github") || get("gitlab") || get("linkedin") || get("portfolio")) {
    return "profile_link";
  }
  return "not_provided";
}

function inferSeekerContactPolicy(frontmatter) {
  const get = valueFrom(frontmatter);
  const explicit = get("public_contact_policy");
  if (explicit) return explicit;
  if (get("email") || get("public_email")) return "public_email";
  if (get("profile_url") || get("github") || get("gitlab") || get("linkedin") || get("portfolio")) {
    return "public_profile_links";
  }
  return "not_provided";
}

function sourceFields(fm, provider, kind, filePath) {
  const get = valueFrom(fm);
  const fileSourcePath = get("source_file_path") || sourcePath(kind, filePath);
  const platform = get("source_platform") || provider.id;
  return {
    source_platform: platform,
    source_file_path: fileSourcePath,
    source_file_url: get("source_file_url") || provider.sourceFileUrl(fileSourcePath),
    source_issue_url: get("source_issue_url") || null,
    source_merge_request_url: get("source_merge_request_url") || null,
    source_commit_url: get("source_commit_url") || null,
    submission_type: get("submission_type") || (get("source_issue_url") ? "issue" : "direct_commit"),
    review_status: get("review_status") || "published",
    reviewed_by: get("reviewed_by") || null,
  };
}

function mdToJob(filePath, options = {}) {
  const provider = options.provider || createProviderConfig();
  const content = fs.readFileSync(filePath, "utf8");
  const stem = path.basename(filePath, ".md");
  const { data: fm, content: body } = matter(content);
  const get = valueFrom(fm);

  const description = (body || get("description") || "").trim();
  let salaryRange = get("salary_range") || null;
  if (!salaryRange && description) {
    salaryRange = extractSalary(description);
  }

  const needsReview = get("needs_manual_review") === true || get("needs_manual_review") === "true";

  // FIX: compute effective_expires_at here so the filter below actually works
  const effectiveExpiry = resolveExpiry(fm);

  const addedBy = get("added_by") || null;
  return {
    id: stem,
    organization_name: get("organization_name", "Unknown organization"),
    organization_logo: get("organization_logo") || null,
    organization_website: get("organization_website") || null,
    organization_git_host: get("organization_git_host") || null,
    organization_git_username: get("organization_git_username") || null,
    organization_contact_email: get("organization_contact_email") || null,
    title: get("title", "Untitled"),
    description,
    requirements: get("requirements") || null,
    location: get("location") || null,
    remote_mode: get("remote_mode") || null,
    job_type: get("job_type", "full-time"),
    experience_level: get("experience_level") || null,
    tags: get("tags") || [],
    skills: get("skills") || [],
    salary_range: salaryRange,
    salary_min: get("salary_min") || null,
    salary_max: get("salary_max") || null,
    salary_currency: get("salary_currency") || null,
    salary_period: get("salary_period") || null,
    expires_at: get("expires_at") || null,
    effective_expires_at: effectiveExpiry ? effectiveExpiry.toISOString() : null,
    date_posted: get("date_posted") || null,
    updated_at: get("updated_at") || null,
    last_verified_at: get("last_verified_at") || null,
    application_mode: inferApplicationMode(fm),
    application_email: get("application_email") || null,
    application_url: get("application_url") || null,
    application_repo: get("application_repo") || null,
    application_instructions: get("application_instructions") || null,
    public_contact_policy: inferJobContactPolicy(fm),
    created_at: get("created_at") || new Date().toISOString(),
    views_count: parseInt(get("views_count"), 10) || 0,
    added_by: addedBy,
    // Preserve profile links for listings created before the GitLab migration.
    added_by_url: get("added_by_url") || (addedBy ? `https://github.com/${addedBy}` : null),
    needs_manual_review: needsReview,
    ...sourceFields(fm, provider, "jobs", filePath),
  };
}

function mdToSeeker(filePath, options = {}) {
  const provider = options.provider || createProviderConfig();
  const content = fs.readFileSync(filePath, "utf8");
  const stem = path.basename(filePath, ".md");
  const { data: fm, content: body } = matter(content);
  const get = valueFrom(fm);
  return {
    id: stem,
    name: get("name", "Anonymous"),
    git_username: get("git_username") || null,
    git_platform: get("git_platform") || null,
    email_hash: get("email_hash") || null,
    public_email: get("public_email") || null,
    headline: get("headline", ""),
    location: get("location", ""),
    timezone: get("timezone", ""),
    remote_preference: get("remote_preference", ""),
    skills: get("skills", ""),
    experience_years: get("experience_years", ""),
    experience_summary: get("experience_summary", ""),
    preferred_job_types: get("preferred_job_types", ""),
    target_roles: get("target_roles", ""),
    experience_level: get("experience_level", ""),
    proof_of_work_links: get("proof_of_work_links", ""),
    profile_url: get("profile_url", ""),
    availability: get("availability", ""),
    github: get("github", ""),
    gitlab: get("gitlab", ""),
    linkedin: get("linkedin", ""),
    portfolio: get("portfolio", ""),
    email: get("email", ""),
    twitter: get("twitter", ""),
    resume_url: get("resume_url", ""),
    contact_method: inferSeekerContactMethod(fm),
    public_contact_policy: inferSeekerContactPolicy(fm),
    created_at: get("created_at") || new Date().toISOString(),
    updated_at: get("updated_at") || null,
    about: (body || "").trim(),
    ...sourceFields(fm, provider, "seekers", filePath),
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

function buildJobs(options = {}) {
  const resolved = defaultOptions(options);
  const { jobsDir, jobsOutFile, provider } = resolved;

  if (!fs.existsSync(jobsDir)) {
    fs.mkdirSync(path.dirname(jobsOutFile), { recursive: true });
    fs.writeFileSync(
      jobsOutFile,
      JSON.stringify({ jobs: [], count: 0, generated_at: new Date().toISOString(), ...provider.summary() }, null, 2)
    );
    return [];
  } else {
    const files = fs
      .readdirSync(jobsDir)
      .filter((f) => f.endsWith(".md") && f !== "README.md");
    const jobs = files.map((f) => mdToJob(path.join(jobsDir, f), { provider }));

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
      if (!job.effective_expires_at) return true;
      const expiryDate = parseDate(job.effective_expires_at);
      return expiryDate ? expiryDate > now : true;
    });

    const expiredCount = jobs.length - activeJobs.length;
    if (expiredCount > 0) {
      console.log(`Filtered out ${expiredCount} expired job(s)`);
    }

    const needsReview = jobs.filter((j) => j.needs_manual_review);
    if (needsReview.length > 0) {
      console.warn("\n⚠️  WARNING: The following jobs need manual review (possible scrape failures):");
      needsReview.forEach((j) => {
        console.warn(`   - ${j.id}: ${j.title} (${j.organization_name})`);
      });
      console.warn(`\nTotal jobs needing review: ${needsReview.length}\n`);
    }

    const out = {
      jobs: activeJobs,
      count: activeJobs.length,
      generated_at: new Date().toISOString(),
      ...provider.summary(),
    };
    fs.mkdirSync(path.dirname(jobsOutFile), { recursive: true });
    fs.writeFileSync(jobsOutFile, JSON.stringify(out, null, 2));
    return activeJobs;
  }
}

function buildSeekers(options = {}) {
  const resolved = defaultOptions(options);
  const { seekersDir, seekersOutFile, provider } = resolved;

  if (!fs.existsSync(seekersDir)) {
    fs.mkdirSync(path.dirname(seekersOutFile), { recursive: true });
    fs.writeFileSync(
      seekersOutFile,
      JSON.stringify({ seekers: [], count: 0, generated_at: new Date().toISOString(), ...provider.summary() }, null, 2)
    );
    return [];
  }

  const files = fs
    .readdirSync(seekersDir)
    .filter((f) => f.endsWith(".md") && f !== "README.md");
  const seekers = files.map((f) => mdToSeeker(path.join(seekersDir, f), { provider }));
  const out = {
    seekers,
    count: seekers.length,
    generated_at: new Date().toISOString(),
    ...provider.summary(),
  };
  fs.mkdirSync(path.dirname(seekersOutFile), { recursive: true });
  fs.writeFileSync(seekersOutFile, JSON.stringify(out, null, 2));
  return seekers;
}

function buildAll(options = {}) {
  const resolved = defaultOptions(options);
  const jobs = buildJobs(resolved);
  const seekers = buildSeekers(resolved);
  return { jobs, seekers };
}

function main() {
  buildAll();
}

if (require.main === module) {
  main();
}

module.exports = {
  buildAll,
  buildJobs,
  buildSeekers,
  detectDuplicates,
  mdToJob,
  mdToSeeker,
  parseDate,
  resolveExpiry,
};
