#!/usr/bin/env node

const fs = require("fs");

const configSource = fs.readFileSync("public/js/hackathons-config.js", "utf8");
const hackathonHtml = fs.readFileSync("public/hackathon.html", "utf8");
const themeCss = fs.readFileSync("public/css/blt-theme.css", "utf8");
const indexHtml = fs.readFileSync("public/index.html", "utf8");
const dataPath = "public/hackathon-data/gsoc-2027-warmup.json";
const summaryPath = "public/hackathon-data/gsoc-2027-warmup-summary.json";

const HACKATHONS_CONFIG = eval(`${configSource}\nHACKATHONS_CONFIG`);

const requiredProjects = [
  "owasp-blt/blt",
  "owasp-blt/blt-action",
  "owasp-blt/blt-api",
  "owasp-blt/blt-autopatch",
  "owasp-blt/blt-byte",
  "owasp-blt/blt-cve",
  "owasp-blt/blt-dash",
  "owasp-blt/blt-design",
  "owasp-blt/blt-design-contest",
  "owasp-blt/blt-docs",
  "owasp-blt/blt-enforcement",
  "owasp-blt/blt-extension",
  "owasp-blt/blt-flutter",
  "owasp-blt/blt-gitcaster",
  "owasp-blt/blt-gsoc",
  "owasp-blt/blt-hackathons",
  "owasp-blt/blt-hackerhouse",
  "owasp-blt/blt-ideas",
  "owasp-blt/blt-jobs",
  "owasp-blt/blt-ketchup",
  "owasp-blt/blt-leaf",
  "owasp-blt/blt-lettuce",
  "owasp-blt/blt-mayo",
  "owasp-blt/blt-mcp",
  "owasp-blt/blt-monitor",
  "owasp-blt/blt-netguardian",
  "owasp-blt/blt-netguardian-client",
  "owasp-blt/blt-newsletter",
  "owasp-blt/blt-next",
  "owasp-blt/blt-nexus",
  "owasp-blt/blt-ossh",
  "owasp-blt/blt-owasp-bumper",
  "owasp-blt/blt-owasp-metadata",
  "owasp-blt/blt-owasp-projects",
  "owasp-blt/blt-owasp-wich",
  "owasp-blt/blt-pages",
  "owasp-blt/blt-panini",
  "owasp-blt/blt-pool",
  "owasp-blt/blt-preflight",
  "owasp-blt/blt-profiles",
  "owasp-blt/blt-rewards",
  "owasp-blt/blt-safecloak",
  "owasp-blt/blt-sammich",
  "owasp-blt/blt-sizzle",
  "owasp-blt/blt-start",
  "owasp-blt/blt-timer-flutter",
  "owasp-blt/blt-timer-web",
  "owasp-blt/blt-toasty",
  "owasp-blt/blt-tomato",
  "owasp-blt/blt-university",
  "owasp-blt/blt-vanish",
  "owasp-blt/blt-vanish-flutter",
  "owasp-blt/blt-waypoint",
  "owasp-blt/blt-zero",
  "owasp-blt/coderabbit",
  "owasp-blt/dot_github",
  "owasp-blt/my-gsoc-tool",
];

const failures = [];
const gsoc2027 = HACKATHONS_CONFIG.hackathons.find(
  (hackathon) => hackathon.slug === "gsoc-2027-warmup",
);

if (!gsoc2027) {
  failures.push("missing gsoc-2027-warmup hackathon");
} else {
  if (gsoc2027.provider !== "gitlab") {
    failures.push("gsoc-2027-warmup must use provider=gitlab");
  }
  if (gsoc2027.gitlab?.url !== "https://gitlab.com") {
    failures.push("gsoc-2027-warmup must point at https://gitlab.com");
  }
  if (gsoc2027.gitlab?.group !== "owasp-blt") {
    failures.push("gsoc-2027-warmup must use the owasp-blt GitLab group");
  }
  const projects = gsoc2027.gitlab?.projects || [];
  const missing = requiredProjects.filter((project) => !projects.includes(project));
  if (missing.length > 0) {
    failures.push(`gsoc-2027-warmup missing GitLab projects: ${missing.join(", ")}`);
  }
  if (projects.length < requiredProjects.length) {
    failures.push(
      `gsoc-2027-warmup has ${projects.length} projects; expected at least ${requiredProjects.length}`,
    );
  }
}

if (HACKATHONS_CONFIG.global.organizationUrl !== "https://gitlab.com/owasp-blt") {
  failures.push("global organizationUrl must point to the OWASP-BLT GitLab group");
}

if (!fs.existsSync(dataPath)) {
  failures.push(`${dataPath} must exist`);
} else {
  const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));
  if (data.provider !== "gitlab") {
    failures.push(`${dataPath} must use provider=gitlab`);
  }
  const missing = requiredProjects.filter((project) => !data.repositories?.includes(project));
  if (missing.length > 0) {
    failures.push(`${dataPath} missing repositories: ${missing.join(", ")}`);
  }
}

if (!fs.existsSync(summaryPath)) {
  failures.push(`${summaryPath} must exist`);
} else {
  const summary = JSON.parse(fs.readFileSync(summaryPath, "utf8"));
  if (summary.provider !== "gitlab") {
    failures.push(`${summaryPath} must use provider=gitlab`);
  }
  if (summary.repositories < requiredProjects.length) {
    failures.push(
      `${summaryPath} tracks ${summary.repositories} repositories; expected at least ${requiredProjects.length}`,
    );
  }
}

const statColorChecks = [
  {
    name: "dashboard stat numbers",
    source: hackathonHtml,
    selector: /\.dash-stat strong\s*{[^}]*color:\s*#111827;/s,
  },
  {
    name: "platform stat numbers",
    source: themeCss,
    selector: /\.blt-stat-card span\s*{[^}]*color:\s*var\(--blt-text\);/s,
  },
  {
    name: "inline hero stat numbers",
    source: indexHtml,
    selector: /\.hero-stat strong\s*{[^}]*color:\s*#111827;/s,
  },
];

statColorChecks.forEach(({ name, source, selector }) => {
  if (!selector.test(source)) {
    failures.push(`${name} must use black text`);
  }
});

const forbiddenPublicProjectUrls = [
  "https://github.com/OWASP-BLT/BLT-Hackathons",
  "https://github.com/OWASP-BLT/BLT-Hackathons/issues",
];

forbiddenPublicProjectUrls.forEach((url) => {
  if (indexHtml.includes(url) || hackathonHtml.includes(url)) {
    failures.push(`public pages must use GitLab instead of ${url}`);
  }
});

if (failures.length > 0) {
  console.error("GSOC 2027 contract validation failed:");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log("GSOC 2027 contract validation passed.");
