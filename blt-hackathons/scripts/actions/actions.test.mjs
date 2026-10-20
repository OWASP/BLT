// node --test 'scripts/actions/*.test.mjs'
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { buildEntry, insertEntry, extractField } from "./create-hackathon.mjs";
import { addSponsor } from "./process-sponsor.mjs";

const CONFIG = readFileSync(new URL("../../public/js/hackathons-config.js", import.meta.url), "utf8");
const load = (src) => JSON.parse(JSON.stringify(vm.runInNewContext(src + "\nHACKATHONS_CONFIG", {})));

const form = (fields) => Object.entries(fields).map(([k, v]) => `### ${k}\n\n${v}`).join("\n\n");
const HACKATHON = {
  "Hackathon Name": "Test Hack",
  "Slug (URL identifier)": "test-hack-2099",
  Description: "A `test` hackathon.",
  "Start Date & Time (ISO 8601)": "2099-01-01T00:00:00Z",
  "End Date & Time (ISO 8601)": "2099-01-31T23:59:59Z",
  "Banner Image": "![b](https://example.org/b.png)",
  "Source Control Provider": "GitHub",
  "GitHub Organization (optional)": "OWASP-BLT",
  "Repositories (one per line, optional)": "OWASP-BLT/BLT\nOWASP-BLT/BLT-Jobs",
  "Prizes JSON (optional)": "not json",
};

test("extractField reads issue form sections", () => {
  assert.equal(extractField(form(HACKATHON), "Hackathon Name"), "Test Hack");
});

test("a valid hackathon form is inserted first and the config still evaluates", () => {
  const built = buildEntry(form(HACKATHON));
  assert.equal(built.slug, "test-hack-2099");
  assert.match(built.prizesWarning, /could not be parsed/);
  const { config } = insertEntry(CONFIG, built.slug, built.entry);
  const first = load(config).hackathons[0];
  assert.equal(first.slug, "test-hack-2099");
  assert.equal(first.github.organization, "OWASP-BLT");
  assert.deepEqual(first.github.repositories, ["OWASP-BLT/BLT", "OWASP-BLT/BLT-Jobs"]);
  assert.equal(first.bannerImage, "https://example.org/b.png");
  assert.equal(load(config).hackathons.length, load(CONFIG).hackathons.length + 1);
  assert.match(insertEntry(config, built.slug, built.entry).error, /already exists/);
});

test("invalid forms are rejected with a comment", () => {
  const { Description, ...noDescription } = HACKATHON;
  assert.match(buildEntry(form(noDescription)).error, /Description/);
  assert.match(buildEntry(form({ ...HACKATHON, "Slug (URL identifier)": "Bad Slug" })).error, /invalid/);
  assert.match(buildEntry(form({ ...HACKATHON, "End Date & Time (ISO 8601)": "2098-01-01T00:00:00Z" })).error, /must be after/);
});

test("a sponsor is appended to the matching hackathon", () => {
  const target = load(CONFIG).hackathons[0];
  const body = `**Hackathon:** ${target.name}\n**Sponsor Name / Company:** ACME\n**Website:** https://acme.example\n**Sponsorship Amount:** $100\n`;
  const result = addSponsor(CONFIG, body);
  assert.equal(result.slug, target.slug);
  const sponsors = load(result.config).hackathons.find((h) => h.slug === target.slug).sponsors;
  assert.deepEqual(sponsors.at(-1), { name: "ACME", website: "https://acme.example", amount: "$100", level: "partner", logo: "" });
  assert.match(addSponsor(CONFIG, "**Hackathon:** nope-nothing-matches\n**Sponsor Name / Company:** A\n**Sponsorship Amount:** 1").error, /No hackathon found/);
  assert.match(addSponsor(CONFIG, "").error, /missing/);
});

test("issue text cannot break out of the config's string literals", () => {
  globalThis.__pwned = false;
  const payloads = [
    "${globalThis.__pwned = true}",
    "\\`, pwned: (globalThis.__pwned = true), x: `",
    "\"; globalThis.__pwned = true; \"",
  ];
  for (const payload of payloads) {
    const built = buildEntry(form({ ...HACKATHON, Description: payload, "Rules (optional)": payload }));
    const { config } = insertEntry(CONFIG, built.slug, built.entry);
    const first = vm.runInNewContext(config + "\nHACKATHONS_CONFIG", { globalThis: {} }).hackathons[0];
    assert.equal(first.description, payload);
    assert.equal(first.pwned, undefined);
    // Evaluated the way scripts/parse_hackathons_config.js does it.
    const parsed = eval(`${config}\nHACKATHONS_CONFIG`).hackathons[0];
    assert.equal(parsed.description, payload);
  }
  assert.equal(globalThis.__pwned, false);
});
