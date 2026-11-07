// The sweep's logic (sweep.html draws it with sweep-app.js): which OWASP projects look finished,
// and why. Kept free of the DOM so test/sweep.test.mjs can run it under Node.
//
// Each project in data/sweep.json (generate_sweep.py) gets signals, each worth points and backed by
// one fact a reviewer can check. Points add up to a score from 0 to 100; the score and a few hard
// rules give the recommendation. Signals that a project is alive (a release, a commit, a maintainer
// answering a reminder, many users) take points away.

import { DAY, YEAR, ago, escapeHtml, safeUrl } from "./bumper.js";

export const RECS = {
  archive: { label: "Archive", order: 0, tone: "bad",
    help: "Strong evidence the project has ended: archive the repositories and move the project to inactive." },
  inactive: { label: "Mark inactive", order: 1, tone: "bad",
    help: "Idle for years with no sign of a maintainer: mark inactive (it can come back with new leaders)." },
  delisted: { label: "Archive website repo", order: 2, tone: "warn",
    help: "Not in the owasp.org project inventory, but its www-project repository is still open." },
  ask: { label: "Ask leaders first", order: 3, tone: "warn",
    help: "Quiet, but not conclusive, or a Flagship/Production project: ask the leaders (a Bumper reminder) before deciding." },
  unlisted_active: { label: "Active, not listed", order: 4, tone: "info",
    help: "Has recent commits but isn't in the owasp.org inventory: check whether it should be listed." },
  active: { label: "Active", order: 5, tone: "ok", help: "No reason to act." },
};

export const ARCHIVE_AT = 70;
export const INACTIVE_AT = 45;
export const ASK_AT = 25;

const DEFUNCT = /\b(defunct|deprecated|obsolete|unmaintained|no longer (maintained|active|supported|developed)|(has )?moved to|migrated to|superseded by|replaced by|discontinued)\b/i;
const BIG_USE = 1000;

const time = (iso) => {
  const t = Date.parse(iso || "");
  return Number.isNaN(t) ? null : t;
};
const years = (iso, now) => {
  const t = time(iso);
  return t === null ? null : (now - t) / YEAR;
};
const fmtYears = (y) => (y >= 2 ? `${Math.floor(y)} years` : y >= 1 ? "over a year" : `${Math.max(1, Math.round(y * 12))} months`);
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

// The newest human activity on the project: its code repository's last commit by a person (Bumper
// skips bot commits for OWASP repositories; for repositories elsewhere the Matrix's last commit,
// which may be a bot's) or its latest release. The website repository counts only when it is the
// project's only repository: OWASP staff edit every www-project site in bulk, which says nothing
// about the project.
export function lastActivity(p) {
  const code = p.code || {};
  const dates = [code.human || code.last_commit, code.release];
  if (!code.repo && p.site) dates.push(p.site.human);
  return dates.filter((d) => time(d) !== null).sort().pop() || "";
}

// A reminder is "unanswered" when nobody but its author has replied.
function reminderReplied(rem) {
  return rem.replies > 0 && rem.last_reply_by && rem.last_reply_by !== rem.by;
}

