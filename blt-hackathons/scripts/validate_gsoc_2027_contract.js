#!/usr/bin/env node

const fs = require("fs");

const configSource = fs.readFileSync("public/js/hackathons-config.js", "utf8");
const hackathonHtml = fs.readFileSync("public/hackathon.html", "utf8");
const themeCss = fs.readFileSync("public/css/blt-theme.css", "utf8");
const indexHtml = fs.readFileSync("public/index.html", "utf8");
const dataPath = "public/hackathon-data/gsoc-2027-warmup.json";
const summaryPath = "public/hackathon-data/gsoc-2027-warmup-summary.json";

const HACKATHONS_CONFIG = eval(`${configSource}\nHACKATHONS_CONFIG`);

// The gitlab.com/owasp-blt projects the event was announced with, now folders of the BLT
// monorepo on git.owaspblt.org (owasp-blt/blt is blt-legacy, formerly blt-core). blt-timer-web and
// blt-timer-flutter are now blt-timer; blt-vanish-flutter and dot_github were removed.
const requiredFolders = [
  "blt-legacy", "blt-action", "blt-api", "blt-autopatch", "blt-byte", "blt-cve", "blt-dash",
  "blt-design", "blt-design-contest", "blt-docs", "blt-enforcement", "blt-extension",
  "blt-flutter", "blt-gitcaster", "blt-gsoc", "blt-hackathons", "blt-hackerhouse", "blt-ideas",
  "blt-jobs", "blt-ketchup", "blt-leaf", "blt-lettuce", "blt-mayo", "blt-mcp", "blt-monitor",
  "blt-netguardian", "blt-netguardian-client", "blt-newsletter", "blt-next", "blt-nexus",
  "blt-ossh", "blt-owasp-bumper", "blt-owasp-metadata", "blt-owasp-projects", "blt-owasp-wich",
  "blt-pages", "blt-panini", "blt-pool", "blt-preflight", "blt-profiles", "blt-rewards",
  "blt-safecloak", "blt-sammich", "blt-sizzle", "blt-start", "blt-timer",
  "blt-toasty", "blt-tomato", "blt-university", "blt-vanish",
  "blt-waypoint", "blt-zero", "coderabbit", "my-gsoc-tool",
];

const failures = [];
const gsoc2027 = HACKATHONS_CONFIG.hackathons.find(
  (hackathon) => hackathon.slug === "gsoc-2027-warmup",
);

if (!gsoc2027) {
  failures.push("missing gsoc-2027-warmup hackathon");
} else {
  if (gsoc2027.provider !== "forkmesh") {
    failures.push("gsoc-2027-warmup must use provider=forkmesh");
  }
  if (gsoc2027.forkmesh?.url !== "https://git.owaspblt.org") {
    failures.push("gsoc-2027-warmup must point at https://git.owaspblt.org");
  }
  if (gsoc2027.forkmesh?.owner !== "owasp-blt" || gsoc2027.forkmesh?.repo !== "BLT") {
    failures.push("gsoc-2027-warmup must read the owasp-blt/BLT repository");
  }
  const paths = gsoc2027.forkmesh?.paths || [];
  const missing = requiredFolders.filter((folder) => !paths.includes(folder));
  if (missing.length > 0) {
    failures.push(`gsoc-2027-warmup missing project folders: ${missing.join(", ")}`);
  }
  if (gsoc2027.trackSlack !== true || !gsoc2027.slackUsersFile) {
    failures.push("gsoc-2027-warmup must track Slack activity (trackSlack, slackUsersFile)");
  } else if (!fs.existsSync(gsoc2027.slackUsersFile)) {
    failures.push(`${gsoc2027.slackUsersFile} must exist`);
  }
}

if (HACKATHONS_CONFIG.global.organizationUrl !== "https://git.owaspblt.org/BLT") {
  failures.push("global organizationUrl must point to https://git.owaspblt.org/BLT");
}

for (const path of [dataPath, summaryPath]) {
  if (!fs.existsSync(path)) {
    failures.push(`${path} must exist`);
    continue;
  }
  const data = JSON.parse(fs.readFileSync(path, "utf8"));
  if (data.provider !== "forkmesh") {
    failures.push(`${path} must use provider=forkmesh`);
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

// gitlab.com/owasp-blt is closed: the pages must not send anyone there.
[["index.html", indexHtml], ["hackathon.html", hackathonHtml]].forEach(([name, html]) => {
  if (/gitlab\.com\/owasp-blt/i.test(html)) {
    failures.push(`public/${name} must not link to gitlab.com/owasp-blt`);
  }
});

if (failures.length > 0) {
  console.error("GSOC 2027 contract validation failed:");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log("GSOC 2027 contract validation passed.");
