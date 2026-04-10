#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const OUT_FILE = process.env.OUT_FILE || path.join(__dirname, '..', 'data', 'scheduled-crawl-candidates.json');
const MAX_CANDIDATES = Number(process.env.MAX_CANDIDATES || 20);

const SOFTWARE_KEYWORDS = [
  'software',
  'engineer',
  'developer',
  'security',
  'devops',
  'sre',
  'application',
  'backend',
  'frontend',
  'full stack',
  'pentest',
  'cloud',
];

function isSoftwareRole(title = '') {
  const t = String(title).toLowerCase();
  return SOFTWARE_KEYWORDS.some((k) => t.includes(k));
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'User-Agent': 'BLT-Jobs-Scheduled-Crawl/1.0' },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch ${url}: ${res.status}`);
  }

  return await res.json();
}

function normalizeUrl(url) {
  return String(url || '')
    .trim()
    .replace(/#.*$/, '')
    .replace(/\/$/, '');
}

function loadExistingUrls() {
  const jobsFile = path.join(__dirname, '..', 'data', 'jobs.json');
  if (!fs.existsSync(jobsFile)) return new Set();

  const parsed = JSON.parse(fs.readFileSync(jobsFile, 'utf8'));
  const urls = (parsed.jobs || [])
    .map((job) => normalizeUrl(job.application_url))
    .filter(Boolean);

  return new Set(urls);
}

async function pullRemoteOk() {
  const data = await fetchJson('https://remoteok.com/api');
  if (!Array.isArray(data)) return [];

  return data
    .filter((item) => item && item.position)
    .map((item) => ({
      source: 'remoteok',
      title: item.position,
      organization_name: item.company || 'Unknown',
      url: normalizeUrl(item.url),
    }))
    .filter((job) => job.url && isSoftwareRole(job.title));
}

async function pullRemotive() {
  const data = await fetchJson('https://remotive.com/api/remote-jobs');
  const jobs = Array.isArray(data?.jobs) ? data.jobs : [];

  return jobs
    .map((item) => ({
      source: 'remotive',
      title: item.title,
      organization_name: item.company_name || 'Unknown',
      url: normalizeUrl(item.url),
    }))
    .filter((job) => job.url && isSoftwareRole(job.title));
}

async function pullArbeitnow() {
  const data = await fetchJson('https://www.arbeitnow.com/api/job-board-api');
  const jobs = Array.isArray(data?.data) ? data.data : [];

  return jobs
    .map((item) => ({
      source: 'arbeitnow',
      title: item.title,
      organization_name: item.company_name || 'Unknown',
      url: normalizeUrl(item.url),
    }))
    .filter((job) => job.url && isSoftwareRole(job.title));
}

async function main() {
  const existing = loadExistingUrls();

  const [remoteok, remotive, arbeitnow] = await Promise.allSettled([
    pullRemoteOk(),
    pullRemotive(),
    pullArbeitnow(),
  ]);

  const combined = [remoteok, remotive, arbeitnow]
    .filter((result) => result.status === 'fulfilled')
    .flatMap((result) => result.value);

  const uniqueByUrl = new Map();
  for (const job of combined) {
    if (!job.url || existing.has(job.url)) continue;
    if (!uniqueByUrl.has(job.url)) {
      uniqueByUrl.set(job.url, job);
    }
  }

  const candidates = Array.from(uniqueByUrl.values()).slice(0, MAX_CANDIDATES);

  fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true });
  fs.writeFileSync(
    OUT_FILE,
    JSON.stringify({ generated_at: new Date().toISOString(), count: candidates.length, candidates }, null, 2)
  );

  console.log(JSON.stringify({ out_file: OUT_FILE, count: candidates.length }));
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