export function signals(p, now = Date.now()) {
  const out = [];
  const add = (points, text, kind = points > 0 ? "against" : "for") => out.push({ points, text, kind });
  const code = p.code || {};
  const site = p.site || {};
  const repoName = code.repo || site.repo || "its repository";

  const last = lastActivity(p);
  const idle = years(last, now);
  if (idle === null) {
    if (code.repo && code.status === "success") add(20, `No commit data for ${repoName}`);
  } else if (idle >= 1) {
    add(Math.min(60, Math.round(15 * idle)), `No commit by a person or release in ${fmtYears(idle)} (last ${last.slice(0, 10)})`);
  }

  if (!code.repo) add(25, "owasp.org lists no GitHub repository");
  else if (code.status === "Not Found") add(40, `${code.repo} doesn't exist on GitHub (404)`);
  else if (code.status && code.status !== "success" && !/rate limit|two-factor|not fetched/i.test(code.status)) {
    add(10, `GitHub refused ${code.repo}: ${code.status.slice(0, 80)}`);
  }
  if (code.archived && p.listed) {
    add(60, `${code.repo}, the repository owasp.org links, is archived on GitHub (ended, or moved: if moved, fix the link)`);
  }
  if (code.empty) add(20, `${code.repo} is empty`);
  if (code.bot_only && idle !== null && idle >= 1) add(0, "Only bots have committed lately", "info");

  const text = `${code.description || ""} ${site.description || ""} ${p.pitch || ""}`;
  const defunct = text.match(DEFUNCT);
  if (defunct) add(30, `Its description says "${defunct[0]}"`);
  if (site.template_page || (!site.repo && code.template_page)) add(20, "Its owasp.org page (index.md) is still the unedited www-project template");

  for (const [where, rem] of [["code", code.reminder], ["site", site.reminder]]) {
    if (!rem || !rem.number) continue;
    const age = (now - (time(rem.created) || now)) / DAY;
    const label = `Reminder #${rem.number} on ${where === "code" ? code.repo : site.repo}`;
    if (reminderReplied(rem)) add(-15, `${label}: ${rem.last_reply_by} replied`);
    else if (rem.state === "closed") add(10, `${label} was closed without a reply`);
    else if (age >= 30) add(20, `${label} unanswered for ${ago(rem.created, now)}`);
    else add(0, `${label} opened ${ago(rem.created, now)} ago, waiting`, "info");
  }

  const prs = code.prs || {};
  if (prs.stale >= 3) add(8, `${plural(prs.stale, "pull request")} by contributors untouched for over a year`);
  if (p.code && code.commits_90d === 0 && code.people_90d === 0 && idle !== null && idle < 1) {
    add(5, "No commits in the last 90 days");
  }

  const release = years(code.release, now);
  if (release !== null && release < 1) add(-25, `Released ${code.release.slice(0, 10)}`);
  if (code.commits_90d > 0) add(-30, `${plural(code.commits_90d, "commit")} in the last 90 days`);
  if ((code.stars || 0) >= BIG_USE) add(-10, `${code.stars.toLocaleString("en-US")} stars: widely used, look for new leaders before archiving`);
  return out;
}

export function assess(p, now = Date.now()) {
  const list = signals(p, now);
  const score = Math.max(0, Math.min(100, list.reduce((s, x) => s + x.points, 0)));
  const idle = years(lastActivity(p), now);
  const code = p.code || {};
  const site = years(p.site && p.site.human, now);
  // Flagship and Production projects, and archived repositories whose project shows life elsewhere
  // (its website repository edited this year), go to the leaders before the working group acts.
  const careful = ["flagship", "production"].includes(p.level) || (code.archived && site !== null && site < 1);
  let rec;
  if (!p.listed) rec = idle !== null && idle < 1 ? "unlisted_active" : "delisted";
  else if (score >= ARCHIVE_AT || (code.archived && score >= INACTIVE_AT)) rec = "archive";
  else if (score >= INACTIVE_AT || code.archived) rec = "inactive";
  else if (score >= ASK_AT) rec = "ask";
  else rec = "active";
  const caution = careful && (rec === "archive" || rec === "inactive");
  if (caution) rec = "ask";
  const reminded = [code.reminder, p.site && p.site.reminder].some((r) => r && r.number);
  return { score, rec, signals: list, idle, reminded, caution };
}

export function assessAll(projects, now = Date.now()) {
  for (const p of projects) p._a = assess(p, now);
  return projects;
}

export const DEFAULT_VIEW = { q: "", rec: "suggested", level: "", sort: "score", dir: "desc" };

// "suggested" is every recommendation that asks the working group to act.
export const SUGGESTED = ["archive", "inactive", "delisted", "ask"];

export function filterProjects(projects, v = DEFAULT_VIEW) {
  const words = String(v.q || "").toLowerCase().split(/\s+/).filter(Boolean);
  return projects.filter((p) => {
    const a = p._a;
    if (v.rec === "suggested" ? !SUGGESTED.includes(a.rec) : v.rec && v.rec !== "all" && a.rec !== v.rec) return false;
    if (v.level && p.level !== v.level) return false;
    if (words.length) {
      const hay = [p.title, p.slug, p.code && p.code.repo, p.site && p.site.repo, p.pitch, ...(p.leaders || [])].join(" ").toLowerCase();
      if (!words.every((w) => hay.includes(w))) return false;
    }
    return true;
  });
}

