// Bumper's logic, kept free of the DOM so test/bumper.test.mjs can run it under Node: filtering,
// sorting, who can be bumped, and the prefilled "new issue" links. app.js draws the page.

export const BATCH_SIZE = 10;
export const DAY = 86400000;
export const YEAR = 365.25 * DAY;

export function escapeHtml(text) {
  if (text == null || text === "") return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Only http(s) URLs become links.
export function safeUrl(url) {
  const value = String(url || "").trim();
  return /^https?:\/\//i.test(value) ? value : "#";
}

// Upkeep is the last commit by a person on the default branch (with a token the generator
// skips bot commits); else the last push. `updated` also moves when someone stars the repo.
export function lastActive(repo) {
  return repo.human || repo.pushed || repo.updated || repo.created || "";
}

export function idleYears(repo, now = Date.now()) {
  const t = Date.parse(lastActive(repo));
  return Number.isNaN(t) ? 0 : (now - t) / YEAR;
}

// The repo's latest reminder issue (Bumper's or a hand-written "still maintained?"), if open.
export function openReminder(repo) {
  const rem = repo.reminder;
  return rem && rem.number && rem.state !== "closed" ? rem : null;
}

// "none" | "waiting" (open, no reply) | "replied" (open, with replies) | "closed".
export function reminderStatus(repo) {
  const rem = repo.reminder;
  if (!rem || !rem.number) return "none";
  if (rem.state === "closed") return "closed";
  return rem.replies ? "replied" : "waiting";
}

// When this repo was last bumped: its latest reminder issue, or a form you opened here.
export function lastBump(repo, bumped = {}) {
  const dates = [repo.reminder && repo.reminder.created, lastMine(bumped, repo.name)].filter(Boolean);
  return dates.sort().pop() || "";
}

// Why a repo can't get a reminder issue, or "" when it can. A reminder opened within the last
// year is still waiting on the maintainers: comment there instead of opening another.
export function bumpBlocker(repo, now = Date.now()) {
  if (repo.archived) return "Archived: issues are read-only";
  if (repo.issues_off) return "Issues are turned off";
  if (repo.opted_out) return "Opted out of reminders (topic bumper-ignore)";
  const rem = openReminder(repo);
  if (rem && now - Date.parse(rem.created) < YEAR) return `Reminder #${rem.number} is already open (since ${String(rem.created).slice(0, 10)})`;
  return "";
}

export function ago(dateStr, now = Date.now()) {
  const t = Date.parse(dateStr);
  if (Number.isNaN(t)) return "–";
  const days = Math.floor((now - t) / DAY);
  if (days < 1) return "today";
  if (days < 31) return `${days}d`;
  if (days < 365) return `${Math.floor(days / 30.44)}mo`;
  const years = days / 365.25;
  return years < 10 ? `${years.toFixed(1).replace(/\.0$/, "")}y` : `${Math.floor(years)}y`;
}

// "today", "3d ago", "2.4y ago": never "today ago".
export function since(dateStr, now = Date.now()) {
  const a = ago(dateStr, now);
  return a === "today" || a === "–" ? a : `${a} ago`;
}

// Reminder forms you opened from this browser: { repo: [ISO times] } (older saves held one time).
export const COOLDOWN_DAYS = 7;
export function myBumps(bumped, name) {
  const v = bumped[name];
  return Array.isArray(v) ? v : v ? [v] : [];
}
export function lastMine(bumped, name) {
  return myBumps(bumped, name).slice().sort().pop() || "";
}

// Why a new reminder now would be one too many, or "" when there is none: a form opened from
// here, or a reminder issue created, within the cooldown.
export function cooldown(repo, bumped = {}, now = Date.now()) {
  const recent = myBumps(bumped, repo.name).filter((d) => now - Date.parse(d) < COOLDOWN_DAYS * DAY);
  if (recent.length) {
    const last = recent.slice().sort().pop();
    return `You opened a reminder form for ${repo.name} ${since(last, now)}${recent.length > 1 ? ` (${recent.length} times in the last ${COOLDOWN_DAYS} days)` : ""}.`;
  }
  const rem = repo.reminder;
  if (rem && rem.created && now - Date.parse(rem.created) < COOLDOWN_DAYS * DAY) {
    return `Reminder #${rem.number} was opened on ${repo.name} ${since(rem.created, now)}.`;
  }
  return "";
}

export const IDLE = {
  any: { label: "Any activity", test: () => true },
  active: { label: "Active (pushed < 1y)", test: (y) => y < 1 },
  "1y": { label: "Idle 1y+", test: (y) => y >= 1 },
  "2y": { label: "Idle 2y+", test: (y) => y >= 2 },
  "3y": { label: "Idle 3y+", test: (y) => y >= 3 },
  "5y": { label: "Idle 5y+", test: (y) => y >= 5 },
};

export const DEFAULT_FILTERS = { q: "", kind: "all", idle: "1y", lang: "", created: "", reminder: "any", archived: false, noise: false, bumped: "any", sort: "score-desc" };

// ---- "Best to bump": how much a reminder is worth, and why ----------------------------------
//
// score = importance × staleness × noise. Importance is what a reminder could save: stars, forks,
// open issues and PRs (people still using or contributing), OWASP projects over other repos,
// project level, and stars arriving after the last push (interest without maintenance).
// Staleness grows with the years since the last push (pushes by bots don't count as upkeep).
// Noise multipliers push down repos a reminder won't help: forks, templates, empty repos, ones
// that say they moved or are defunct (archive them instead), "-old" copies, near-duplicate
// siblings, and repos already waiting on maintainers (an open reminder issue). Rows whose noise
// multiplier is 0.3 or less are "low-signal" and hidden by default.

const DEFUNCT = /\b(defunct|deprecated|obsolete|unmaintained|no longer (maintained|active|supported)|(has )?moved to|migrated to|superseded by|archived)\b/i;
const SUPERSEDED = /[-_.](old|archive|archived|backup|bak|deprecated|legacy)$/i;
const SIBLING = /[-_.](v?\d+(\.\d+)*|[a-z]\d+|\d{4})$/i;
export const NOISE_AT = 0.3;

const compact = (n) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/, "")}k` : String(n));
const log = (n) => Math.log10((n || 0) + 1);

// Name stem shared by numbered or lettered siblings (owasp-mstg-crackme-a1, -a2 -> owasp-mstg-crackme).
export function siblingStem(name) {
  return String(name).toLowerCase().replace(SUPERSEDED, "").replace(SIBLING, "");
}

export function signal(repo, { now = Date.now(), bumped = {}, siblings = 1, lead = true } = {}) {
  const blocker = bumpBlocker(repo, now);
  const good = [], bad = [];
  if (blocker) return { score: 0, noise: true, good, bad: [blocker], why: blocker };

  let importance = 1;
  const add = (points, label) => { importance += points; if (label && points >= 1) good.push([points, label]); };
  add(3 * log(repo.stars), repo.stars ? `★ ${compact(repo.stars)}` : "");
  add(2 * log(repo.forks), repo.forks >= 10 ? `${compact(repo.forks)} forks` : "");
  add(2 * log(repo.issues), repo.issues ? `${compact(repo.issues)} open issue${repo.issues === 1 ? "" : "s"}` : "");
  if (repo.prs) add(2 + 2 * log(repo.prs), `${repo.prs} open PR${repo.prs === 1 ? "" : "s"} waiting`);
  const kindPoints = { project: 3, site: 2, other: 1, chapter: 0 }[repo.kind] || 0;
  add(kindPoints, repo.kind === "project" || repo.kind === "site" ? "OWASP project" : "");
  if (repo.level) add(Number(repo.level) || 0, `level ${repo.level}`);
  if (repo.description || repo.title) add(0.5);
  const pushed = Date.parse(lastActive(repo)), touched = Date.parse(repo.updated);
  if (touched - pushed > 180 * DAY && repo.stars >= 5) add(1.5, "still getting stars");

  const years = idleYears(repo, now);
  const staleness = years < 1 ? 0.15 : Math.min(1, 0.45 + 0.11 * years);
  if (years >= 1) good.push([0.5 + years, `idle ${ago(lastActive(repo), now)}`]);
  if (repo.bot_only && years >= 1) good.push([0, "only bot commits lately"]);

  let noise = 1;
  const down = (factor, label) => { noise *= factor; bad.push(label); };
  if (openReminder(repo)) down(0.1, `reminder #${repo.reminder.number} open since ${String(repo.reminder.created).slice(0, 10)}`);
  else if (repo.reminder && repo.reminder.closed && now - Date.parse(repo.reminder.closed) < YEAR) {
    down(0.3, `reminder #${repo.reminder.number} closed ${String(repo.reminder.closed).slice(0, 10)}`);
  }
  if (repo.fork) down(0.2, "fork");
  if (repo.empty) down(0.1, "empty repo");
  if (repo.template) down(0.4, "template");
  if (DEFUNCT.test(`${repo.description || ""} ${repo.pitch || ""}`)) down(0.15, "says it moved or is defunct: archive instead");
  if (SUPERSEDED.test(repo.name)) down(0.3, "looks superseded");
  if (siblings > 1 && !lead) down(0.5, `1 of ${siblings} similar repos`);
  const low = noise <= NOISE_AT;
  if (myBumps(bumped, repo.name).length) down(0.15, "you opened a form");

  const score = Math.round(importance * staleness * noise * 10);
  good.sort((a, b) => b[0] - a[0]);
  const why = [
    `Score ${score} = importance ${importance.toFixed(1)} × staleness ${staleness.toFixed(2)} × noise ${noise.toFixed(2)}`,
    good.length ? `Up: ${good.map((g) => g[1]).join(", ")}` : "",
    bad.length ? `Down: ${bad.join(", ")}` : "",
  ].filter(Boolean).join("\n");
  return { score, noise: low, good: good.map((g) => g[1]), bad, why };
}

