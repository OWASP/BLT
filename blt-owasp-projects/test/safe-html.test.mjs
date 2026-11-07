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
  // Only http(s) links, plus the page's own open.html links with an encoded repository.
  assert.doesNotMatch(html, /href="(?!https?:|open\.html\?kind=(issues|prs)&amp;repo=[^"<>']*")/i);
  assert.match(html, /href="open\.html\?kind=prs&amp;repo=%22%3E%3Cimg%20src%3Dx/);
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
  assert.equal(ctx.levelOf({ level: "Lab" }), "lab");
  assert.equal(ctx.levelOf({ level: "flagship" }), "flagship");
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
  projects[1].listed = false;
  assert.equal(titles({ listed: "www" }), "Amass");
  assert.equal(titles({ listed: "owasp" }), "Zed,Cheat");
});

test("matrix.js totals count shared repositories once and show – for missing data, not 0", () => {
  const ctx = loadPage();
  vm.runInContext(read("matrix.js"), ctx);
  const html = ctx.totalsHtml([
    { repo_name: "OWASP/a", issues: 3, prs: 1, commits_90d: 10 },
    { repo_name: "owasp/A", issues: 3, prs: 1, commits_90d: 10 },
    { repo_name: "OWASP/b", issues: 2, prs: 4, commits_90d: 5, listed: false },
  ]);
  assert.match(html, /<dt>Commits in 90 days<\/dt><dd>15<\/dd>/);
  assert.match(html, /href="open\.html\?kind=issues"><dt>Open issues<\/dt><dd>5<\/dd>/);
  assert.match(html, /href="open\.html\?kind=prs"><dt>Open pull requests<\/dt><dd>5<\/dd>/);
  assert.match(html, /2 in the owasp\.org inventory and 1 active www-project/);
  assert.match(ctx.totalsHtml([{ repo_name: "OWASP/a", issues: 1 }]), /<dt>Commits in 90 days<\/dt><dd>–<\/dd>/);
});

