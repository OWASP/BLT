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

// Last push is the best activity signal; `updated` also moves when someone stars the repo.
export function lastActive(repo) {
  return repo.pushed || repo.updated || repo.created || "";
}

export function idleYears(repo, now = Date.now()) {
  const t = Date.parse(lastActive(repo));
  return Number.isNaN(t) ? 0 : (now - t) / YEAR;
}

// Why a repo can't get a reminder issue, or "" when it can.
export function bumpBlocker(repo) {
  if (repo.archived) return "Archived: issues are read-only";
  if (repo.issues_off) return "Issues are turned off";
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

export const IDLE = {
  any: { label: "Any activity", test: () => true },
  active: { label: "Active (pushed < 1y)", test: (y) => y < 1 },
  "1y": { label: "Idle 1y+", test: (y) => y >= 1 },
  "2y": { label: "Idle 2y+", test: (y) => y >= 2 },
  "3y": { label: "Idle 3y+", test: (y) => y >= 3 },
  "5y": { label: "Idle 5y+", test: (y) => y >= 5 },
};

export const DEFAULT_FILTERS = { q: "", kind: "all", idle: "1y", lang: "", created: "", archived: false, bumped: "any", sort: "idle-desc" };

export function matches(repo, f, { now = Date.now(), bumped = {} } = {}) {
  if (!f.archived && repo.archived) return false;
  if (f.kind !== "all" && repo.kind !== f.kind) return false;
  if (!(IDLE[f.idle] || IDLE.any).test(idleYears(repo, now))) return false;
  if (f.lang && (repo.language || "none") !== f.lang) return false;
  if (f.created && String(repo.created || "").slice(0, 4) !== f.created) return false;
  if (f.bumped === "not" && bumped[repo.name]) return false;
  if (f.bumped === "yes" && !bumped[repo.name]) return false;
  if (f.q) {
    const hay = [repo.name, repo.description, repo.title, repo.pitch, repo.language, repo.region, repo.country, ...(repo.topics || []), ...(repo.tags || [])]
      .join(" ")
      .toLowerCase();
    if (!f.q.toLowerCase().split(/\s+/).filter(Boolean).every((w) => hay.includes(w))) return false;
  }
  return true;
}

const SORT_KEYS = {
  idle: (r) => -Date.parse(lastActive(r)) || 0,
  name: (r) => r.name.toLowerCase(),
  stars: (r) => r.stars || 0,
  issues: (r) => r.issues || 0,
  created: (r) => Date.parse(r.created) || 0,
};

export function sortRepos(list, sort) {
  const [key, dir] = String(sort || "idle-desc").split("-");
  const get = SORT_KEYS[key] || SORT_KEYS.idle;
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
  return `Hello from the OWASP BLT team 👋

The last push to this repository was on ${when} (${ago(lastActive(repo), now)} ago). Could a maintainer let us know where it stands?

- **Still active?** A short update or a commit shows the project is maintained.
- **No longer maintained?** Please consider archiving it to keep the OWASP organization tidy.
- **Need help or resources?** Say so in a comment.

Thank you for contributing to the OWASP community!

---
*Opened with [OWASP Bumper](https://bumper.owaspblt.org/), part of [OWASP BLT](https://git.owaspblt.org/BLT).*`;
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
    (r) => `- [ ] [${r.name}](${safeUrl(r.url)}): last push ${lastActive(r).slice(0, 10) || "unknown"} · [open reminder](${bumpUrl(r, now)})`,
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