// Scores every repo; within a group of similar names only the best-scoring one leads.
export function scoreAll(repos, ctx = {}) {
  const groups = new Map();
  for (const r of repos) {
    const stem = siblingStem(r.name);
    if (!groups.has(stem)) groups.set(stem, []);
    groups.get(stem).push(r);
  }
  for (const group of groups.values()) {
    const ranked = group.map((r) => [r, signal(r, ctx)]).sort((a, b) => b[1].score - a[1].score);
    ranked.forEach(([r, s], i) => {
      r._sig = group.length > 1 && i > 0 ? signal(r, { ...ctx, siblings: group.length, lead: false }) : s;
    });
  }
  return repos;
}

export function matches(repo, f, { now = Date.now(), bumped = {} } = {}) {
  if (!f.archived && repo.archived) return false;
  if (f.reminder !== "any") {
    const status = reminderStatus(repo);
    const want = { open: ["waiting", "replied"], waiting: ["waiting"], replied: ["replied"], closed: ["closed"], none: ["none"] }[f.reminder];
    if (want && !want.includes(status)) return false;
  }
  if (!f.noise && f.reminder === "any" && repo._sig && repo._sig.noise && !repo.archived) return false;
  if (f.kind !== "all" && repo.kind !== f.kind) return false;
  if (!(IDLE[f.idle] || IDLE.any).test(idleYears(repo, now))) return false;
  if (f.lang && (repo.language || "none") !== f.lang) return false;
  if (f.created && String(repo.created || "").slice(0, 4) !== f.created) return false;
  if (f.bumped === "not" && myBumps(bumped, repo.name).length) return false;
  if (f.bumped === "yes" && !myBumps(bumped, repo.name).length) return false;
  if (f.q) {
    const hay = [repo.name, repo.description, repo.title, repo.pitch, repo.language, repo.region, repo.country, ...(repo.topics || []), ...(repo.tags || [])]
      .join(" ")
      .toLowerCase();
    if (!f.q.toLowerCase().split(/\s+/).filter(Boolean).every((w) => hay.includes(w))) return false;
  }
  return true;
}

