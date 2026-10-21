// Static checks on the landing page: no made-up numbers, no stale banner, no
// missing local files, nothing loaded from other origins (the CSP forbids it).
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const publicDir = join(here, "..", "public");
const repo = join(here, "..", "..");
const html = readFileSync(join(publicDir, "index.html"), "utf8");
const js = readFileSync(join(publicDir, "_home", "home.js"), "utf8");

const attrs = (name) => [...html.matchAll(new RegExp(`\\s${name}="([^"]*)"`, "g"))].map((m) => m[1]);

test("no fabricated statistics or sample leaderboard", () => {
  const banned = [
    "15,234", "3,421", "248,500", "$248", "12,000+", "3,500+", "$250K", "800+", "892",
    "14 total reports", "Bugs Logged</h3>", "8 bugs", "3 bugs", "219 ms", "341 ms",
    "DonnieBLT", "rinkitadhana", "mdkaifansari04", "+3 reports", "32 apps", "20 total",
  ];
  for (const s of banned) {
    assert.ok(!html.includes(s), `index.html contains "${s}"`);
    assert.ok(!js.includes(s), `home.js contains "${s}"`);
  }
});

test("live number slots start empty and hidden", () => {
  for (const m of html.matchAll(/<([a-z]+)[^>]*data-stat="[^"]*"[^>]*>([^<]*)</g)) {
    assert.equal(m[2].trim(), "", `data-stat slot has baked-in text: ${m[0]}`);
  }
  for (const m of html.matchAll(/<[a-z]+[^>]*data-stat-card="[^"]*"[^>]*>/g)) assert.match(m[0], /\shidden[\s>]/, m[0]);
  for (const m of html.matchAll(/<[a-z]+[^>]*data-live="[^"]*"[^>]*>/g)) assert.match(m[0], /\shidden[\s>]/, m[0]);
  assert.match(html, /<section id="numbers"[^>]*\shidden>/);
});

test("fetched data is only inserted as text", () => {
  assert.doesNotMatch(js, /innerHTML|outerHTML|insertAdjacentHTML|document\.write/);
});

test("no stale banner or GitLab-era links", () => {
  for (const s of ["April 15, 2026", "Design context", "contest now live", "gitlab.com", "owaspblt.slack.com", "owaspblt.org/leaderboard.html", "legacy.owaspblt.org"]) {
    assert.ok(!html.includes(s), s);
  }
});

test("the announcement banner is one element with a real link", () => {
  const banner = html.match(/<a id="announcement"[^>]*href="([^"]+)"/);
  assert.ok(banner, "announcement link");
  assert.match(banner[1], /^https:\/\/git\.owaspblt\.org\/BLT\/issues\?label=hacktoberfest$/);
});

test("every local src/href exists under public/", () => {
  const refs = [...attrs("src"), ...attrs("href")].filter((u) => u.startsWith("/") && !u.startsWith("//"));
  assert.ok(refs.length > 40);
  for (const ref of refs) {
    const path = ref.split(/[?#]/)[0];
    const file = path === "/" ? "index.html" : path.slice(1);
    assert.ok(existsSync(join(publicDir, file)), `missing ${ref}`);
  }
  // fragment links point at real ids
  for (const ref of attrs("href").filter((u) => u.startsWith("#"))) {
    assert.ok(html.includes(`id="${ref.slice(1)}"`), `missing anchor ${ref}`);
  }
});

test("nothing is loaded from another origin; no inline scripts or styles", () => {
  for (const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
    assert.match(m[1], /src="\/_home\//, "scripts are local files");
    assert.equal(m[2].trim(), "", "no inline script");
  }
  for (const m of html.matchAll(/<link\b[^>]*>/g)) assert.doesNotMatch(m[0], /href="https?:/, m[0]);
  assert.doesNotMatch(html, /<style\b|\sstyle="|\son[a-z]+="/);
  for (const src of attrs("src")) assert.ok(src.startsWith("/_home/"), `src ${src}`);
});

test("images are small, sized and have alt text", () => {
  for (const m of html.matchAll(/<img\b[^>]*>/g)) {
    assert.match(m[0], /\salt="[^"]*"/, m[0]);
    assert.match(m[0], /\swidth="\d+"/, m[0]);
  }
  for (const src of attrs("src").filter((s) => /\.(webp|png|svg)$/.test(s))) {
    assert.ok(statSync(join(publicDir, src.slice(1))).size < 20_000, `${src} is over 20 KB`);
  }
});

test("buttons have accessible names", () => {
  for (const m of html.matchAll(/<button\b[^>]*>([\s\S]*?)<\/button>/g)) {
    const text = m[1].replace(/<[^>]+>/g, "").trim();
    assert.ok(/aria-label="[^"]+"/.test(m[0]) || text, m[0].slice(0, 80));
  }
});

test("Explore cards link only to live sites listed in the root README", { skip: !existsSync(join(repo, "README.md")) && "no monorepo README" }, () => {
  const readme = readFileSync(join(repo, "README.md"), "utf8");
  const live = new Set([...readme.matchAll(/\]\((https:\/\/[a-z0-9-]+\.owaspblt\.org\/)\)\s*\|\s*$/gm)].map((m) => m[1]));
  live.add("https://pool.owaspblt.org/");
  const cards = [...html.matchAll(/<a class="product-card" href="([^"]+)"><img src="([^"]+)"/g)];
  assert.ok(cards.length >= 40, `only ${cards.length} cards`);
  const seen = new Set();
  for (const [, href, logo] of cards) {
    assert.ok(live.has(href), `${href} is not a live site in the README table`);
    assert.ok(!seen.has(href), `duplicate card ${href}`);
    seen.add(href);
    assert.match(logo, /^\/_home\/logos\/[a-z0-9-]+\.(svg|webp)$/);
  }
});

test("external links use https", () => {
  for (const href of attrs("href").filter((h) => /^[a-z]+:/i.test(h))) assert.match(href, /^https:\/\//, href);
});
