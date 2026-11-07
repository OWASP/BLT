// Regression tests: dashboard pages must escape GitHub/OWASP data before it is rendered as HTML
// (by DataTables, or by matrix.js on the home page), and must only link to http(s) URLs.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const read = (p) => readFileSync(new URL(`../public/${p}`, import.meta.url), "utf8");
const PAYLOAD = `"><img src=x onerror=alert(1)>'`;

// Loads safe-html.js plus a page's inline script into a sandbox (fetch never resolves, so the
// page's loader never reaches DataTables) and returns the sandbox.
function loadPage(page) {
  const ctx = vm.createContext({ URL, fetch: () => new Promise(() => {}), console });
  vm.runInContext(read("safe-html.js"), ctx);
  if (page) {
    const html = read(page);
    assert.match(html, /<script src="safe-html\.js"><\/script>/, `${page} loads safe-html.js`);
    const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]).join("\n");
    vm.runInContext(inline, ctx);
  }
  return ctx;
}

const noRawPayload = (html) => {
  assert.doesNotMatch(html, /<img/i);
  assert.doesNotMatch(html, /href="(?!https?:)/i);
};

test("escapeHtml escapes & < > \" '", () => {
  const { escapeHtml } = loadPage();
  assert.equal(escapeHtml(`&<>"'`), "&amp;&lt;&gt;&quot;&#39;");
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(42), "42");
});

test("safeHref allows only http(s)", () => {
  const { safeHref, linkHtml } = loadPage();
  assert.equal(safeHref("https://github.com/OWASP/x"), "https://github.com/OWASP/x");
  assert.equal(safeHref("http://owasp.org/"), "http://owasp.org/");
  for (const bad of ["javascript:alert(1)", " JaVaScRiPt:alert(1)", "data:text/html,x", "//evil", "/rel", "", null]) {
    assert.equal(safeHref(bad), null, String(bad));
  }
  assert.equal(linkHtml("javascript:alert(1)", "x<y"), "x&lt;y");
  assert.equal(
    linkHtml(`https://a.test/?q="'`, "t"),
    `<a href="https://a.test/?q=%22%27" target="_blank" rel="noopener noreferrer">t</a>`,
  );
});

test("index.html (matrix.js) escapes project metadata and contributors, and drops script hrefs", () => {
  const ctx = loadPage();
  vm.runInContext(read("matrix.js"), ctx);
  assert.match(read("index.html"), /<script src="safe-html\.js"><\/script>\s*<script src="matrix\.js">/);
  const html = ctx.cardHtml({
    name: PAYLOAD, pitch: PAYLOAD, title: PAYLOAD, license: PAYLOAD, repo_name: PAYLOAD, top_language: PAYLOAD,
    codeurl: "javascript:alert(1)", url: `https://owasp.org/${PAYLOAD}`, stars: 5, github_status: "success",
    top_contributors: [
      { login: PAYLOAD, html_url: "javascript:alert(1)", avatar_url: "javascript:alert(1)", contributions: 3 },
      { login: "alice", html_url: "https://github.com/alice", avatar_url: "https://avatars.githubusercontent.com/u/1?v=4", contributions: 1 },
    ],
  });
  assert.doesNotMatch(html, /<img src=x/i);
  assert.doesNotMatch(html, /href="(?!https?:)/i);
  assert.doesNotMatch(html, /src="(?!https:\/\/avatars\.githubusercontent\.com\/)/i);
  assert.match(html, /<a href="https:\/\/owasp\.org\/%22%3E%3Cimg/);
  assert.match(html, /src="https:\/\/avatars\.githubusercontent\.com\/u\/1\?v=4&amp;s=64"/);
  assert.match(html, /1 commit</);
});

test("matrix.js classifies, filters and sorts projects", () => {
  const ctx = loadPage();
  vm.runInContext(read("matrix.js"), ctx);
  const now = Date.parse("2026-11-06T00:00:00Z");
  assert.equal(ctx.levelOf({ level: 4 }), "flagship");
  assert.equal(ctx.levelOf({ level: "3.5" }), "production");
  assert.equal(ctx.levelOf({ level: "-1" }), "other");
  assert.equal(ctx.typeOf({ type: "documentation, code" }), "code");
  assert.equal(ctx.typeOf({ type: "Standards" }), "documentation");
  assert.equal(ctx.typeOf({ type: "" }), "other");
  assert.equal(ctx.ago("2026-11-01T00:00:00Z", now), "5 days ago");
  assert.equal(ctx.ago(null, now), null);
  assert.equal(ctx.pulse({ last_commit: "2026-10-20T00:00:00Z" }, now), "active");
  assert.equal(ctx.pulse({ last_commit: "2026-09-01T00:00:00Z" }, now), "recent");
  assert.equal(ctx.pulse({ last_commit: null }, now), "unknown");
  const projects = [
    { title: "Zed", level: "4", type: "code", commits_90d: 5, last_commit: "2026-11-01T00:00:00Z", top_contributors: [{ login: "bob" }] },
    { title: "Amass", level: "2", type: "tool", commits_90d: 40, last_commit: "2026-10-30T00:00:00Z" },
    { title: "Cheat", level: "4", type: "documentation", commits_90d: null, last_commit: "2020-01-01T00:00:00Z" },
  ];
  const titles = (opts) => ctx.filterProjects(projects, opts, now).map((p) => p.title).join(",");
  assert.equal(titles({}), "Amass,Zed,Cheat");
  assert.equal(titles({ sort: "name" }), "Amass,Cheat,Zed");
  assert.equal(titles({ level: "flagship", sort: "name" }), "Cheat,Zed");
  assert.equal(titles({ active: true }), "Amass,Zed");
  assert.equal(titles({ q: "BOB" }), "Zed");
});

test("projects.html escapes repo names", () => {
  const ctx = loadPage("projects.html");
  const now = "2026-01-01T00:00:00Z";
  const [row] = ctx.generateProjectData([
    { name: PAYLOAD, created_at: now, updated_at: now, pushed_at: now, stargazers_count: 1 },
  ]);
  noRawPayload(row.project_name);
  assert.match(row.project_name, /^<a href="https:\/\/owasp\.org\/%22%3E%3Cimg/);
});

test("issues.html escapes titles and only links http(s) issue URLs", () => {
  const ctx = loadPage("issues.html");
  const [row] = ctx.generateIssueData([
    { repo: "OWASP/x", number: 1, title: PAYLOAD, html_url: "javascript:alert(1)", author: PAYLOAD,
      author_url: "javascript:alert(1)", assignees: [PAYLOAD], milestone: PAYLOAD,
      labels: [{ name: PAYLOAD, color: `fff;background:url(x)` }], state: "open",
      created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", comments: 0 },
  ]);
  // *_sort fields feed DataTables' sort only (render returns them for type "sort"), never the DOM.
  for (const [key, value] of Object.entries(row)) if (!key.endsWith("_sort")) noRawPayload(String(value));
  assert.doesNotMatch(row.title, /<a /);
  assert.doesNotMatch(row.number, /<a /);
  assert.doesNotMatch(row.labels, /url\(x\)/);
  const [ok] = ctx.generateIssueData([
    { repo: "OWASP/x", number: 2, title: "t", html_url: "https://github.com/OWASP/x/issues/2", labels: [],
      assignees: [], state: "open", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
  ]);
  assert.match(ok.title, /^<a href="https:\/\/github\.com\/OWASP\/x\/issues\/2"/);
});