const SORT_KEYS = {
  score: (r) => (r._sig ? r._sig.score : 0),
  bump: (r) => Date.parse((r.reminder && r.reminder.created) || "") || 0,
  idle: (r) => -Date.parse(lastActive(r)) || 0,
  name: (r) => r.name.toLowerCase(),
  stars: (r) => r.stars || 0,
  issues: (r) => r.issues || 0,
  created: (r) => Date.parse(r.created) || 0,
};

export function sortRepos(list, sort) {
  const [key, dir] = String(sort || "score-desc").split("-");
  const get = SORT_KEYS[key] || SORT_KEYS.score;
  const sign = dir === "asc" ? 1 : -1;
  return list.slice().sort((a, b) => {
    const x = get(a), y = get(b);
    return (x < y ? -1 : x > y ? 1 : 0) * sign || a.name.localeCompare(b.name);
  });
}

export function bumpTitle() {
  return "Is this repository still maintained?";
}

export function bumpBody(repo, now = Date.now()) {
  const when = lastActive(repo).slice(0, 10) || "a while ago";
  return `Hi! 👋 I'm checking in on idle repositories in the OWASP organization.

The last commit to this repository was on ${when} (${since(lastActive(repo), now)}). Could a maintainer let us know where it stands?

- **Still active?** A short update or a commit shows the project is maintained.
- **No longer maintained?** Please consider archiving it to keep the OWASP organization tidy.
- **Need help or resources?** Say so in a comment.

Thank you for contributing to the OWASP community!

---
*Opened with [OWASP Bumper](https://bumper.owaspblt.org/), part of [OWASP BLT](https://git.owaspblt.org/BLT). [Why am I seeing this, and how do I opt out?](https://bumper.owaspblt.org/#why)*`;
}

