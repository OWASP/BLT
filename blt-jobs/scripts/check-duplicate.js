#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const matter = require("gray-matter");

const JOBS_DIR = path.join(__dirname, "..", "jobs");

function normalizeFingerprint(title, org, location) {
  return [
    (title || "").toLowerCase().trim(),
    (org || "").toLowerCase().trim(),
    (location || "").toLowerCase().trim(),
  ].join("|");
}

function checkDuplicate(newJobPath) {
  if (!fs.existsSync(newJobPath)) {
    console.error(`Error: Job file not found: ${newJobPath}`);
    process.exit(1);
  }

  const newContent = fs.readFileSync(newJobPath, "utf8");
  const { data: newFm } = matter(newContent);
  
  const newFingerprint = normalizeFingerprint(
    newFm.title,
    newFm.organization_name,
    newFm.location
  );

  const existingFiles = fs
    .readdirSync(JOBS_DIR)
    .filter((f) => f.endsWith(".md") && f !== "README.md" && f !== path.basename(newJobPath));

  for (const file of existingFiles) {
    const filePath = path.join(JOBS_DIR, file);
    const content = fs.readFileSync(filePath, "utf8");
    const { data: fm } = matter(content);
    
    const existingFingerprint = normalizeFingerprint(
      fm.title,
      fm.organization_name,
      fm.location
    );

    if (newFingerprint === existingFingerprint) {
      console.log(JSON.stringify({
        isDuplicate: true,
        existingFile: file,
        title: fm.title || "Untitled",
        organization: fm.organization_name || "Unknown",
        location: fm.location || "Not specified"
      }));
      process.exit(1);
    }
  }

  console.log(JSON.stringify({ isDuplicate: false }));
  process.exit(0);
}

const jobPath = process.argv[2];
if (!jobPath) {
  console.error("Usage: node check-duplicate.js <path-to-job-file>");
  process.exit(1);
}

checkDuplicate(jobPath);
