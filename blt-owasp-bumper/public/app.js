// Bumper page: loads data/repos.json (refreshed daily into KV by scripts/refresh-kv.sh), filters
// and sorts it, and opens prefilled reminder issues for the selected repositories in batches.
import {
  BATCH_SIZE, DEFAULT_FILTERS, IDLE, ago, bumpBlocker, bumpUrl, checklist, escapeHtml, filtersFromQuery,
  filtersToQuery, idleYears, lastActive, lastBump, lastMine, matches, myBumps, openReminder, reminderStatus, safeUrl,
  COOLDOWN_DAYS, cooldown, since, scoreAll, sortRepos,
} from "./bumper.js";

const PAGE = 200;
const BUMPED_KEY = "bumper-bumped";
const KIND_LABEL = { project: "Project", site: "Project site", chapter: "Chapter", other: "Repo" };
const KIND_TITLE = {
  project: "Its GitHub homepage is its owasp.org project page",
  site: "An owasp.org project website repo (www-project-*)",
  chapter: "An owasp.org chapter website repo (www-chapter-*)",
  other: "Not linked to an owasp.org project page: set the repo's homepage to link it (see Why am I seeing this?)",
};
const TILES = [
  { idle: "all", label: "All repositories", minor: true },
  { idle: "active", label: "Active < 1y", color: "var(--ok)" },
  { idle: "1y", label: "Idle 1y+", color: "var(--warn)" },
  { idle: "3y", label: "Idle 3y+", color: "var(--bad)" },
  { idle: "5y", label: "Idle 5y+", color: "var(--bad)", minor: true },
];

const $ = (id) => document.getElementById(id);
const form = $("filters");
const now = Date.now();
let repos = [];
let dataInfo = "";
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
    const when = new Date(data.generated_at);
    dataInfo = `data from ${when.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}, ${when.toISOString().slice(11, 16)} UTC`;
  } catch (err) {
    $("stamp").textContent = `Couldn't load the repository list (${err.message}).`;
    return;
  }
  byName = new Map(repos.map((r) => [r.name, r]));
  scoreAll(repos, { now, bumped });
  fillSelect(form.lang, repos.map((r) => r.language || "none"), (v) => (v === "none" ? "No language" : v), true);
  fillSelect(form.created, repos.map((r) => String(r.created || "").slice(0, 4)).filter(Boolean), (v) => `Created ${v}`, false);
  const counts = {};
  for (const r of repos) counts[reminderStatus(r)] = (counts[reminderStatus(r)] || 0) + 1;
  counts.open = (counts.waiting || 0) + (counts.replied || 0);
  for (const o of form.reminder.options) if (o.value !== "any") o.text += ` (${fmt(counts[o.value] || 0)})`;
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
  renderStamp(ctx);
  renderTiles(ctx);
  renderRows();
  renderNoise(ctx);
  renderSortHeaders();
  renderBar();
}