test("matrix.js cards: a cover in the main language's colour, GitHub's language bar, contribution chips", () => {
  const ctx = loadPage();
  vm.runInContext(read("matrix.js"), ctx);
  const p = { title: "OWASP Juice Shop", level: "flagship", repo_name: "juice-shop/juice-shop", codeurl: "https://github.com/juice-shop/juice-shop",
    github_status: "success", languages: [["TypeScript", "#3178c6", 0.7], ["JavaScript", "#f1e05a", 0.25], ["HTML", "red;}", 0.05], [PAYLOAD, "#000000", 0]] };
  assert.equal(ctx.monogram(p), "JS");
  assert.equal(ctx.monogram({ title: "OWASP ZAP" }), "ZA");
  assert.equal(ctx.coverColor(p), "#3178c6");
  assert.equal(ctx.coverColor({ level: "lab" }), "#2563eb");
  assert.equal(ctx.languagesOf(p).length, 3);
  const bar = ctx.langBarHtml(p);
  assert.match(bar, /flex-grow:0\.7;background:#3178c6/);
  assert.match(bar, /background:#94a3b8/); // a colour that isn't #rrggbb is replaced
  assert.match(bar, /aria-label="TypeScript 70%, JavaScript 25%, HTML 5\.0%"/);
  assert.match(ctx.langBarHtml({ github_status: "success" }), /No code languages detected/);
  const card = ctx.cardHtml(p, Date.parse("2026-11-06T00:00:00Z"), { good_first: 3, help_wanted: 0, needs_review: 1 });
  assert.match(card, /style="--cover:#3178c6;--cover-ink:#ffffff"/);
  assert.match(card, /href="open\.html\?kind=issues&amp;repo=juice-shop%2Fjuice-shop&amp;view=good-first"><b>3<\/b> good first issues/);
  assert.match(card, /<b>1<\/b> PR to review/);
  assert.doesNotMatch(card, /help wanted/);
  assert.doesNotMatch(card, /<img/);
  const strip = ctx.contributeStripHtml(ctx.workTotals([{ good_first: 2, help_wanted: 1, needs_review: 5, quick: 2, first_time: 1 }, { good_first: 1 }]));
  assert.match(strip, /<b>3<\/b><span>Good first issues/);
  assert.match(strip, /href="open\.html\?kind=prs&amp;view=quick"/);
});

test("open.html (open.js) escapes GitHub data and sorts by any column", () => {
  const ctx = loadPage();
  vm.runInContext(read("open.js"), ctx);
  assert.match(read("open.html"), /<script src="safe-html\.js"><\/script>\s*<script src="open\.js">/);
  const row = {
    repo: "OWASP/a", projects: [["a", PAYLOAD]], number: 7, title: PAYLOAD, url: "javascript:alert(1)",
    author: PAYLOAD, bot: false, labels: [[PAYLOAD, `"red;}`], ["bug", "d73a4a"]], assignees: [PAYLOAD, "bob"],
    comments: 2, created_at: "2026-11-01T00:00:00Z", updated_at: "2026-11-02T00:00:00Z",
    draft: false, review: "APPROVED", additions: 10, deletions: 2, files: 1,
  };
  for (const kind of ["issues", "prs"]) {
    const html = ctx.rowHtml(row, kind);
    assert.doesNotMatch(html, /<img src=x/i);
    assert.doesNotMatch(html, /href="(?!https?:|#")/i);
    assert.doesNotMatch(html, /--label:#"/);
    assert.match(html, /--label:#d73a4a;--label-text:#fff/);
  }
  assert.match(ctx.rowHtml(row, "prs"), /Approved/);
  assert.match(ctx.rowHtml(row, "issues"), /src="https:\/\/avatars\.githubusercontent\.com\/bob\?s=48"/);
  assert.equal(ctx.avatarUrl("dependabot[bot]"), "https://avatars.githubusercontent.com/dependabot?s=48");
  assert.equal(ctx.avatarUrl(PAYLOAD), null);

  const rows = [
    { repo: "OWASP/b", projects: [["b", "Beta"]], number: 1, title: "zeta", author: "x", bot: false, labels: [], assignees: [], comments: 5, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-03-01T00:00:00Z", review: "APPROVED" },
    { repo: "OWASP/a", projects: [["a", "Alpha"]], number: 2, title: "alpha fix", author: "y", bot: false, labels: [["bug", "ff0000"]], assignees: [], comments: 1, created_at: "2026-02-01T00:00:00Z", updated_at: "2026-02-01T00:00:00Z", review: "CHANGES_REQUESTED" },
    { repo: "OWASP/a", projects: [["a", "Alpha"]], number: 3, title: "bump deps", author: "dependabot[bot]", bot: true, labels: [], assignees: [], comments: 0, created_at: "2026-03-01T00:00:00Z", updated_at: "2026-04-01T00:00:00Z", draft: true },
  ];
  const nums = (opts, kind = "prs") => ctx.filterRows(rows, opts, kind).map((r) => r.number).join(",");
  assert.equal(nums({}), "1,2");
  assert.equal(nums({ bots: true }), "3,1,2");
  assert.equal(nums({ sort: "title" }), "2,1");
  assert.equal(nums({ sort: "title", dir: -1 }), "1,2");
  assert.equal(nums({ sort: "comments" }), "1,2");
  assert.equal(nums({ sort: "project" }), "2,1");
  assert.equal(nums({ repo: "owasp/a", bots: true }), "3,2");
  assert.equal(nums({ q: "BUG" }), "2");
  assert.equal(nums({ sort: "review", bots: true }), "2,1,3");
  assert.match(ctx.headHtml("prs", "comments", 0), /<th scope="col" class="col-comments n" aria-sort="descending">/);

  // Quick views, counted over the other filters.
  const NOW = Date.parse("2026-11-07T00:00:00Z");
  const work = [
    { ...rows[0], number: 10, labels: [["good first issue", "7057ff"]], assignees: [], comments: 0, created_at: "2026-11-01T00:00:00Z", updated_at: "2026-11-02T00:00:00Z", lang: "Python", level: "lab" },
    { ...rows[0], number: 11, labels: [["Help Wanted", "008672"]], assignees: ["x"], comments: 3, created_at: "2025-01-01T00:00:00Z", updated_at: "2025-02-01T00:00:00Z", lang: "Java", level: "flagship" },
    { ...rows[1], number: 12, review: null, draft: false, additions: 10, deletions: 2, role: "NONE", lang: "Python", level: "lab" },
    { ...rows[1], number: 13, review: "REVIEW_REQUIRED", draft: false, additions: 400, deletions: 0, role: "MEMBER", created_at: "2025-01-01T00:00:00Z" },
    { ...rows[1], number: 14, review: null, draft: false, additions: 0, deletions: 0, role: "CONTRIBUTOR" },
  ];
  const view = (kind, v, extra = {}) => ctx.filterRows(work, { view: v, ...extra }, kind, NOW).map((r) => r.number).join(",");
  assert.equal(view("issues", "good-first"), "10");
  assert.equal(view("issues", "help-wanted"), "11");
  assert.equal(view("issues", "unassigned"), "10");
  assert.equal(view("issues", "fresh"), "10");
  assert.equal(view("prs", "quick"), "12");
  assert.equal(view("prs", "first-time"), "12");
  assert.equal(view("prs", "waiting", { bots: true }).split(",")[0], "13");
  assert.equal(view("issues", "all", { lang: "Python" }), "10,12");
  assert.equal(view("issues", "all", { level: "flagship" }), "11");
  const counts = ctx.viewCounts(ctx.baseRows(work, {}), "prs", NOW);
  assert.equal(counts.all, 5);
  assert.equal(counts["needs-review"], 3);
  assert.equal(counts.quick, 1);
  assert.doesNotMatch(ctx.headHtml("issues", "updated", 0), /Review/);
});

test("projects.html (repos.js) escapes repository data and matches repositories to projects", () => {
  const ctx = loadPage();
  vm.runInContext(read("repos.js"), ctx);
  assert.match(read("projects.html"), /<script src="safe-html\.js"><\/script>\s*<script src="repos\.js">/);
  const now = "2026-01-01T00:00:00Z";
  const rows = ctx.generateRows([
    { name: PAYLOAD, full_name: "OWASP/x", html_url: "javascript:alert(1)", description: PAYLOAD, created_at: now, pushed_at: now, stargazers_count: 1 },
    { name: "www-project-y", full_name: "OWASP/www-project-y", html_url: "https://github.com/OWASP/www-project-y", archived: true },
    { name: "www-project-z", full_name: "OWASP/www-project-z", html_url: "https://github.com/OWASP/www-project-z" },
  ], [{ title: PAYLOAD, url: "javascript:x", www_repo: "owasp/X" }, { title: "Zed", url: "https://owasp.org/projects/z", www_repo: "OWASP/www-project-z", listed: false }]);
  assert.deepEqual(rows.map((r) => r.status), ["listed", "archived", "unlisted"]);
  const html = rows.map(ctx.rowHtml).join("");
  assert.doesNotMatch(html, /<img/i);
  assert.doesNotMatch(html, /href="(?!https?:)/i);
  assert.match(html, /href="https:\/\/github\.com\/OWASP\/x"/);
  assert.deepEqual(ctx.filterRows(rows, { status: "unlisted" }).map((r) => r.name), ["www-project-z"]);
  assert.deepEqual(ctx.filterRows(rows, { q: "zed" }).map((r) => r.name), ["www-project-z"]);
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
