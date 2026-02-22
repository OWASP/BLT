#!/usr/bin/env node
/**
 * Parse GitHub issue body (markdown **Label:** value or ### Label\n\nvalue) and write seekers/<slug>.md.
 * Used by process-submissions.yml for [SEEKER] issues.
 * Reads issue body from stdin or FIRST argument.
 */
const fs = require("fs");
const path = require("path");

const SEEKERS_DIR = path.join(__dirname, "..", "seekers");

function parseFormBody(body) {
  const data = {};
  // ### Label (form-style)
  const formSections = body.split(/\n### /).filter(Boolean);
  for (const section of formSections) {
    const firstNewline = section.indexOf("\n");
    let label = (firstNewline === -1 ? section : section.slice(0, firstNewline)).trim().replace(/\s*\(Optional\)\s*$/, "");
    label = label.replace(/^#+\s*/, "").trim();
    let value = firstNewline === -1 ? "" : section.slice(firstNewline).replace(/^\n+/, "");
    value = value.split(/\n\n###/)[0].trim();
    if (label) data[label] = value;
  }
  // **Label:** value (markdown template style) - only if not already set
  const boldRegex = /\*\*([^*]+):\*\*\s*([^\n]*(?:\n(?!\*\*)[^\n]*)*)/g;
  let m;
  while ((m = boldRegex.exec(body)) !== null) {
    const label = m[1].trim();
    const value = m[2].trim();
    if (!data[label]) data[label] = value;
  }
  return data;
}

function slugify(s) {
  return (s || "")
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/[-\s]+/g, "-")
    .replace(/^-|-$/g, "")
    || "seeker";
}

function main() {
  const body = process.argv[2] || fs.readFileSync(0, "utf8");
  const d = parseFormBody(body);

  const name = (d["Name"] || "").trim() || "Anonymous";
  const headline = (d["Current Title/Role"] || d["Title"] || d["Headline"] || "").trim();
  const location = (d["Location"] || "").trim();
  const skills = (d["Skills"] || "").trim();
  const experience = (d["Years of Experience"] || "").trim();
  const availability = (d["Availability"] || d["Preferred Job Type"] || "").trim();
  const about = (d["About Me"] || "").trim();
  const experienceHighlights = (d["Experience Highlights"] || "").trim();
  const lookingFor = (d["What I'm Looking For"] || "").trim();
  const linkedin = (d["LinkedIn"] || "").trim().replace(/^[(\s]+|[)\s]+$/g, "");
  const github = (d["GitHub"] || "").trim().replace(/^[(\s]+|[)\s]+$/g, "");
  const profileUrl = linkedin || github || "";

  const experienceSummary = experience ? `${experience} experience` : experienceHighlights.slice(0, 200) || "";

  let filename = `${slugify(name)}.md`;
  let outPath = path.join(SEEKERS_DIR, filename);
  let n = 0;
  while (fs.existsSync(outPath)) {
    n++;
    outPath = path.join(SEEKERS_DIR, `${slugify(name)}-${n}.md`);
  }
  filename = path.basename(outPath);

  const created = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");

  const frontmatter = {
    name: name || "Anonymous",
    headline: headline || "",
    location: location || "",
    skills: skills || "",
    experience_summary: experienceSummary || "",
    profile_url: profileUrl || "",
    availability: availability || "",
    created_at: created,
  };

  const bodyParts = [];
  if (about) bodyParts.push(`## About Me\n\n${about}`);
  if (experienceHighlights) bodyParts.push(`## Experience Highlights\n\n${experienceHighlights}`);
  if (lookingFor) bodyParts.push(`## What I'm Looking For\n\n${lookingFor}`);
  const bodyContent = bodyParts.join("\n\n") || "Profile created via issue.";

  const lines = ["---"];
  for (const [k, v] of Object.entries(frontmatter)) {
    const s = String(v).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, " ");
    lines.push(`${k}: "${s}"`);
  }
  lines.push("---", "", bodyContent);

  fs.mkdirSync(SEEKERS_DIR, { recursive: true });
  fs.writeFileSync(outPath, lines.join("\n"), "utf8");
  console.log(path.relative(process.cwd(), outPath));
}

main();
