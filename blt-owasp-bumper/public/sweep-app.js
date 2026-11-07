// Sweep page: loads data/sweep.json (refreshed daily into KV by scripts/refresh-kv.sh), scores each
// project with sweep.js and draws the table, tiles and exports.
import {
  RECS, SUGGESTED, ago, assessAll, csv, escapeHtml, filterProjects, lastActivity, levelLabel, markdown,
  safeUrl, sortProjects, viewFromQuery, viewToQuery,
} from "./sweep.js";

const $ = (id) => document.getElementById(id);
const form = $("filters");
const now = Date.now();
let projects = [];
let shown = [];
let view = viewFromQuery(location.search);

const fmt = (n) => Number(n || 0).toLocaleString("en-US");
const level = (p) => `<span class="pill">${escapeHtml(levelLabel(p.level))}</span>`;
const gh = (full) => (full ? `https://github.com/${full}` : "");

async function init() {
  try {
    const res = await fetch("data/sweep.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    projects = assessAll(data.projects || [], now);
    const when = new Date(data.generated_at);
    $("stamp").textContent = `${fmt(projects.length)} projects · data from ${when.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}`;
  } catch (err) {
    $("stamp").textContent = `Couldn't load the project data (${err.message}).`;
    return;
  }
  for (const el of form.elements) el.value = view[el.name] ?? "";
  form.addEventListener("input", () => {
    view = { ...view, q: form.q.value, rec: form.rec.value, level: form.level.value };
    render();
  });
  document.querySelector("thead").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-sort]");
    if (!b) return;
    const key = b.dataset.sort;
    const first = key === "title" || key === "level" ? "asc" : "desc";
    view = { ...view, sort: key, dir: view.sort === key ? (view.dir === "asc" ? "desc" : "asc") : first };
    render();
  });
  $("tiles").addEventListener("click", (e) => {
    const t = e.target.closest("[data-rec]");
    if (!t) return;
    view = { ...view, rec: t.dataset.rec };
    form.rec.value = view.rec;
    render();
  });
  $("copy").addEventListener("click", copyList);
  $("csv").addEventListener("click", downloadCsv);
  render();
}

function tiles() {
  const count = (rec) => projects.filter((p) => p._a.rec === rec).length;
  const items = [
    ["suggested", "All suggestions", projects.filter((p) => SUGGESTED.includes(p._a.rec)).length, ""],
    ...["archive", "inactive", "delisted", "ask", "unlisted_active"].map((r) => [r, RECS[r].label, count(r), RECS[r].tone]),
  ];
  $("tiles").innerHTML = items.map(([rec, label, n, tone]) =>
    `<button type="button" class="tile" data-rec="${rec}" aria-pressed="${view.rec === rec}" title="${escapeHtml(RECS[rec] ? RECS[rec].help : "Everything the working group could act on")}">
      <b>${fmt(n)}</b><span>${tone ? `<i class="dot ${tone}"></i>` : ""}${escapeHtml(label)}</span></button>`).join("");
}

function lastCell(p) {
  const last = lastActivity(p);
  if (!last) return `<span class="never">no data</span>`;
  const years = (now - Date.parse(last)) / (365.25 * 86400000);
  const tone = years >= 3 ? "bad" : years >= 1 ? "warn" : "ok";
  return `<span class="age ${tone}">${escapeHtml(ago(last, now))}</span><span class="sub">${escapeHtml(last.slice(0, 10))}</span>`;
}

function evidence(p) {
  const items = p._a.signals.map((s) => {
    const pts = s.points ? `${s.points > 0 ? "+" : "−"}${Math.abs(s.points)}` : "";
    return `<li class="${s.kind}"><span class="pts">${pts}</span><span>${escapeHtml(s.text)}</span></li>`;
  });
  return items.length ? `<ul class="evidence">${items.join("")}</ul>` : `<span class="muted">Nothing against it.</span>`;
}

function links(p) {
  const code = p.code || {}, site = p.site || {};
  const rem = [code.reminder, site.reminder].find((r) => r && r.number);
  const repo = code.repo || site.repo;
  return [
    p.page ? `<a href="${escapeHtml(safeUrl(p.page))}" target="_blank" rel="noopener">owasp.org</a>` : "",
    code.repo ? `<a href="${escapeHtml(safeUrl(gh(code.repo)))}" target="_blank" rel="noopener">${escapeHtml(code.repo)}</a>` : "",
    site.repo ? `<a href="${escapeHtml(safeUrl(gh(site.repo)))}" target="_blank" rel="noopener">website repo</a>` : "",
    rem ? `<a href="${escapeHtml(safeUrl(rem.url))}" target="_blank" rel="noopener">reminder #${escapeHtml(rem.number)}</a>` : "",
    repo && String(repo).toLowerCase().startsWith("owasp/") && !rem && !(code.repo ? code.archived : site.archived)
      ? `<a href="./?q=${encodeURIComponent(repo.split("/")[1])}&idle=any&noise=1">bump in Bumper</a>` : "",
  ].filter(Boolean).join("");
}

function row(p) {
  const a = p._a, r = RECS[a.rec];
  const why = a.signals.map((s) => `${s.points > 0 ? "+" : ""}${s.points} ${s.text}`).join("\n");
  const held = a.caution ? `<span class="caution">Score alone says ${a.score >= 70 ? "archive" : "mark inactive"}; held for review</span>` : "";
  const leaders = p.leaders && p.leaders.length ? `<span class="sub">Top contributors: ${p.leaders.map(escapeHtml).join(", ")}</span>` : "";
  return `<tr>
    <td><a class="name" href="${escapeHtml(safeUrl(p.page))}" target="_blank" rel="noopener">${escapeHtml(p.title)}</a>
      <div class="links">${links(p)}</div>${leaders}</td>
    <td class="c-level">${level(p)}</td>
    <td><span class="rec ${r.tone}" title="${escapeHtml(r.help)}">${escapeHtml(r.label)}</span>${held}</td>
    <td class="num c-score" title="${escapeHtml(`Score ${a.score}\n${why}`)}"><span class="score ${a.score >= 70 ? "hot" : a.score >= 45 ? "warm" : "plain"}">${a.score}</span></td>
    <td class="c-last nowrap">${lastCell(p)}</td>
    <td class="c-ev">${evidence(p)}</td>
    <td class="num c-stars">${p.code && p.code.stars != null ? fmt(p.code.stars) : "–"}</td>
  </tr>`;
}

function render() {
  tiles();
  shown = sortProjects(filterProjects(projects, view), view.sort, view.dir);
  $("rows").innerHTML = shown.map(row).join("") || `<tr><td colspan="7" class="empty">No projects match.</td></tr>`;
  $("count").textContent = `${fmt(shown.length)} project${shown.length === 1 ? "" : "s"}`;
  for (const b of document.querySelectorAll("thead button[data-sort]")) {
    if (b.dataset.sort === view.sort) b.dataset.dir = view.dir; else delete b.dataset.dir;
  }
  history.replaceState(null, "", `${location.pathname}${viewToQuery(view)}`);
}

async function copyList() {
  const text = markdown(shown.filter((p) => p._a.rec !== "active"), now, location.href);
  try {
    await navigator.clipboard.writeText(text);
    $("msg").textContent = `Copied ${fmt(shown.filter((p) => p._a.rec !== "active").length)} projects as a Markdown checklist, grouped by suggestion.`;
  } catch {
    $("msg").textContent = "The browser blocked the clipboard; use Download CSV instead.";
  }
}

function downloadCsv() {
  const blob = new Blob([csv(shown)], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `owasp-projects-to-archive-${new Date(now).toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

init();