const SORTS = {
  score: (p) => p._a.score,
  rec: (p) => -RECS[p._a.rec].order,
  title: (p) => String(p.title).toLowerCase(),
  idle: (p) => (p._a.idle === null ? 99 : p._a.idle),
  level: (p) => ["flagship", "production", "lab", "incubator", "other"].indexOf(p.level),
  stars: (p) => (p.code && p.code.stars) || 0,
};

export function sortProjects(list, sort = "score", dir = "desc") {
  const get = SORTS[sort] || SORTS.score;
  const sign = dir === "asc" ? 1 : -1;
  return list.slice().sort((a, b) => {
    const x = get(a), y = get(b);
    return (x < y ? -1 : x > y ? 1 : 0) * sign || b._a.score - a._a.score || String(a.title).localeCompare(String(b.title));
  });
}

const LEVEL_LABEL = { flagship: "Flagship", production: "Production", lab: "Lab", incubator: "Incubator", other: "Other" };
export const levelLabel = (level) => LEVEL_LABEL[level] || "Other";

// The list for the Project working group: Markdown, grouped by recommendation, every row with
// its links and evidence.
export function markdown(projects, now = Date.now(), source = "https://bumper.owaspblt.org/sweep") {
  const day = new Date(now).toISOString().slice(0, 10);
  const groups = Object.keys(RECS).filter((r) => r !== "active")
    .map((r) => [r, projects.filter((p) => p._a.rec === r)]).filter(([, list]) => list.length);
  const md = (s) => String(s || "").replace(/([\\[\]|*_`<>])/g, "\\$1");
  const lines = [`# OWASP projects suggested for archiving or inactive status (${day})`, "",
    `${projects.length} projects from ${source}. Each line lists the evidence; please check before acting.`, ""];
  for (const [rec, list] of groups) {
    lines.push(`## ${RECS[rec].label} (${list.length})`, "", RECS[rec].help, "");
    for (const p of list) {
      const a = p._a;
      const repo = p.code && p.code.repo ? ` · [${md(p.code.repo)}](${safeUrl(`https://github.com/${p.code.repo}`)})` : "";
      lines.push(`- [ ] **[${md(p.title)}](${safeUrl(p.page)})** (${levelLabel(p.level)}, score ${a.score})${repo}${a.caution ? ` · ⚠️ score says ${a.score >= ARCHIVE_AT ? "archive" : "inactive"}; held back for review` : ""}`);
      for (const s of a.signals.filter((x) => x.points !== 0)) lines.push(`  - ${s.points > 0 ? "" : "(in its favour) "}${md(s.text)}`);
    }
    lines.push("");
  }
  return lines.join("\n");
}

export function csv(projects) {
  const cell = (v) => {
    const s = String(v ?? "");
    // A leading = + - @ would run as a formula in a spreadsheet.
    const safe = /^[=+\-@\t\r]/.test(s) ? `'${s}` : s;
    return /[",\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
  };
  const head = ["project", "level", "listed", "recommendation", "score", "last_activity", "code_repo", "site_repo", "stars", "open_prs", "reminder", "evidence", "page"];
  const rows = projects.map((p) => {
    const a = p._a, code = p.code || {}, rem = code.reminder || (p.site && p.site.reminder) || {};
    return [p.title, p.level, p.listed ? "yes" : "no", RECS[a.rec].label, a.score, lastActivity(p).slice(0, 10), code.repo,
      p.site && p.site.repo, code.stars ?? "", code.prs ? code.prs.open : "", rem.url || "",
      a.signals.map((s) => `${s.points > 0 ? "+" : ""}${s.points} ${s.text}`).join("; "), p.page];
  });
  return [head, ...rows].map((r) => r.map(cell).join(",")).join("\n") + "\n";
}

export function viewFromQuery(search) {
  const q = new URLSearchParams(search);
  const v = { ...DEFAULT_VIEW };
  for (const k of Object.keys(v)) if (q.has(k)) v[k] = q.get(k);
  return v;
}

export function viewToQuery(v) {
  const q = new URLSearchParams();
  for (const [k, val] of Object.entries(v)) if (val !== DEFAULT_VIEW[k]) q.set(k, val);
  const s = q.toString();
  return s ? `?${s}` : "";
}

export { escapeHtml, safeUrl, ago };
