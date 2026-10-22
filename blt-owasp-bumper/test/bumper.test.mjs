import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";
import {
  DEFAULT_FILTERS, bumpBlocker, bumpUrl, checklist, escapeHtml, filtersFromQuery, filtersToQuery, idleYears,
  matches, safeUrl, sortRepos,
} from "../public/bumper.js";

const NOW = Date.parse("2026-10-22T00:00:00Z");
const repo = (over) => ({ name: "www-project-x", url: "https://github.com/OWASP/www-project-x", kind: "project", archived: false, pushed: "2022-10-22T00:00:00Z", ...over });
const f = (over) => ({ ...DEFAULT_FILTERS, ...over });

test("escapeHtml is quote-safe and links are http(s) only", () => {
  assert.equal(escapeHtml(`fix" onmouseover="alert(1)`), "fix&quot; onmouseover=&quot;alert(1)");
  assert.equal(escapeHtml("it's <b>"), "it&#39;s &lt;b&gt;");
  assert.equal(escapeHtml(0), "0");
  assert.equal(safeUrl("javascript:alert(1)"), "#");
  assert.equal(bumpUrl(repo({ url: "javascript:alert(1)" }), NOW), "#");
});

test("idle time uses the last push, then the last update", () => {
  assert.equal(Math.round(idleYears(repo(), NOW)), 4);
  assert.equal(Math.round(idleYears(repo({ pushed: "", updated: "2025-10-22T00:00:00Z" }), NOW)), 1);
});

test("filters: activity, type, archived, language, created year, search and bumped", () => {
  const r = repo({ language: "Python", created: "2019-01-01T00:00:00Z", topics: ["threat-modeling"] });
  const ctx = { now: NOW, bumped: {} };
  assert.ok(matches(r, f({ idle: "3y" }), ctx));
  assert.ok(!matches(r, f({ idle: "5y" }), ctx));
  assert.ok(!matches(r, f({ idle: "active" }), ctx));
  assert.ok(!matches(r, f({ kind: "chapter" }), ctx));
  assert.ok(!matches(repo({ archived: true }), f(), ctx));
  assert.ok(matches(repo({ archived: true }), f({ archived: true }), ctx));
  assert.ok(matches(r, f({ lang: "Python", created: "2019" }), ctx));
  assert.ok(!matches(r, f({ lang: "none" }), ctx));
  assert.ok(matches(r, f({ q: "THREAT project" }), ctx));
  assert.ok(!matches(r, f({ q: "nothing-like-it" }), ctx));
  assert.ok(!matches(r, f({ bumped: "not" }), { now: NOW, bumped: { "www-project-x": "2026-10-01" } }));
});

test("archived repos and ones with issues off can't be bumped", () => {
  assert.equal(bumpBlocker(repo()), "");
  assert.match(bumpBlocker(repo({ archived: true })), /Archived/);
  assert.match(bumpBlocker(repo({ issues_off: true })), /turned off/);
});

test("the reminder is GitHub's prefilled new-issue form, naming the last push", () => {
  const url = new URL(bumpUrl(repo(), NOW));
  assert.equal(url.origin + url.pathname, "https://github.com/OWASP/www-project-x/issues/new");
  assert.match(url.searchParams.get("title"), /still maintained/);
  assert.match(url.searchParams.get("body"), /last push to this repository was on 2022-10-22 \(4y ago\)/);
  assert.match(url.searchParams.get("body"), /https:\/\/bumper\.owaspblt\.org\//);
  assert.doesNotMatch(url.searchParams.get("body"), /github\.com\/OWASP-BLT|gitlab/i);
});

test("checklist lists each repo with its reminder link", () => {
  const text = checklist([repo(), repo({ name: "b", url: "https://github.com/OWASP/b" })], NOW);
  assert.match(text, /^OWASP repositories to bump \(2, from https:\/\/bumper\.owaspblt\.org\/ on 2026-10-22\)/);
  assert.match(text, /- \[ \] \[www-project-x\]\(https:\/\/github\.com\/OWASP\/www-project-x\): last push 2022-10-22 · \[open reminder\]\(https:\/\/github\.com\/OWASP\/www-project-x\/issues\/new\?/);
  assert.equal(text.trim().split("\n").length, 4);
});

test("sorting and the shareable query string", () => {
  const list = [repo({ name: "a", pushed: "2020-01-01" }), repo({ name: "b", pushed: "2024-01-01" })];
  assert.deepEqual(sortRepos(list, "idle-desc").map((r) => r.name), ["a", "b"]);
  assert.deepEqual(sortRepos(list, "idle-asc").map((r) => r.name), ["b", "a"]);
  const q = filtersToQuery(f({ q: "zap", idle: "3y", archived: true }));
  assert.equal(q, "?q=zap&idle=3y&archived=1");
  assert.deepEqual(filtersFromQuery(q), f({ q: "zap", idle: "3y", archived: true }));
  assert.equal(filtersFromQuery("?idle=bogus").idle, DEFAULT_FILTERS.idle);
});

test("the generator writes compact records the page reads", () => {
  const here = new URL("..", import.meta.url).pathname;
  const out = execFileSync("python3", ["-c", `
import json, sys; sys.path.insert(0, '.'); import generate_repo_list as g
d = g.build_data([{"name": "www-chapter-x", "html_url": "https://github.com/OWASP/www-chapter-x", "archived": False,
  "has_issues": False, "pushed_at": "2020-01-01T00:00:00Z", "stargazers_count": 0, "topics": ["a"]}], "owasp")
print(json.dumps(d))`], { cwd: here, encoding: "utf8" });
  const data = JSON.parse(out);
  assert.equal(data.total, 1);
  assert.deepEqual(data.repos[0], {
    name: "www-chapter-x", url: "https://github.com/OWASP/www-chapter-x", pushed: "2020-01-01T00:00:00Z",
    topics: ["a"], archived: false, issues_off: true, kind: "chapter",
  });
});
