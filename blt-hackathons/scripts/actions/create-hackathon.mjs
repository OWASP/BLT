#!/usr/bin/env node
// Adds a hackathon to public/js/hackathons-config.js from a `hackathon-creation` issue form,
// commits it to main, comments on the issue and closes it.
// Run by .forkmesh/blt-hackathons--create-hackathon.yml (ported from the GitHub workflow of the same name).
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { readEvent, comment, closeIssue, commitBack, run } from "../../../scripts/actions/forge.mjs";

const PROJECT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const CONFIG = "public/js/hackathons-config.js";
const NO_RESPONSE = "_No response_";
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Value under a `### Heading` of the issue form body. */
export function extractField(body, heading) {
  const match = body.match(new RegExp(`###\\s+${escapeRe(heading)}\\s*\\n([\\s\\S]*?)(?=\\n###|$)`, "i"));
  return match ? match[1].trim() : "";
}

/** Validates the form and builds the config entry. Returns {error} or {slug, name, entry, prizesWarning}. */
export function buildEntry(body) {
  const name = extractField(body, "Hackathon Name");
  const slug = extractField(body, "Slug (URL identifier)");
  const description = extractField(body, "Description");
  const startTime = extractField(body, "Start Date & Time (ISO 8601)");
  const endTime = extractField(body, "End Date & Time (ISO 8601)");
  const bannerRaw = extractField(body, "Banner Image");
  const providerRaw = extractField(body, "Source Control Provider");
  const organization = extractField(body, "GitHub Organization (optional)");
  const gitlabUrlRaw = extractField(body, "GitLab URL (optional)");
  const gitlabGroup = extractField(body, "GitLab Group (optional)");
  const reposRaw = extractField(body, "Repositories (one per line, optional)");
  const rulesRaw = extractField(body, "Rules (optional)");
  const prizesRaw = extractField(body, "Prizes JSON (optional)");

  const missing = [];
  if (!name) missing.push("Hackathon Name");
  if (!slug) missing.push("Slug");
  if (!description) missing.push("Description");
  if (!startTime) missing.push("Start Date & Time");
  if (!endTime) missing.push("End Date & Time");
  if (missing.length > 0) {
    return {
      error: `❌ Could not create hackathon — the following required fields are missing or empty:\n\n${missing.map((f) => `- **${f}**`).join("\n")}\n\nPlease edit the issue and fill in all required fields.`,
      reason: "Missing required fields: " + missing.join(", "),
    };
  }
  if (!/^[a-z0-9-]+$/.test(slug)) {
    return {
      error: `❌ The slug **"${slug}"** is invalid. Slugs may only contain lowercase letters, numbers, and hyphens.`,
      reason: "Invalid slug: " + slug,
    };
  }
  const iso8601Re = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
  const startMs = Date.parse(startTime);
  const endMs = Date.parse(endTime);
  if (!iso8601Re.test(startTime) || isNaN(startMs)) {
    return {
      error: "❌ **Start Date & Time** is not a valid ISO 8601 date (expected format: `YYYY-MM-DDTHH:MM:SSZ`).",
      reason: "Invalid start date: " + startTime,
    };
  }
  if (!iso8601Re.test(endTime) || isNaN(endMs)) {
    return {
      error: "❌ **End Date & Time** is not a valid ISO 8601 date (expected format: `YYYY-MM-DDTHH:MM:SSZ`).",
      reason: "Invalid end date: " + endTime,
    };
  }
  if (endMs <= startMs) {
    return { error: "❌ **End Date** must be after **Start Date**.", reason: "End date is not after start date" };
  }

  const imgMatch = bannerRaw.match(/!\[.*?\]\((https?:\/\/[^\s)]+)\)/);
  const bannerImage = imgMatch ? imgMatch[1] : "";
  const repositories = reposRaw ? reposRaw.split("\n").map((r) => r.trim()).filter((r) => r.length > 0) : [];
  const provider = providerRaw === "GitLab" ? "gitlab" : "github";
  const gitlabUrl = gitlabUrlRaw && gitlabUrlRaw !== NO_RESPONSE ? gitlabUrlRaw : "https://gitlab.com";

  let prizes = [];
  let prizesWarning = "";
  if (prizesRaw && prizesRaw !== NO_RESPONSE) {
    try {
      prizes = JSON.parse(prizesRaw);
    } catch (e) {
      prizesWarning = `\n\n⚠️ The **Prizes JSON** field could not be parsed (${e.message}) — prizes have been set to an empty array. You can edit the config manually to add prizes.`;
      console.warn("Could not parse prizes JSON:", e.message);
    }
  }

  const reposArray = repositories.length > 0
    ? `[\n                    ${repositories.map((r) => JSON.stringify(r)).join(",\n                    ")}\n                ]`
    : "[]";
  const prizesArray = prizes.length > 0 ? JSON.stringify(prizes, null, 4).replace(/^/gm, "            ") : "[]";
  // The leading comma fixes the old workflow, which wrote `}\n bannerImage: ...` (a syntax error).
  const bannerLine = bannerImage ? `,\n            // Banner image\n            bannerImage: ${JSON.stringify(bannerImage)}` : "";
  const orgLine = organization && organization !== NO_RESPONSE
    ? `\n                // Organization field - all repos in this org will be tracked\n                organization: ${JSON.stringify(organization)},`
    : "";
  const gitlabGroupLine = gitlabGroup && gitlabGroup !== NO_RESPONSE
    ? `\n                // Group field - all projects in this group will be tracked\n                group: ${JSON.stringify(gitlabGroup)},`
    : "";
  const providerLine = provider === "gitlab" ? `\n            provider: "gitlab",` : "";
  const sourceControlBlock = provider === "gitlab"
    ? `gitlab: {
              url: ${JSON.stringify(gitlabUrl)},${gitlabGroupLine}
              projects: ${reposArray}
          }`
    : `github: {
              token: "",${orgLine}
              repositories: ${reposArray}
          }`;
  const rulesValue = rulesRaw && rulesRaw !== NO_RESPONSE ? rulesRaw : "";

  // Every value from the issue goes into the config as a JSON string literal. The config is a JS file
  // that scripts/parse_hackathons_config.js evals (with the update-stats tokens in the environment)
  // and browsers run, so a template literal here let `${...}` or a `\` before a backtick run code.

  const entry = `
          {
          slug: ${JSON.stringify(slug)},
          name: ${JSON.stringify(name)},
          description: ${JSON.stringify(description)},
          rules: ${JSON.stringify(rulesValue)},
          startTime: ${JSON.stringify(startTime)},
          endTime: ${JSON.stringify(endTime)},
          ${providerLine}
          ${sourceControlBlock},
          prizes: ${prizesArray},
          sponsors: [],
          display: {
              showRepoStats: true,
              maxLeaderboardEntries: 10,
              showPRsInLeaderboard: true,
              showReviewsInLeaderboard: true
          }${bannerLine}
          }`;
  return { slug, name, entry, prizesWarning };
}

