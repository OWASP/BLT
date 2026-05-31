#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const outDir = path.join(root, ".worker-assets");
const publicEntries = [
  "404.html",
  "add.html",
  "assets",
  "data/jobs.json",
  "data/seekers.json",
  "index.html",
  "job.html",
  "jobs.html",
  "leaderboard.html",
  "saved-jobs.html",
  "seeker.html",
  "seekers.html",
];

fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, ".gitkeep"), "");

for (const entry of publicEntries) {
  fs.cpSync(path.join(root, entry), path.join(outDir, entry), { recursive: true });
}

console.log(`Prepared ${publicEntries.length} public entries in ${path.relative(root, outDir)}`);
