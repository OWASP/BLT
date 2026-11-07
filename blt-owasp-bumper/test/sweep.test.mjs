// The sweep (sweep.html): which projects look finished, and why.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";
import { assess, assessAll, csv, filterProjects, lastActivity, markdown, sortProjects, viewFromQuery, viewToQuery } from "../public/sweep.js";

const NOW = Date.parse("2026-11-07T00:00:00Z");
const project = (over = {}, code = {}, site = null) => ({
  slug: "x", title: "OWASP X", level: "incubator", listed: true, page: "https://owasp.org/projects/x", pitch: "",
  code: { repo: "OWASP/x", status: "success", human: "2026-10-01T00:00:00Z", commits_90d: 3, people_90d: 1, stars: 10, prs: {}, ...code },
  site: site || {},
  leaders: ["alice"],
  ...over,
});

test("an active project is left alone", () => {
  const a = assess(project(), NOW);
  assert.equal(a.rec, "active");
  assert.equal(a.score, 0);
  assert.ok(a.signals.some((s) => s.points === -30));
});

test("years idle, an unanswered reminder and a template page add up to archive", () => {
  const a = assess(project({}, {
    human: "2021-06-01T00:00:00Z", commits_90d: 0, people_90d: 0,
    reminder: { number: 7, url: "https://github.com/OWASP/x/issues/7", state: "open", created: "2026-05-01T00:00:00Z", replies: 0, by: "bob" },
  }, { repo: "OWASP/www-project-x", template_page: true, human: "2026-09-01T00:00:00Z" }), NOW);
  assert.equal(a.rec, "archive");
  assert.equal(a.score, 100);
  const text = a.signals.map((s) => s.text).join("\n");
  assert.match(text, /No commit by a person or release in 5 years \(last 2021-06-01\)/);
  assert.match(text, /Reminder #7 on OWASP\/x unanswered/);
  assert.match(text, /unedited www-project template/);
});

test("the website repository doesn't count as activity when there is a code repository", () => {
  const p = project({}, { human: "2022-01-01T00:00:00Z", commits_90d: 0 }, { repo: "OWASP/www-project-x", human: "2026-11-01T00:00:00Z" });
  assert.equal(lastActivity(p), "2022-01-01T00:00:00Z");
  assert.equal(lastActivity(project({}, { repo: "", human: "" }, { repo: "OWASP/www-project-x", human: "2026-01-01T00:00:00Z" })), "2026-01-01T00:00:00Z");
  // A release is activity.
  assert.equal(lastActivity(project({}, { human: "2020-01-01T00:00:00Z", release: "2025-01-01T00:00:00Z" })), "2025-01-01T00:00:00Z");
});

test("signs of life take points away: a reply from someone else, a release, many stars", () => {
  const idle = { human: "2023-11-01T00:00:00Z", commits_90d: 0, people_90d: 0 };
  const base = assess(project({}, idle), NOW).score;
  const replied = assess(project({}, { ...idle, reminder: { number: 2, state: "open", created: "2026-01-01T00:00:00Z", replies: 1, by: "bob", last_reply_by: "lead" } }), NOW);
  const selfReply = assess(project({}, { ...idle, reminder: { number: 2, state: "open", created: "2026-01-01T00:00:00Z", replies: 1, by: "bob", last_reply_by: "bob" } }), NOW);
  assert.equal(replied.score, base - 15);
  assert.equal(selfReply.score, base + 20);
  assert.equal(assess(project({}, { ...idle, stars: 5000 }), NOW).score, base - 10);
});

test("Flagship and Production projects, and archived links with a live website, are held for the leaders", () => {
  const dead = { human: "2019-01-01T00:00:00Z", commits_90d: 0, archived: true };
  const flagship = assess(project({ level: "flagship" }, dead), NOW);
  assert.equal(flagship.rec, "ask");
  assert.equal(flagship.caution, true);
  assert.equal(assess(project({}, dead), NOW).rec, "archive");
  const moved = assess(project({}, dead, { repo: "OWASP/www-project-x", human: "2026-08-01T00:00:00Z" }), NOW);
  assert.equal(moved.rec, "ask");
  assert.match(moved.signals.map((s) => s.text).join(), /archived on GitHub \(ended, or moved/);
});

test("missing repositories and projects no longer in the inventory", () => {
  assert.match(assess(project({}, { status: "Not Found", human: "" }), NOW).signals[0].text, /doesn't exist on GitHub/);
  assert.ok(assess(project({}, { repo: "", status: "", human: "" }), NOW).signals.some((s) => /lists no GitHub repository/.test(s.text)));
  assert.equal(assess(project({ listed: false }, { human: "2020-01-01T00:00:00Z", commits_90d: 0 }), NOW).rec, "delisted");
  assert.equal(assess(project({ listed: false }), NOW).rec, "unlisted_active");
  // A rate-limited read is not evidence.
  assert.equal(assess(project({}, { status: "API rate limit exceeded for 1.2.3.4", human: "" }), NOW).score, 0);
});

test("filtering, sorting, the shareable view and the exports", () => {
  const list = assessAll([
    project({ slug: "a", title: "Alpha" }),
    project({ slug: "b", title: "Beta", level: "lab" }, { human: "2020-01-01T00:00:00Z", commits_90d: 0, description: "Deprecated, see Y" }),
    project({ slug: "c", title: "Gamma <b>", listed: false }, { human: "2021-01-01T00:00:00Z", commits_90d: 0 }),
  ], NOW);
  assert.deepEqual(filterProjects(list, { rec: "suggested" }).map((p) => p.slug), ["b", "c"]);
  assert.deepEqual(filterProjects(list, { rec: "all", level: "lab" }).map((p) => p.slug), ["b"]);
  assert.deepEqual(filterProjects(list, { rec: "all", q: "ALICE gamma" }).map((p) => p.slug), ["c"]);
  assert.deepEqual(sortProjects(list, "title", "asc").map((p) => p.slug), ["a", "b", "c"]);
  assert.deepEqual(sortProjects(list, "score", "desc").map((p) => p.slug)[2], "a");
  assert.equal(viewToQuery({ q: "", rec: "archive", level: "", sort: "score", dir: "desc" }), "?rec=archive");
  assert.equal(viewFromQuery("?rec=archive&sort=title").sort, "title");

  const md = markdown(filterProjects(list, { rec: "suggested" }), NOW);
  assert.match(md, /^# OWASP projects suggested for archiving or inactive status \(2026-11-07\)/);
  assert.match(md, /## Archive \(1\)[\s\S]*- \[ \] \*\*\[Beta\]\(https:\/\/owasp\.org\/projects\/x\)\*\* \(Lab, score \d+\)/);
  assert.match(md, /Its description says "Deprecated"/);
  assert.match(md, /Gamma \\<b\\>/);

  const sheet = csv([project({ title: "=HYPERLINK(\"x\")" })].map((p) => (p._a = assess(p, NOW), p)));
  assert.match(sheet.split("\n")[1], /^"'=HYPERLINK\(""x""\)"/);
});

test("generate_sweep.py joins Bumper's repositories with the Matrix's projects and pull requests", () => {
  const here = new URL("..", import.meta.url).pathname;
  const out = execFileSync("python3", ["-c", `
import json, sys; sys.path.insert(0, '.'); import generate_sweep as g
from datetime import datetime, timezone
projects = [{"slug": "x", "title": "OWASP X", "level": "lab", "url": "https://owasp.org/projects/x", "repo_name": "OWASP/x",
  "www_repo": "OWASP/www-project-x", "github_status": "success", "commits_90d": 0, "stars": 4,
  "top_contributors": [{"login": "OWASPFoundation"}, {"login": "a"}, {"login": "b"}, {"login": "c"}, {"login": "d"}]},
  {"slug": "y", "title": "Y", "listed": False, "repo_name": "someone/y", "www_repo": "OWASP/www-project-y", "github_status": "success"}]
repos = [{"name": "x", "human": "2022-01-01T00:00:00Z", "reminder": {"number": 3, "state": "open", "created": "2026-01-01T00:00:00Z", "replies": 1, "author": "bob", "last_reply": {"author": "lead"}}},
  {"name": "www-project-x", "human": "2026-10-01T00:00:00Z", "template_page": True}]
prs = [{"repo": "OWASP/x", "updated_at": "2024-01-01T00:00:00Z", "bot": False}, {"repo": "owasp/x", "updated_at": "2026-11-01T00:00:00Z", "bot": True}]
print(json.dumps(g.build(projects, repos, prs, datetime(2026, 11, 7, tzinfo=timezone.utc))))`], { cwd: here, encoding: "utf8" });
  const [x, y] = JSON.parse(out).projects;
  assert.equal(x.code.human, "2022-01-01T00:00:00Z");
  assert.deepEqual(x.code.reminder, { number: 3, url: "", state: "open", created: "2026-01-01T00:00:00Z", closed: "", replies: 1, bumps: 1, by: "bob", last_reply_by: "lead" });
  assert.deepEqual(x.code.prs, { open: 2, human: 1, stale: 1, oldest: "2024-01-01T00:00:00Z" });
  assert.equal(x.site.template_page, true);
  assert.deepEqual(x.leaders, ["a", "b", "c"]);
  assert.equal(y.listed, false);
  assert.equal(y.code.in_org, false);
  assert.equal(y.code.human, undefined);
});

test("generate_repo_list.py links repositories to owasp.org projects and spots template pages", () => {
  const here = new URL("..", import.meta.url).pathname;
  const out = execFileSync("python3", ["-c", `
import json, sys; sys.path.insert(0, '.'); import generate_repo_list as g
links = g.project_links([{"slug": "x", "title": "OWASP X", "level": "lab", "url": "https://owasp.org/projects/x", "repo_name": "OWASP/X-Tool", "www_repo": "OWASP/www-project-x"},
  {"slug": "z", "title": "Z", "repo_name": "elsewhere/z", "listed": False}], "owasp")
repos = [{"name": "X-Tool", "project": links.get("x-tool")}, {"name": "www-project-x", "project": links.get("www-project-x"), "template_page": True}]
print(json.dumps([g.repo_record(r) for r in repos]))`], { cwd: here, encoding: "utf8" });
  const [code, site] = JSON.parse(out);
  assert.equal(code.kind, "project");
  assert.equal(code.title, "OWASP X");
  assert.equal(code.level, 3);
  assert.equal(code.project_page, "https://owasp.org/projects/x");
  assert.deepEqual(code.project, { slug: "x", title: "OWASP X", level: "lab", listed: true, role: "code" });
  assert.equal(site.kind, "site");
  assert.equal(site.template_page, true);
  assert.equal(site.project.role, "site");
});