/** Inserts the entry at the start of the hackathons array. Returns {error} or {config}. */
export function insertEntry(config, slug, entry) {
  if (new RegExp(`slug:\\s*${escapeRe(JSON.stringify(slug))}`).test(config)) {
    return {
      error: `❌ A hackathon with slug **"${slug}"** already exists. Please choose a different slug.`,
      reason: "Duplicate slug: " + slug,
    };
  }
  const updated = config.replace(/hackathons:\s*\[/, `hackathons: [${entry},`);
  if (updated === config) {
    return {
      error: "❌ Could not insert hackathon into the config file — the expected `hackathons: [` marker was not found. Please check the config file format.",
      reason: "Config file does not contain expected hackathons array marker",
    };
  }
  return { config: updated };
}

async function main() {
  const event = readEvent();
  const issue = event.issue;
  if (!issue) throw new Error("no issue in the event payload");
  const n = issue.number;
  const body = issue.body || "";

  await comment(n, "👀 Your hackathon request has been received and is being processed. We'll update this issue once it's been added to the platform.");

  const fail = async ({ error, reason }) => {
    await comment(n, error);
    console.error(reason);
    process.exit(1);
  };

  const built = buildEntry(body);
  if (built.error) return fail(built);
  const configPath = join(PROJECT, CONFIG);
  const inserted = insertEntry(readFileSync(configPath, "utf8"), built.slug, built.entry);
  if (inserted.error) return fail(inserted);
  writeFileSync(configPath, inserted.config, "utf8");
  console.log(`Hackathon "${built.name}" (${built.slug}) added to config.`);

  commitBack({
    cwd: PROJECT,
    message: `blt-hackathons: add hackathon ${built.slug} (issue #${n})`,
    paths: [CONFIG],
    deploy: "blt-hackathons",
  });

  await comment(n, `✅ Hackathon **${built.name}** has been successfully added to the platform!\n\nSlug: \`${built.slug}\`\n\nIt will appear on the site after the next deployment.${built.prizesWarning}`);
  await closeIssue(n);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) run(main);
