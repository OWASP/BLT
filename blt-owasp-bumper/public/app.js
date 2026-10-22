// Bumper page: loads data/repos.json (refreshed daily into KV by scripts/refresh-kv.sh), filters
// and sorts it, and opens prefilled reminder issues for the selected repositories in batches.
import {
  BATCH_SIZE, DEFAULT_FILTERS, IDLE, ago, bumpBlocker, bumpUrl, checklist, escapeHtml, filtersFromQuery,
  filtersToQuery, idleYears, lastActive, matches, openReminder, safeUrl, scoreAll, sortRepos,
} from "./bumper.js";

const PAGE = 200;
const BUMPED_KEY = "bumper-bumped";
const KIND_LABEL = { project: "Project", chapter: "Chapter", other: "Repo" };
const TILES = [
  { idle: "any", label: "All repositories", minor: true },
  { idle: "active", label: "Active < 1y", color: "var(--ok)" },
  { idle: "1y", label: "Idle 1y+", color: "var(--warn)" },
  { idle: "3y", label: "Idle 3y+", color: "var(--bad)" },
  { idle: "5y", label: "Idle 5y+", color: "var(--bad)", minor: true },
];

const $ = (id) => document.getElementById(id);
const form = $("filters");
const now = Date.now();
let repos = [];
let byName = new Map();
let filters = filtersFromQuery(location.search);
let matched = [];
let limit = PAGE;
let lastClicked = -1;
const selected = new Set();
let bumped = load();

function load() {
  try { return JSON.parse(localStorage.getItem(BUMPED_KEY)) || {}; } catch { return {}; }
}
function save() {
  try { localStorage.setItem(BUMPED_KEY, JSON.stringify(bumped)); } catch { /* private mode: not remembered */ }
}
const fmt = (n) => n.toLocaleString("en-US");
const plural = (n, word) => `${fmt(n)} ${word}${n === 1 ? "" : "s"}`;
const bumpable = (r) => !bumpBlocker(r, now);