// GitHub's "new issue" form, prefilled. The maintainer-facing repos are OWASP's, on GitHub.
export function bumpUrl(repo, now = Date.now()) {
  const base = safeUrl(repo.url);
  if (base === "#") return "#";
  return `${base}/issues/new?title=${encodeURIComponent(bumpTitle())}&body=${encodeURIComponent(bumpBody(repo, now))}`;
}

export function checklist(repos, now = Date.now()) {
  const day = new Date(now).toISOString().slice(0, 10);
  const lines = repos.map(
    (r) => `- [ ] [${r.name}](${safeUrl(r.url)}): last active ${lastActive(r).slice(0, 10) || "unknown"} · [open reminder](${bumpUrl(r, now)})`,
  );
  return `OWASP repositories to bump (${repos.length}, from https://bumper.owaspblt.org/ on ${day})\n\n${lines.join("\n")}\n`;
}

// Filters <-> query string, so a filtered view can be shared as a link.
export function filtersFromQuery(search) {
  const p = new URLSearchParams(search);
  const f = { ...DEFAULT_FILTERS };
  for (const k of Object.keys(f)) {
    if (!p.has(k)) continue;
    f[k] = typeof f[k] === "boolean" ? p.get(k) === "1" : p.get(k);
  }
  if (!IDLE[f.idle]) f.idle = DEFAULT_FILTERS.idle;
  return f;
}

export function filtersToQuery(f) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(f)) {
    if (v === DEFAULT_FILTERS[k]) continue;
    p.set(k, typeof v === "boolean" ? (v ? "1" : "0") : v);
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}
