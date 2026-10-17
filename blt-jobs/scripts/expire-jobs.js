#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');

const JOBS_DIR = path.join(__dirname, '..', 'jobs');
const DEFAULT_EXPIRY_DAYS = 60;

function parseDate(value) {
  if (!value) return null;
  // Handle native Date objects returned by gray-matter for YAML date fields
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  if (typeof value !== 'string') return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function addDays(date, days) {
  const d = new Date(date.getTime());
  d.setUTCDate(d.getUTCDate() + days);
  return d;
}

function resolveExpiry(frontmatter) {
  const explicit = parseDate(frontmatter.expires_at);
  if (explicit) return explicit;

  const posted =
    parseDate(frontmatter.date_posted) ||
    parseDate(frontmatter.created_at) ||
    parseDate(frontmatter.created) ||
    null;

  if (!posted) return null;
  return addDays(posted, DEFAULT_EXPIRY_DAYS);
}

function main() {
  if (!fs.existsSync(JOBS_DIR)) {
    console.log(JSON.stringify({ expired: [], count: 0 }));
    return;
  }

  const today = new Date();
  const files = fs
    .readdirSync(JOBS_DIR)
    .filter((f) => f.endsWith('.md') && f !== 'README.md');

  const expired = [];

  for (const file of files) {
    const filePath = path.join(JOBS_DIR, file);
    const raw = fs.readFileSync(filePath, 'utf8');
    const { data } = matter(raw);

    const expiry = resolveExpiry(data);
    if (!expiry) continue;

    if (expiry <= today) {
      fs.unlinkSync(filePath);
      expired.push({
        file,
        title: data.title || '',
        organization_name: data.organization_name || '',
        expired_at: expiry.toISOString(),
      });
    }
  }

  console.log(JSON.stringify({ expired, count: expired.length }));
}

main();