async function init() {
  for (const [value, { label }] of Object.entries(IDLE)) form.idle.add(new Option(label, value));
  try {
    const res = await fetch("data/repos.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    repos = data.repos || [];
    $("stamp").textContent = `${fmt(repos.length)} ${String(data.org || "OWASP").toUpperCase()} repositories · data from ${new Date(data.generated_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}`;
  } catch (err) {
    $("stamp").textContent = `Couldn't load the repository list (${err.message}).`;
    return;
  }
  byName = new Map(repos.map((r) => [r.name, r]));
  scoreAll(repos, { now, bumped });
  fillSelect(form.lang, repos.map((r) => r.language || "none"), (v) => (v === "none" ? "No language" : v), true);
  fillSelect(form.created, repos.map((r) => String(r.created || "").slice(0, 4)).filter(Boolean), (v) => `Created ${v}`, false);
  const reminders = repos.filter((r) => openReminder(r)).length;
  form.reminder.options[1].text = `Open reminder (${fmt(reminders)})`;
  form.reminder.options[2].text = `No open reminder (${fmt(repos.length - reminders)})`;
  writeForm();
  update();
}

// Options with counts; by count (languages) or newest first (years).
function fillSelect(select, values, label, byCount) {
  const counts = new Map();
  for (const v of values) counts.set(v, (counts.get(v) || 0) + 1);
  const keys = [...counts.keys()].sort(byCount ? (a, b) => counts.get(b) - counts.get(a) : (a, b) => b.localeCompare(a));
  for (const k of keys) select.add(new Option(`${label(k)} (${fmt(counts.get(k))})`, k));
}

function writeForm() {
  for (const [k, v] of Object.entries(filters)) {
    const el = form.elements[k];
    if (!el) continue;
    if (el.type === "checkbox") el.checked = v;
    else el.value = v;
    if (el.tagName === "SELECT" && el.value !== v) { el.value = DEFAULT_FILTERS[k]; filters[k] = DEFAULT_FILTERS[k]; }
  }
}

function readForm() {
  const f = {};
  for (const k of Object.keys(DEFAULT_FILTERS)) {
    const el = form.elements[k];
    f[k] = el.type === "checkbox" ? el.checked : el.value.trim();
  }
  return f;
}

function update({ keepLimit = false, rescore = false } = {}) {
  if (!keepLimit) limit = PAGE;
  if (rescore) scoreAll(repos, { now, bumped });
  const ctx = { now, bumped };
  matched = sortRepos(repos.filter((r) => matches(r, filters, ctx)), filters.sort);
  history.replaceState(null, "", location.pathname + filtersToQuery(filters) + location.hash);
  renderTiles(ctx);
  renderRows();
  renderNoise(ctx);
  renderSortHeaders();
  renderBar();
}

const NOISE_GROUPS = [
  [/^reminder/, "already reminded"], [/^Issues are turned off/, "issues off"], [/^fork/, "fork"], [/^empty/, "empty"],
  [/^template/, "template"], [/^says it moved/, "moved / defunct"], [/^looks superseded/, "-old / -backup copy"],
  [/similar repos$/, "near-duplicate"],
];
function noiseGroup(reason) {
  const hit = NOISE_GROUPS.find(([re]) => re.test(reason));
  return hit ? hit[1] : reason;
}

// Low-signal rows are collapsed into one line under the table, with what they are.
function renderNoise(ctx) {
  const hidden = filters.noise ? [] : repos.filter((r) => !r.archived && r._sig.noise && matches(r, { ...filters, noise: true }, ctx));
  const note = $("noiseNote");
  note.hidden = hidden.length === 0;
  if (!hidden.length) return;
  const kinds = new Map();
  for (const r of hidden) {
    const k = noiseGroup(r._sig.bad[0]);
    kinds.set(k, (kinds.get(k) || 0) + 1);
  }
  const list = [...kinds].sort((a, b) => b[1] - a[1]).map(([k, n]) => `${k} (${n})`).join(" · ");
  note.innerHTML = `<b>${plural(hidden.length, "low-signal repo")}</b> collapsed: ${escapeHtml(list)}. <button type="button" class="linkbtn" id="showNoise">Show them</button>`;
}

function renderTiles(ctx) {
  // Counts honour every filter except Activity, so each tile says what that preset would show.
  const base = repos.filter((r) => matches(r, { ...filters, idle: "any" }, ctx));
  $("tiles").innerHTML = TILES.map((t) => {
    const n = base.filter((r) => IDLE[t.idle].test(idleYears(r, now))).length;
    const dot = t.color ? `<i class="dot" style="background:${t.color}"></i>` : "";
    return `<button type="button" class="tile${t.minor ? " minor" : ""}" data-idle="${t.idle}" aria-pressed="${filters.idle === t.idle}">
      <b>${fmt(n)}</b><span>${dot}${escapeHtml(t.label)}</span></button>`;
  }).join("");
}

function ageClass(years) {
  return years < 1 ? "ok" : years < 3 ? "warn" : "bad";
}

function row(r, i) {
  const blocker = bumpBlocker(r, now);
  const rem = openReminder(r);
  const remLink = rem ? `<a class="rem" href="${escapeHtml(safeUrl(rem.url))}" target="_blank" rel="noopener" title="Open reminder issue since ${escapeHtml(String(rem.created).slice(0, 10))}: comment there to follow up">🔔 #${escapeHtml(rem.number)} · ${escapeHtml(ago(rem.created, now))}</a>` : "";
  const sel = selected.has(r.name);
  const years = idleYears(r, now);
  const when = bumped[r.name];
  const pills = [
    remLink,
    r.archived ? `<span class="pill">Archived</span>` : "",
    r.issues_off && !r.archived ? `<span class="pill">Issues off</span>` : "",
    when ? `<span class="pill red" title="You opened a reminder form on ${escapeHtml(when.slice(0, 10))}">Bumped ${escapeHtml(ago(when, now))} ago</span>` : "",
  ].join(" ");
  const sig = r._sig;
  const chips = sig.bad.filter((b) => b !== blocker && !b.startsWith("you bumped") && !b.startsWith("reminder #")).slice(0, 2).map((b) => `<span class="why down">${escapeHtml(b)}</span>`)
    .concat(sig.good.slice(0, 2).map((g) => `<span class="why">${escapeHtml(g)}</span>`)).slice(0, 2).join("");
  const lang = r.language || "";
  const created = String(r.created || "").slice(0, 4);
  const desc = r.title || r.description || "";
  const bump = rem && blocker && !r.archived && !r.issues_off
    ? `<a class="bump" href="${escapeHtml(safeUrl(rem.url))}" target="_blank" rel="noopener" title="${escapeHtml(blocker)}: view it">#${escapeHtml(rem.number)}<span class="label">&nbsp;View</span></a>`
    : blocker
    ? `<span class="muted" title="${escapeHtml(blocker)}">–</span>`
    : `<a class="bump${when ? " done" : ""}" href="${escapeHtml(bumpUrl(r, now))}" target="_blank" rel="noopener" data-bump="${escapeHtml(r.name)}" title="Open a prefilled reminder issue on GitHub">🔔<span class="label">&nbsp;${when ? "Again" : "Bump"}</span></a>`;
  return `<tr data-i="${i}"${sel ? ' class="sel"' : ""}>
    <td class="c-sel"><input type="checkbox" data-name="${escapeHtml(r.name)}"${sel ? " checked" : ""}${blocker ? ` disabled title="${escapeHtml(blocker)}"` : ""} aria-label="Select ${escapeHtml(r.name)}"></td>
    <td><a class="name" href="${escapeHtml(safeUrl(r.url))}" target="_blank" rel="noopener">${escapeHtml(r.name)}</a> ${pills}${chips ? `<span class="whys" title="${escapeHtml(sig.why)}">${chips}</span>` : ""}
      ${desc ? `<div class="desc" title="${escapeHtml(desc)}">${escapeHtml(desc)}</div>` : ""}
      <div class="meta" title="${escapeHtml(sig.why)}">${escapeHtml([blocker ? "" : `score ${sig.score}`, KIND_LABEL[r.kind], lang, created && `created ${created}`].filter(Boolean).join(" · "))}</div></td>
    <td class="num c-score"><span class="score${sig.noise ? " low" : ""}" title="${escapeHtml(sig.why)}">${blocker ? "–" : sig.score}</span></td>
    <td class="c-kind nowrap"><span class="pill">${KIND_LABEL[r.kind] || "Repo"}</span><span class="sub">${escapeHtml(lang)}</span></td>
    <td class="c-age nowrap"><span class="age ${ageClass(years)}">${escapeHtml(ago(lastActive(r), now))}</span><span class="sub">${escapeHtml(lastActive(r).slice(0, 10))}</span></td>
    <td class="c-created nowrap">${escapeHtml(created)}</td>
    <td class="num c-stars">${fmt(r.stars || 0)}</td>
    <td class="num c-issues">${fmt(r.issues || 0)}</td>
    <td class="c-bump">${bump}</td>
  </tr>`;
}

function renderRows() {
  $("rows").innerHTML = matched.slice(0, limit).map(row).join("");
  $("empty").hidden = matched.length > 0;
  const more = $("more");
  more.hidden = matched.length <= limit;
  more.textContent = `Show all ${fmt(matched.length)} (${fmt(matched.length - limit)} more)`;
}

function renderSortHeaders() {
  const [key, dir] = filters.sort.split("-");
  for (const b of document.querySelectorAll("th button[data-sort]")) {
    if (b.dataset.sort === key) b.dataset.dir = dir;
    else delete b.dataset.dir;
  }
}

function selectedRepos() {
  // In the table's order first, then any selected repos the filters now hide.
  const inView = matched.filter((r) => selected.has(r.name));
  const seen = new Set(inView.map((r) => r.name));
  return inView.concat([...selected].filter((n) => !seen.has(n)).map((n) => byName.get(n)).filter(Boolean));
}

function renderBar() {
  const n = selected.size;
  const eligible = matched.filter(bumpable);
  const hidden = n - matched.filter((r) => selected.has(r.name)).length;
  $("count").innerHTML = `<b>${fmt(n)}</b> selected${hidden ? ` <span class="muted">(${fmt(hidden)} hidden by filters)</span>` : ""}`;
  const allIn = eligible.length > 0 && eligible.every((r) => selected.has(r.name));
  const selAll = $("selAll");
  selAll.hidden = allIn || eligible.length === 0;
  selAll.textContent = `Select all ${fmt(eligible.length)} matching`;
  $("clear").hidden = n === 0;
  const head = $("headAll");
  head.checked = allIn;
  head.indeterminate = !allIn && eligible.some((r) => selected.has(r.name));
  head.disabled = eligible.length === 0;
  $("copy").disabled = n === 0;
  const open = $("open");
  open.disabled = n === 0;
  open.textContent = n === 0 ? "Open issue forms" : n <= BATCH_SIZE ? `Open ${plural(n, "issue form")}` : `Open next ${BATCH_SIZE} of ${fmt(n)}`;
}

function say(text, warn = false) {
  const msg = $("msg");
  msg.textContent = text;
  msg.classList.toggle("warn", warn);
}

function setSelected(names, on) {
  for (const name of names) {
    if (on && bumpable(byName.get(name) || { archived: true })) selected.add(name);
    else selected.delete(name);
  }
}

// Ticks and row highlights in place, so keyboard focus stays where it was.
function afterSelect() {
  for (const box of document.querySelectorAll("#rows input[data-name]")) {
    box.checked = selected.has(box.dataset.name);
    box.closest("tr").classList.toggle("sel", box.checked);
  }
  renderBar();
  if (selected.size > BATCH_SIZE) {
    say(`${fmt(selected.size)} selected: forms open ${BATCH_SIZE} at a time so the browser doesn't block them. Click again for each batch, or copy the checklist.`);
  } else say("");
}

// Opens one batch. window.open must run inside the click handler, or popup blockers stop it.
function openBatch() {
  const batch = selectedRepos().slice(0, BATCH_SIZE);
  let opened = 0;
  const stamp = new Date().toISOString();
  for (const r of batch) {
    const w = window.open(bumpUrl(r, now), "_blank");
    if (!w) break;
    try { w.opener = null; } catch { /* cross-origin already */ }
    opened++;
    bumped[r.name] = stamp;
    selected.delete(r.name);
  }
  save();
  const left = selected.size;
  update({ keepLimit: true, rescore: true });
  if (opened === 0) {
    say("Your browser blocked the new tabs. Allow pop-ups for this site (the icon in the address bar), then click again.", true);
  } else if (opened < batch.length) {
    say(`Opened ${plural(opened, "form")}; the browser blocked the rest. Allow pop-ups for this site, then click again for the ${fmt(left)} left.`, true);
  } else {
    say(left ? `Opened ${plural(opened, "form")}. ${fmt(left)} still selected: click again for the next batch.` : `Opened ${plural(opened, "form")}. Review and submit each one on GitHub.`);
  }
}

async function copyChecklist() {
  const list = selectedRepos();
  const text = checklist(list, now);
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = Object.assign(document.createElement("textarea"), { value: text });
    document.body.append(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
  say(`Copied ${plural(list.length, "repository")} as a Markdown checklist with reminder links.`);
}

let typing;
form.addEventListener("input", (e) => {
  clearTimeout(typing);
  typing = setTimeout(() => { filters = readForm(); update(); }, e.target.type === "search" ? 120 : 0);
});
$("reset").addEventListener("click", () => { filters = { ...DEFAULT_FILTERS }; writeForm(); update(); });
$("tiles").addEventListener("click", (e) => {
  const t = e.target.closest(".tile");
  if (!t) return;
  filters.idle = t.dataset.idle;
  form.idle.value = filters.idle;
  update();
});
document.querySelector("thead").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-sort]");
  if (!b) return;
  const [key, dir] = filters.sort.split("-");
  const k = b.dataset.sort;
  filters.sort = `${k}-${k === key ? (dir === "asc" ? "desc" : "asc") : k === "name" ? "asc" : "desc"}`;
  if (![...form.sort.options].some((o) => o.value === filters.sort)) form.sort.add(new Option(b.textContent + (filters.sort.endsWith("asc") ? " ↑" : " ↓"), filters.sort));
  form.sort.value = filters.sort;
  update({ keepLimit: true });
});
$("headAll").addEventListener("change", (e) => {
  setSelected(matched.map((r) => r.name), e.target.checked);
  afterSelect();
});
$("rows").addEventListener("click", (e) => {
  const box = e.target.closest('input[type="checkbox"][data-name]');
  if (box) {
    // Shift-click ticks or unticks the whole range since the last click.
    const i = Number(box.closest("tr").dataset.i);
    const range = e.shiftKey && lastClicked >= 0 ? matched.slice(Math.min(i, lastClicked), Math.max(i, lastClicked) + 1) : [byName.get(box.dataset.name)];
    setSelected(range.map((r) => r.name), box.checked);
    lastClicked = i;
    afterSelect();
    return;
  }
  const bump = e.target.closest("a[data-bump]");
  if (bump) {
    bumped[bump.dataset.bump] = new Date().toISOString();
    save();
    setTimeout(() => update({ keepLimit: true, rescore: true }), 0);
  }
});
$("selAll").addEventListener("click", () => { setSelected(matched.map((r) => r.name), true); afterSelect(); });
$("clear").addEventListener("click", () => { selected.clear(); lastClicked = -1; afterSelect(); });
$("noiseNote").addEventListener("click", (e) => {
  if (!e.target.closest("#showNoise")) return;
  filters.noise = true;
  form.noise.checked = true;
  update({ keepLimit: true });
});
$("more").addEventListener("click", () => { limit = Infinity; renderRows(); });
$("open").addEventListener("click", openBatch);
$("copy").addEventListener("click", copyChecklist);

init();
