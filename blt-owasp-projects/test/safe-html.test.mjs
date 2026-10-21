// Regression tests: dashboard pages must escape GitHub/OWASP data before DataTables renders it as
// HTML, and must only link to http(s) URLs.
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

test("index.html escapes project metadata and drops script hrefs", () => {
  const ctx = loadPage("index.html");
  const [row] = ctx.generateProjectData([
    { name: PAYLOAD, pitch: PAYLOAD, title: PAYLOAD, license: PAYLOAD, repo_name: PAYLOAD,
      codeurl: "javascript:alert(1)", url: `https://owasp.org/${PAYLOAD}`, stars: 5 },
  ]);
  for (const value of Object.values(row)) noRawPayload(value);
  assert.equal(row.stars, "5");
  assert.match(row.url, /^<a href="https:\/\/owasp\.org\//);
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
