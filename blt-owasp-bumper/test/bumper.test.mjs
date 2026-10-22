import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";
import {
  COOLDOWN_DAYS, DEFAULT_FILTERS, bumpBlocker, cooldown, since, bumpUrl, checklist, escapeHtml, filtersFromQuery, filtersToQuery, idleYears,
  lastBump, matches, reminderStatus, safeUrl, scoreAll, signal, siblingStem, sortRepos,
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

test("the reminder is GitHub's prefilled new-issue form, naming the last activity", () => {
  const url = new URL(bumpUrl(repo(), NOW));
  assert.equal(url.origin + url.pathname, "https://github.com/OWASP/www-project-x/issues/new");
  assert.match(url.searchParams.get("title"), /still maintained/);
  assert.match(url.searchParams.get("body"), /last commit to this repository was on 2022-10-22 \(4y ago\)/);
  assert.match(url.searchParams.get("body"), /https:\/\/bumper\.owaspblt\.org\//);
  assert.doesNotMatch(url.searchParams.get("body"), /github\.com\/OWASP-BLT|gitlab/i);
});

test("checklist lists each repo with its reminder link", () => {
  const text = checklist([repo(), repo({ name: "b", url: "https://github.com/OWASP/b" })], NOW);
  assert.match(text, /^OWASP repositories to bump \(2, from https:\/\/bumper\.owaspblt\.org\/ on 2026-10-22\)/);
  assert.match(text, /- \[ \] \[www-project-x\]\(https:\/\/github\.com\/OWASP\/www-project-x\): last active 2022-10-22 · \[open reminder\]\(https:\/\/github\.com\/OWASP\/www-project-x\/issues\/new\?/);
  assert.equal(text.trim().split("\n").length, 4);
});

test("sorting and the shareable query string", () => {
  const list = [repo({ name: "a", pushed: "2020-01-01" }), repo({ name: "b", pushed: "2024-01-01" })];
  assert.deepEqual(sortRepos(list, "idle-desc").map((r) => r.name), ["a", "b"]);
  assert.equal(DEFAULT_FILTERS.sort, "score-desc");
  assert.deepEqual(sortRepos(list, "idle-asc").map((r) => r.name), ["b", "a"]);
  const q = filtersToQuery(f({ q: "zap", idle: "3y", archived: true }));
  assert.equal(q, "?q=zap&idle=3y&archived=1");
  assert.equal(filtersToQuery(f({ reminder: "open", noise: true })), "?reminder=open&noise=1");
  assert.deepEqual(filtersFromQuery(q), f({ q: "zap", idle: "3y", archived: true }));
  assert.equal(filtersFromQuery("?idle=bogus").idle, DEFAULT_FILTERS.idle);
});

test("the generator writes compact records the page reads", () => {
  const here = new URL("..", import.meta.url).pathname;
  const out = execFileSync("python3", ["-c", `
import json, sys; sys.path.insert(0, '.'); import generate_repo_list as g
d = g.build_data([{"name": "www-chapter-x", "html_url": "https://github.com/OWASP/www-chapter-x", "archived": False,
  "has_issues": False, "fork": True, "pushed_at": "2020-01-01T00:00:00Z", "stargazers_count": 0, "topics": ["a"]}], "owasp")
print(json.dumps(d))`], { cwd: here, encoding: "utf8" });
  const data = JSON.parse(out);
  assert.equal(data.total, 1);
  assert.deepEqual(data.repos[0], {
    name: "www-chapter-x", url: "https://github.com/OWASP/www-chapter-x", pushed: "2020-01-01T00:00:00Z",
    topics: ["a"], archived: false, issues_off: true, fork: true, kind: "chapter",
  });
});

test("Best to bump: important idle repos lead, quiet or recent ones follow", () => {
  const big = signal(repo({ stars: 2000, forks: 3000, issues: 100 }), { now: NOW });
  const small = signal(repo({ stars: 2 }), { now: NOW });
  const fresh = signal(repo({ stars: 2000, forks: 3000, issues: 100, pushed: "2026-09-01T00:00:00Z" }), { now: NOW });
  assert.ok(big.score > small.score && big.score > fresh.score);
  assert.ok(big.good.includes("★ 2k") && big.good.includes("idle 4y"));
  assert.match(big.why, /^Score \d+ = importance [\d.]+ × staleness [\d.]+ × noise 1\.00\nUp: /);
  // A bot's push doesn't count as upkeep: idleness runs from the last commit by a person.
  const bot = signal(repo({ stars: 50, pushed: "2026-09-01T00:00:00Z", human: "2021-01-01T00:00:00Z", bot_only: true }), { now: NOW });
  const human = signal(repo({ stars: 50, pushed: "2026-09-01T00:00:00Z", human: "2026-09-01T00:00:00Z" }), { now: NOW });
  assert.ok(bot.score > human.score && bot.good.includes("only bot commits lately"));
});

test("noise is pushed down and the clearest cases are low-signal", () => {
  const base = { stars: 300, forks: 50 };
  const clean = signal(repo(base), { now: NOW });
  assert.equal(clean.noise, false);
  for (const over of [{ fork: true }, { empty: true }, { description: "Deprecated: moved to OWASP/foo" }, { name: "www-project-x-old" },
    { reminder: { number: 4, url: "https://github.com/OWASP/x/issues/4", created: "2020-01-01T00:00:00Z" } }]) {
    const s = signal(repo({ ...base, ...over }), { now: NOW });
    assert.ok(s.noise, JSON.stringify(over));
    assert.ok(s.score < clean.score / 3);
  }
  assert.ok(!signal(repo({ ...base, template: true }), { now: NOW }).noise);
  assert.ok(signal(repo(base), { now: NOW, bumped: { "www-project-x": "2026-10-01" } }).score < clean.score);
  const ctx = { now: NOW, bumped: {} };
  const list = scoreAll([repo({ ...base, fork: true })], ctx);
  assert.ok(!matches(list[0], f(), ctx));
  assert.ok(matches(list[0], f({ noise: true }), ctx));
});

test("near-duplicate siblings: only the best one leads", () => {
  assert.equal(siblingStem("owasp-mstg-crackme-a1"), "owasp-mstg-crackme");
  assert.equal(siblingStem("www-event-gassf-old"), "www-event-gassf");
  assert.equal(siblingStem("Top10"), "top10");
  const list = scoreAll([repo({ name: "crackme-a1", stars: 50 }), repo({ name: "crackme-a2", stars: 1 }), repo({ name: "crackme-a3" })], { now: NOW });
  assert.deepEqual(list.map((r) => r._sig.bad.some((b) => /1 of 3 similar/.test(b))), [false, true, true]);
});

test("open reminders: a recent one blocks a second bump and has its own filter", () => {
  const recent = repo({ reminder: { number: 1, url: "https://github.com/OWASP/x/issues/1", created: "2026-03-19T00:00:00Z" } });
  const old = repo({ reminder: { number: 79, url: "https://github.com/OWASP/x/issues/79", created: "2016-04-15T00:00:00Z" } });
  assert.match(bumpBlocker(recent, NOW), /Reminder #1 is already open \(since 2026-03-19\)/);
  assert.equal(bumpBlocker(old, NOW), "");
  const ctx = { now: NOW, bumped: {} };
  scoreAll([recent, old, repo({ name: "other" })], ctx);
  assert.ok(matches(old, f({ reminder: "open" }), ctx));
  assert.ok(matches(recent, f({ reminder: "open" }), ctx));
  assert.ok(!matches(repo({ name: "other" }), f({ reminder: "open" }), ctx));
  assert.ok(!matches(old, f({ reminder: "none", noise: true }), ctx));
});

test("last bump: reminder status, replies, closed reminders and your own bumps", () => {
  const rem = (over) => repo({ reminder: { number: 3, url: "https://github.com/OWASP/x/issues/3", created: "2025-06-01T00:00:00Z", state: "open", bumps: 2, ...over } });
  assert.equal(reminderStatus(repo()), "none");
  assert.equal(reminderStatus(rem({ replies: 0 })), "waiting");
  assert.equal(reminderStatus(rem({ replies: 4 })), "replied");
  assert.equal(reminderStatus(rem({ state: "closed", closed: "2026-09-01T00:00:00Z" })), "closed");
  const ctx = { now: NOW, bumped: {} };
  const closed = rem({ state: "closed", closed: "2026-09-01T00:00:00Z" });
  scoreAll([closed], ctx);
  assert.equal(bumpBlocker(closed, NOW), "");
  assert.ok(closed._sig.bad.some((b) => /reminder #3 closed 2026-09-01/.test(b)));
  assert.ok(matches(closed, f({ reminder: "closed", idle: "any" }), ctx));
  assert.ok(!matches(closed, f({ reminder: "open", idle: "any" }), ctx));
  const replied = rem({ replies: 4 });
  scoreAll([replied], ctx);
  assert.ok(matches(replied, f({ reminder: "replied", idle: "any" }), ctx));
  assert.ok(!matches(replied, f({ reminder: "waiting", idle: "any" }), ctx));
  assert.equal(lastBump(rem({}), { "www-project-x": "2026-10-01T00:00:00Z" }), "2026-10-01T00:00:00Z");
  assert.equal(lastBump(repo()), "");
  assert.deepEqual(sortRepos([repo({ name: "a" }), rem({})], "bump-desc").map((r) => r.name), ["www-project-x", "a"]);
});

test("the GraphQL path maps a repository node to the same record", () => {
  const here = new URL("..", import.meta.url).pathname;
  const out = execFileSync("python3", ["-c", `
import json, sys; sys.path.insert(0, '.'); import generate_repo_list as g
node = {"name": "www-project-x", "url": "https://github.com/OWASP/www-project-x", "stargazerCount": 12, "forkCount": 3,
  "createdAt": "2015-01-01T00:00:00Z", "pushedAt": "2020-01-01T00:00:00Z", "isArchived": False, "isFork": False,
  "isTemplate": False, "hasIssuesEnabled": True, "diskUsage": 40, "primaryLanguage": {"name": "HTML"},
  "repositoryTopics": {"nodes": [{"topic": {"name": "owasp"}}]}, "issues": {"totalCount": 2}, "pullRequests": {"totalCount": 1},
  "defaultBranchRef": {"target": {"history": {"nodes": [
    {"committedDate": "2020-01-01T00:00:00Z", "messageHeadline": "bump", "author": {"name": "dependabot[bot]", "user": None}},
    {"committedDate": "2019-05-01T00:00:00Z", "messageHeadline": "ci", "author": {"name": "x", "user": {"login": "github-actions[bot]", "url": ""}}}]}}},
  "indexMd": {"text": "---\\ntitle: OWASP X\\nlevel: 2\\npitch: Short pitch\\n---\\nbody"}}
print(json.dumps(g.repo_record(g._rest_shape(node))))`], { cwd: here, encoding: "utf8" });
  const r = JSON.parse(out);
  assert.equal(r.prs, 1);
  assert.equal(r.issues, 2);
  assert.equal(r.language, "HTML");
  assert.deepEqual(r.topics, ["owasp"]);
  assert.equal(r.commit.author, "dependabot[bot]");
  assert.equal(r.bot_only, true);
  assert.equal(r.human, "2019-05-01T00:00:00Z");
  assert.equal(r.title, "OWASP X");
  assert.equal(r.level, 2);
  assert.equal(r.kind, "site");
});

test("project mapping: homepage links a code repo to its owasp.org project page; topic opts out", () => {
  const here = new URL("..", import.meta.url).pathname;
  const out = execFileSync("python3", ["-c", `
import json, sys; sys.path.insert(0, '.'); import generate_repo_list as g
rows = [
  {"name": "owasp-ctf-in-a-box", "homepage": "https://owasp.github.io/owasp-ctf-in-a-box/"},
  {"name": "owasp-ctf-in-a-box", "homepage": "https://owasp.org/projects/ctf-in-a-box"},
  {"name": "wrongsecrets-ctf-party", "homepage": "https://owasp.org/www-project-wrongsecrets/"},
  {"name": "www-project-zap", "homepage": ""},
  {"name": "www-chapter-x", "homepage": ""},
  {"name": "tool", "homepage": "https://evil.example/owasp.org/projects/x", "topics": ["Bumper-Ignore"]},
]
print(json.dumps([g.repo_record(r) for r in rows]))`], { cwd: here, encoding: "utf8" });
  const r = JSON.parse(out);
  assert.deepEqual(r.map((x) => x.kind), ["other", "project", "project", "site", "chapter", "other"]);
  assert.equal(r[1].project_page, "https://owasp.org/projects/ctf-in-a-box");
  assert.equal(r[2].project_page, "https://owasp.org/projects/wrongsecrets");
  assert.equal(r[5].project_page, undefined);
  assert.equal(r[5].opted_out, true);
  assert.match(bumpBlocker(r[5], NOW), /Opted out/);
});

test("cooldown: a second reminder within a week needs a confirmation; wording never says 'today ago'", () => {
  const r = repo({ name: "owasp-ctf-in-a-box" });
  const today = new Date(NOW - 3600e3).toISOString();
  assert.equal(since(today, NOW), "today");
  assert.equal(since("2026-10-19T00:00:00Z", NOW), "3d ago");
  assert.equal(cooldown(r, {}, NOW), "");
  // Old saves held one time per repo; new ones keep a list.
  assert.match(cooldown(r, { "owasp-ctf-in-a-box": today }, NOW), /opened a reminder form for owasp-ctf-in-a-box today\.$/);
  assert.match(cooldown(r, { "owasp-ctf-in-a-box": [today, today, today] }, NOW), /today \(3 times in the last 7 days\)/);
  assert.equal(cooldown(r, { "owasp-ctf-in-a-box": ["2026-10-01T00:00:00Z"] }, NOW), "");
  const reminded = repo({ reminder: { number: 9, created: "2026-10-20T00:00:00Z", state: "open" } });
  assert.match(cooldown(reminded, {}, NOW), /Reminder #9 was opened on www-project-x 2d ago/);
  assert.equal(COOLDOWN_DAYS, 7);
  assert.doesNotMatch(bumpUrl(r, NOW), /today%20ago/);
  assert.match(decodeURIComponent(bumpUrl(r, NOW)), /Why am I seeing this, and how do I opt out\?\]\(https:\/\/bumper\.owaspblt\.org\/#why\)/);
});