const NOISE_GROUPS = [
  [/^reminder/i, "already reminded"], [/^Issues are turned off/, "issues off"], [/^fork/, "fork"], [/^empty/, "empty"],
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

// Every repo is counted once: in view, or hidden as archived or low-signal (each with its toggle).
function renderStamp(ctx) {
  const archived = filters.archived ? 0 : repos.filter((r) => r.archived).length;
  const noise = filters.noise ? 0 : repos.filter((r) => !r.archived && r._sig.noise).length;
  const hidden = [archived && `${fmt(archived)} archived`, noise && `${fmt(noise)} low-signal`].filter(Boolean);
  const inView = repos.length - archived - noise;
  $("stamp").textContent = `${fmt(repos.length)} repositories${hidden.length ? `: ${fmt(inView)} in view, ${hidden.join(" and ")} hidden` : ""} · ${dataInfo}`;
}

function renderTiles(ctx) {
  // "All repositories" is the whole dataset and shows everything when clicked. The activity
  // tiles honour every other filter, so each says what that preset would show.
  const base = repos.filter((r) => matches(r, { ...filters, idle: "any" }, ctx));
  const everything = filters.idle === "any" && filters.archived && filters.noise;
  $("tiles").innerHTML = TILES.map((t) => {
    const n = t.idle === "all" ? repos.length : base.filter((r) => IDLE[t.idle].test(idleYears(r, now))).length;
    const pressed = t.idle === "all" ? everything : filters.idle === t.idle && !everything;
    const dot = t.color ? `<i class="dot" style="background:${t.color}"></i>` : "";
    return `<button type="button" class="tile${t.minor ? " minor" : ""}" data-idle="${t.idle}" aria-pressed="${pressed}">
      <b>${fmt(n)}</b><span>${dot}${escapeHtml(t.label)}</span></button>`;
  }).join("");
}

// Score colour: top tenth of idle repos (70+) solid, top quarter (40+) tinted, the rest plain.
function scoreTier(sig) {
  if (sig.noise) return "low";
  return sig.score >= 70 ? "hot" : sig.score >= 40 ? "warm" : "plain";
}

// One short note under the score, only when it says something the other columns don't.
const NOTES = [
  [/^fork$/, "fork", "down"], [/^empty/, "empty", "down"], [/^template/, "template", "down"],
  [/^says it moved/, "moved/defunct?", "down"], [/^looks superseded/, "-old copy", "down"],
  [/similar repos$/, "duplicate", "down"], [/^reminder #\d+ closed/, "recently closed", "down"], [/^you opened a form/, "form opened", "down"],
  [/^([5-9]|\d{2,}) open PRs waiting$/, "PRs waiting", "up"], [/^only bot commits/, "bot-only", "up"],
];
function scoreNote(sig, blocker) {
  if (blocker) return null;
  for (const reason of [...sig.bad, ...sig.good]) {
    const hit = NOTES.find(([re]) => re.test(reason));
    if (hit) return [hit[1], hit[2]];
  }
  return null;
}

function ageClass(years) {
  return years < 1 ? "ok" : years < 3 ? "warn" : "bad";
}

function row(r, i) {
  const blocker = bumpBlocker(r, now);
  const rem = openReminder(r);
  const remCell = reminderCell(r);
  const remLink = remCell.pill;
  const sel = selected.has(r.name);
  const years = idleYears(r, now);
  const cool = blocker ? "" : cooldown(r, bumped, now);
  const pills = [
    remLink,
    r.archived ? `<span class="pill">Archived</span>` : "",
    r.issues_off && !r.archived ? `<span class="pill">Issues off</span>` : "",
    r.opted_out && !r.archived ? `<span class="pill" title="The repo has the topic bumper-ignore">Opted out</span>` : "",
  ].join(" ");
  const sig = r._sig;
  const note = scoreNote(sig, blocker);
  const lang = r.language || "";
  const created = String(r.created || "").slice(0, 4);
  const desc = r.title || r.description || "";
  const bump = blocker
    ? `<span class="muted" title="${escapeHtml(blocker)}">–</span>`
    : `<a class="bump${cool ? " cool" : ""}" href="${escapeHtml(bumpUrl(r, now))}" target="_blank" rel="noopener" data-bump="${escapeHtml(r.name)}" title="${escapeHtml(cool ? `${cool} Wait ${COOLDOWN_DAYS} days between reminders.` : "Open GitHub's new-issue form on this repo, prefilled with a reminder")}">🔔<span class="label">&nbsp;${cool ? "Wait" : "Bump"}</span></a>`;
  return `<tr data-i="${i}"${sel ? ' class="sel"' : ""}>
    <td class="c-sel"><input type="checkbox" data-name="${escapeHtml(r.name)}"${sel ? " checked" : ""}${blocker ? ` disabled title="${escapeHtml(blocker)}"` : ""} aria-label="Select ${escapeHtml(r.name)}"></td>
    <td><a class="name" href="${escapeHtml(safeUrl(r.url))}" target="_blank" rel="noopener">${escapeHtml(r.name)}</a> ${pills}
      ${desc ? `<div class="desc" title="${escapeHtml(desc)}">${escapeHtml(desc)}</div>` : ""}
      <div class="meta" title="${escapeHtml(sig.why)}">${escapeHtml([blocker ? "" : `score ${sig.score}`, KIND_LABEL[r.kind], lang, created && `created ${created}`].filter(Boolean).join(" · "))}</div></td>
    <td class="num c-score" title="${escapeHtml(sig.why)}"><span class="score ${blocker ? "none" : scoreTier(sig)}">${blocker ? "–" : sig.score}</span>${note ? `<span class="sub note ${note[1]}">${escapeHtml(note[0])}</span>` : ""}</td>
    <td class="c-kind nowrap">${r.project_page
      ? `<a class="pill kind-${r.kind}" href="${escapeHtml(safeUrl(r.project_page))}" target="_blank" rel="noopener" title="${escapeHtml(KIND_TITLE[r.kind])}: ${escapeHtml(r.project_page)}">${KIND_LABEL[r.kind]}</a>`
      : `<span class="pill kind-${r.kind}" title="${escapeHtml(KIND_TITLE[r.kind] || "")}">${KIND_LABEL[r.kind] || "Repo"}</span>`}<span class="sub">${escapeHtml([lang, created].filter(Boolean).join(" · "))}</span></td>
    <td class="c-last nowrap">${remCell.cell}</td>
    <td class="c-age nowrap"><span class="age ${ageClass(years)}">${escapeHtml(ago(lastActive(r), now))}</span><span class="sub">${escapeHtml(lastActive(r).slice(0, 10))}</span></td>
    <td class="num c-stars"><span class="${r.stars >= 100 ? "strong" : ""}">${fmt(r.stars || 0)}</span><span class="sub">${r.forks ? `${fmt(r.forks)} forks` : "&nbsp;"}</span></td>
    <td class="num c-issues">${fmt(r.issues || 0)}</td>
    <td class="c-bump">${bump}</td>
  </tr>`;
}

// The repo's last bump: its latest reminder issue (link, age, replies) or a form you opened here.
function reminderCell(r) {
  const rem = r.reminder && r.reminder.number ? r.reminder : null;
  const mine = lastMine(bumped, r.name);
  const mineN = myBumps(bumped, r.name).length;
  const mineNote = mine ? `You opened a reminder form here ${mineN} time${mineN === 1 ? "" : "s"}, last ${since(mine, now)}; it shows on GitHub only once submitted.` : "";
  if (!rem) {
    return mine
      ? { pill: "", cell: `<span class="rem rem-mine" title="${escapeHtml(mineNote)}">🔔 ${mineN}× · ${escapeHtml(ago(mine, now))}</span><span class="sub">form${mineN === 1 ? "" : "s"} opened here</span>` }
      : { pill: "", cell: `<span class="never">never</span><span class="sub">&nbsp;</span>` };
  }
  const status = reminderStatus(r);
  const n = rem.bumps || 1;
  const reply = rem.last_reply && rem.last_reply.date ? rem.last_reply : null;
  const replies = rem.replies ? `${rem.replies} repl${rem.replies === 1 ? "y" : "ies"}` : "no reply";
  const title = [
    `Bumped ${n} time${n === 1 ? "" : "s"}. Latest: reminder #${rem.number}${rem.author ? ` by ${rem.author}` : ""}, opened ${String(rem.created).slice(0, 10)}`,
    status === "closed" ? `closed ${String(rem.closed).slice(0, 10)}` : "still open",
    reply ? `last reply by ${reply.author} on ${reply.date.slice(0, 10)}` : rem.replies ? replies : "no replies yet",
    mineNote,
  ].filter(Boolean).join(" · ");
  const top = `🔔 ${n}× · ${ago(rem.created, now)}`;
  const sub = `#${rem.number} · ${status === "closed" ? `closed ${since(rem.closed, now)}` : reply ? `${replies}, last ${since(reply.date, now)}` : replies}`;
  const href = escapeHtml(safeUrl(reply && reply.url ? reply.url : rem.url));
  return {
    pill: `<a class="rem rem-${status} rem-inline" href="${escapeHtml(safeUrl(rem.url))}" target="_blank" rel="noopener" title="${escapeHtml(title)}">${escapeHtml(top)} · ${escapeHtml(status === "closed" ? "closed" : replies)}</a>`,
    cell: `<a class="rem rem-${status}" href="${escapeHtml(safeUrl(rem.url))}" target="_blank" rel="noopener" title="${escapeHtml(title)}">${escapeHtml(top)}</a>`
      + `<a class="sub rem-sub rem-sub-${status}" href="${href}" target="_blank" rel="noopener" title="${escapeHtml(title)}">${escapeHtml(sub)}</a>`,
  };
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

// A message with one button; its click is a fresh user gesture, so it may open tabs.
function sayWithAction(text, label, action, warn = true) {
  const msg = $("msg");
  msg.textContent = `${text} `;
  msg.classList.toggle("warn", warn);
  const b = Object.assign(document.createElement("button"), { type: "button", className: "linkbtn", textContent: label });
  b.addEventListener("click", action);
  msg.append(b);
}

function record(name, stamp = new Date().toISOString()) {
  bumped[name] = [...myBumps(bumped, name), stamp].slice(-20);
}

function openForm(r) {
  const w = window.open(bumpUrl(r, now), "_blank");
  if (!w) return false;
  try { w.opener = null; } catch { /* cross-origin already */ }
  record(r.name);
  return true;
}

// Opens one batch. window.open must run inside the click handler, or popup blockers stop it.
// Repos inside their cooldown are held back unless the user says to open them anyway.
function openBatch(includeCooling = false) {
  const queue = selectedRepos();
  const cooling = includeCooling ? [] : queue.filter((r) => cooldown(r, bumped, now));
  const batch = queue.filter((r) => !cooling.includes(r)).slice(0, BATCH_SIZE);
  if (!batch.length && cooling.length) {
    sayWithAction(`${plural(cooling.length, "selected repo")} had a reminder in the last ${COOLDOWN_DAYS} days (${cooling.slice(0, 3).map((r) => r.name).join(", ")}${cooling.length > 3 ? "…" : ""}). One reminder a week is plenty.`,
      "Open them anyway", () => openBatch(true));
    return;
  }
  let opened = 0;
  for (const r of batch) {
    if (!openForm(r)) break;
    opened++;
    selected.delete(r.name);
  }
  save();
  const left = selected.size;
  update({ keepLimit: true, rescore: true });
  if (cooling.length && opened === batch.length) {
    sayWithAction(`Opened ${plural(opened, "form")}. Held back ${plural(cooling.length, "repo")} that had a reminder in the last ${COOLDOWN_DAYS} days.`,
      "Open those anyway", () => openBatch(true), false);
  } else if (opened === 0) {
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
  if (t.dataset.idle === "all") {
    filters = { ...filters, idle: "any", archived: true, noise: true };
    writeForm();
  } else {
    filters.idle = t.dataset.idle;
    form.idle.value = filters.idle;
  }
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
    const r = byName.get(bump.dataset.bump);
    const cool = r && cooldown(r, bumped, now);
    if (cool) {
      // Ask first: the button below is a new click, so the browser lets it open the tab.
      e.preventDefault();
      sayWithAction(`${cool} Another one this soon may feel like spam.`, "Open another anyway", () => {
        if (openForm(r)) { save(); say(`Opened a form for ${r.name}.`); update({ keepLimit: true, rescore: true }); }
      });
      return;
    }
    record(bump.dataset.bump);
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
$("open").addEventListener("click", () => openBatch());
$("copy").addEventListener("click", copyChecklist);

// Links to #why (from every reminder issue) and #about open that section.
function openSection() {
  const el = document.getElementById(location.hash.slice(1));
  if (el && el.tagName === "DETAILS") { el.open = true; el.scrollIntoView({ block: "start" }); }
}
window.addEventListener("hashchange", openSection);

init().then(openSection);
