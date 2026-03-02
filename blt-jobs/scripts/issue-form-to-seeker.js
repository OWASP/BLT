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
  
  // First, extract **Label:** value pairs (these are within sections)
  const boldRegex = /\*\*([^*]+):\*\*\s*([^\n]+)/g;
  let m;
  while ((m = boldRegex.exec(body)) !== null) {
    const label = m[1].trim();
    const value = m[2].trim();
    data[label] = value;
  }
  
  // Then extract ## Section content (for multi-line sections)
  const sectionRegex = /## ([^\n]+)\n((?:(?!## ).|\n)*)/g;
  while ((m = sectionRegex.exec(body)) !== null) {
    const label = m[1].trim().replace(/\s*\(Optional\)\s*$/, "");
    let value = m[2].trim();
    
    // Skip if this section only contains **Label:** pairs (already extracted)
    if (!value.match(/^\*\*[^*]+:\*\*/)) {
      // Only set if not already set by **Label:** extraction
      if (!data[label]) {
        data[label] = value;
      }
    }
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

function extractLinks(data) {
  const links = {
    github: "",
    linkedin: "",
    portfolio: "",
    email: "",
    twitter: "",
    resume: ""
  };
  
  // Extract from individual fields
  links.github = (data["GitHub"] || "").trim().replace(/^[(\s]+|[)\s]+$/g, "");
  links.linkedin = (data["LinkedIn"] || "").trim().replace(/^[(\s]+|[)\s]+$/g, "");
  links.portfolio = (data["Portfolio/Website"] || "").trim().replace(/^[(\s]+|[)\s]+$/g, "");
  links.email = (data["Email"] || "").trim().replace(/^[(\s]+|[)\s]+$/g, "");
  links.twitter = (data["Twitter/X"] || "").trim().replace(/^[(\s]+|[)\s]+$/g, "");
  links.resume = (data["Resume"] || "").trim().replace(/^[(\s]+|[)\s]+$/g, "");
  
  return links;
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
  const workExperience = (d["Work Experience"] || d["Experience Highlights"] || "").trim();
  const projects = (d["Projects & Portfolio"] || "").trim();
  const certifications = (d["Certifications & Education"] || "").trim();
  const workSamples = (d["Work Samples"] || "").trim();
  const lookingFor = (d["What I'm Looking For"] || "").trim();
  
  const links = extractLinks(d);

  const experienceSummary = experience ? `${experience} years` : "";

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
    experience_years: experience || "",
    experience_summary: experienceSummary || "",
    availability: availability || "",
    github: links.github || "",
    linkedin: links.linkedin || "",
    portfolio: links.portfolio || "",
    email: links.email || "",
    twitter: links.twitter || "",
    resume_url: links.resume || "",
    created_at: created,
  };

  const bodyParts = [];
  if (about) bodyParts.push(`## About Me\n\n${about}`);
  if (workExperience) bodyParts.push(`## Work Experience\n\n${workExperience}`);
  if (projects) bodyParts.push(`## Projects & Portfolio\n\n${projects}`);
  if (certifications) bodyParts.push(`## Certifications & Education\n\n${certifications}`);
  if (workSamples) bodyParts.push(`## Work Samples\n\n${workSamples}`);
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
