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
    assert.match(m[1], /src="\/(_home\/|_shared\/blt-analytics\.js")/, "scripts are local files");
    assert.equal(m[2].trim(), "", "no inline script");
  }
  for (const m of html.matchAll(/<link\b[^>]*>/g)) assert.doesNotMatch(m[0], /href="https?:/, m[0]);
  assert.doesNotMatch(html, /<style\b|\sstyle="|\son[a-z]+="/);
  for (const src of attrs("src")) assert.ok(src.startsWith("/_home/") || src === "/_shared/blt-analytics.js", `src ${src}`);
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

test("the shared top bar lists the same apps as the Explore cards", () => {
  const nav = readFileSync(join(publicDir, "_shared", "blt-nav.js"), "utf8");
  const apps = [...nav.matchAll(/^\s*\["([^"]+)", "([^"]+)", "([^"]+)"\],$/gm)].map((m) => `${m[1]}|${m[2]}|/_home/logos/${m[3]}`);
  const cards = [...html.matchAll(/class="product-card" href="([^"]+)"><img src="([^"]+)"[^>]*><span><strong>([^<]+)</g)].map((m) => `${m[3]}|${m[1]}|${m[2]}`);
  assert.ok(cards.length > 40);
  assert.deepEqual(apps, cards);
  for (const a of apps) assert.ok(existsSync(join(publicDir, a.split("|")[2])), a);
  assert.doesNotMatch(nav, /innerHTML|outerHTML|insertAdjacentHTML|document\.write/);
});

test("every Explore project has its plain symbol (no wasp) in _home/symbols/", () => {
  const cards = [...html.matchAll(/class="product-card" href="[^"]+"><img src="\/_home\/logos\/([a-z0-9-]+)\.(?:svg|webp)"/g)].map((m) => m[1]);
  assert.ok(cards.length > 40);
  for (const p of cards) {
    const file = join(publicDir, "_home", "symbols", p + ".svg");
    assert.ok(existsSync(file), `missing _home/symbols/${p}.svg`);
    const svg = readFileSync(file, "utf8");
    assert.match(svg, /^<svg\b[^>]*xmlns="http:\/\/www\.w3\.org\/2000\/svg"/, p);
    // not the badge: the badge's project sub-circle is clipped with an id ending in "-sub"
    assert.doesNotMatch(svg, /<clipPath id="[a-z0-9]+-sub">/, `${p} symbol is a wasp badge`);
    assert.notEqual(svg, readFileSync(join(publicDir, "_home", "logos", p + ".svg"), "utf8"), p);
    assert.ok(svg.length < 20_000, `${p} symbol is over 20 KB`);
    assert.doesNotMatch(svg, /<script|\son[a-z]+=|href="(?!#)/i, `${p} symbol: no scripts or external refs`);
  }
});

test("both apps choosers show the plain symbols, the Explore cards keep the badges", () => {
  const nav = readFileSync(join(publicDir, "_shared", "blt-nav.js"), "utf8");
  assert.match(nav, /BASE \+ "\/_home\/symbols\/" \+ p\[2\]/, "blt-nav.js apps grid uses _home/symbols/");
  assert.doesNotMatch(nav, /"\/_home\/logos\/"/, "blt-nav.js loads no badge logos");
  assert.match(js, /symbol: img \? img\.getAttribute\("src"\)\.replace\("\/_home\/logos\/", "\/_home\/symbols\/"\)/);
  const apps = js.slice(js.indexOf("function buildApps"), js.indexOf("function buildApps") + 800);
  assert.match(apps, /img\.src = p\.symbol;/);
  assert.doesNotMatch(apps, /p\.logo/);
  for (const m of html.matchAll(/class="product-card"[^>]*><img src="([^"]+)"/g)) assert.match(m[1], /^\/_home\/logos\//);
});

test("analytics: the page and the shared bar load the forge's first-party analytics", () => {
  assert.match(html, /<script src="\/_shared\/blt-analytics\.js" defer><\/script>/);
  const nav = readFileSync(join(publicDir, "_shared", "blt-nav.js"), "utf8");
  assert.match(nav, /BASE \+ "\/_shared\/blt-analytics\.js"/);
  assert.match(nav, /getAttribute\("data-analytics"\) === "off"/);
});

test("analytics: first-party, private by default, nothing third-party", () => {
  const js = readFileSync(join(publicDir, "_shared", "blt-analytics.js"), "utf8");
  assert.match(js, /var FORGE = "https:\/\/git\.owaspblt\.org";/);
  assert.match(js, /tag\.src = FORGE \+ "\/analytics-sdk\.js";/);
  assert.match(js, /var KEY = "(fma_[0-9a-f]{40})?";/);
  // Do Not Track and Global Privacy Control stop it before anything loads.
  assert.match(js, /nav\.globalPrivacyControl === true/);
  assert.match(js, /doNotTrack/);
  assert.ok(js.indexOf("globalPrivacyControl") < js.indexOf("createElement("), "privacy check runs before the SDK loads");
  for (const opt of ["autocapture", "heatmaps", "sessionRecording", "surveys", "captureErrors"]) {
    assert.match(js, new RegExp(`\\b${opt}: false,`), opt);
  }
  assert.match(js, /maskUrlQuery: true/);
  assert.match(js, /respectDoNotTrack: true/);
  const code = js.replace(/^\s*\/\/.*$/gm, "");
  assert.doesNotMatch(code, /document\.cookie|posthog|phc_|googletagmanager|google-analytics|plausible|umami/i);
  assert.doesNotMatch(code, /innerHTML|outerHTML|insertAdjacentHTML|document\.write/);
});
