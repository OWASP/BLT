#!/usr/bin/env node
// Adds a sponsor to a hackathon in public/js/hackathons-config.js from a `sponsorship` issue,
// commits it to main, comments on the issue and closes it.
// Run by .forkmesh/blt-hackathons--process-sponsor.yml (ported from the GitHub workflow of the same name).
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import { readEvent, comment, closeIssue, commitBack, run } from "../../../scripts/actions/forge.mjs";

const PROJECT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const CONFIG = "public/js/hackathons-config.js";
const NO_RESPONSE = "_No response_";

/** Value of a `**Label:** value` line of the issue body. */
export function extractField(body, label) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = body.match(new RegExp(`\\*\\*${escaped}:\\*\\*\\s*(.+?)(?:\\r?\\n|$)`, "i"));
  return match ? match[1].trim() : "";
}

/** Returns {error, reason} or {config, hackathon, sponsorName, slug}. */
export function addSponsor(config, body) {
  const hackathonName = extractField(body, "Hackathon");
  const sponsorName = extractField(body, "Sponsor Name / Company");
  const website = extractField(body, "Website");
  const amount = extractField(body, "Sponsorship Amount");

  const missing = [];
  if (!hackathonName) missing.push("Hackathon");
  if (!sponsorName) missing.push("Sponsor Name / Company");
  if (!amount) missing.push("Sponsorship Amount");
  if (missing.length > 0) {
    return {
      error: `❌ Could not process sponsor request — the following required fields are missing:\n\n${missing.map((f) => `- **${f}**`).join("\n")}\n\nPlease edit the issue to include all required fields.`,
      reason: "Missing required fields: " + missing.join(", "),
    };
  }

  let HACKATHONS_CONFIG;
  try {
    HACKATHONS_CONFIG = vm.runInNewContext(config + "\nHACKATHONS_CONFIG", {}, { timeout: 5000 });
  } catch (e) {
    return { error: `❌ Failed to parse \`${CONFIG}\`: ${e.message}`, reason: "Config parse error: " + e.message };
  }

  const wanted = hackathonName.toLowerCase().trim();
  let hackathon = HACKATHONS_CONFIG.hackathons.find((h) => h.name.toLowerCase().trim() === wanted);
  if (!hackathon) {
    hackathon = HACKATHONS_CONFIG.hackathons.find(
      (h) => h.name.toLowerCase().includes(hackathonName.toLowerCase()) ||
        hackathonName.toLowerCase().includes(h.name.toLowerCase()),
    );
  }
  if (!hackathon) {
    const available = HACKATHONS_CONFIG.hackathons.map((h) => `\`${h.name}\``).join(", ");
    return {
      error: `❌ No hackathon found matching **"${hackathonName}"**.\n\nAvailable hackathons: ${available}\n\nPlease edit the issue with the exact hackathon name.`,
      reason: "Hackathon not found: " + hackathonName,
    };
  }

  const slug = hackathon.slug;
  const newSponsorJSON = JSON.stringify({
    name: sponsorName,
    website: website && website !== NO_RESPONSE ? website : "",
    amount,
    level: "partner",
    logo: "",
  });

  const slugMatches = [];
  const slugRe = /slug:\s*"([^"]+)"/g;
  let m;
  while ((m = slugRe.exec(config)) !== null) slugMatches.push({ slug: m[1], index: m.index });
  const targetIdx = slugMatches.findIndex((s) => s.slug === slug);
  if (targetIdx === -1) {
    return { error: `❌ Could not locate slug \`${slug}\` in \`${CONFIG}\`.`, reason: "Could not locate slug in config: " + slug };
  }
  const blockStart = slugMatches[targetIdx].index;
  const blockEnd = targetIdx + 1 < slugMatches.length ? slugMatches[targetIdx + 1].index : config.length;
  const block = config.substring(blockStart, blockEnd);
  const updatedBlock = block.replace(/sponsors:\s*\[([^\]]*)\]/, (match, inner) => {
    if (!inner.trim()) return `sponsors: [\n                ${newSponsorJSON}\n            ]`;
    return `sponsors: [${inner.trimEnd()},\n                ${newSponsorJSON}\n            ]`;
  });
  if (updatedBlock === block) {
    return {
      error: `❌ Could not update the sponsors array in the config for hackathon **"${hackathon.name}"**. Please update \`${CONFIG}\` manually.`,
      reason: "Sponsors array not found in hackathon block",
    };
  }
  return {
    config: config.substring(0, blockStart) + updatedBlock + config.substring(blockEnd),
    hackathon,
    sponsorName,
    slug,
  };
}

async function main() {
  const issue = readEvent().issue;
  if (!issue) throw new Error("no issue in the event payload");
  const n = issue.number;
  const configPath = join(PROJECT, CONFIG);

  const result = addSponsor(readFileSync(configPath, "utf8"), issue.body || "");
  if (result.error) {
    await comment(n, result.error);
    console.error(result.reason);
    process.exit(1);
  }
  writeFileSync(configPath, result.config, "utf8");
  console.log(`Sponsor "${result.sponsorName}" added to hackathon "${result.hackathon.name}" (${result.slug}).`);

  commitBack({
    cwd: PROJECT,
    message: `blt-hackathons: add sponsor ${result.sponsorName} to ${result.slug} (issue #${n})`,
    paths: [CONFIG],
    deploy: "blt-hackathons",
  });

  await comment(n, `✅ **${result.sponsorName}** has been added as a sponsor for **${result.hackathon.name}**!\n\nThey will appear in the Sponsors section after the next deployment.\n\n> 💡 Payment should be arranged directly through [GitHub Sponsors](https://github.com/sponsors).`);
  await closeIssue(n);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) run(main);
