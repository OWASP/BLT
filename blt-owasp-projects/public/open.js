// Open issues and pull requests (open.html): every row of open_issues.json or open_prs.json in one
// sortable table, with quick views for finding work (good first issues, PRs waiting for review...),
// search and project, language and level filters. Every value from the data is escaped
// (escapeHtml / safeHref from safe-html.js): it comes from GitHub.
(function (root) {
  const DAY = 86400000;
  const PAGE = 200;
  const KINDS = { issues: "Open issues", prs: "Open pull requests" };

  const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : 0);
  const fmt = (v) => num(v).toLocaleString("en-US");

  function ago(iso, now = Date.now()) {
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return "";
    const days = Math.floor((now - t) / DAY);
    if (days < 1) return "today";
    if (days < 2) return "yesterday";
    if (days < 45) return `${days}d ago`;
    if (days < 365) return `${Math.round(days / 30)}mo ago`;
    return `${(days / 365).toFixed(1).replace(/\.0$/, "")}y ago`;
  }

  // GitHub logins are [A-Za-z0-9-] (bots add "[bot]"); anything else gets no avatar. The avatar host
  // allows other sites to show its images; github.com/<login>.png does not (Cross-Origin-Resource-Policy).
  function avatarUrl(login) {
    const name = String(login || "").replace(/\[bot\]$/, "");
    return /^[A-Za-z0-9-]+$/.test(name) ? `https://avatars.githubusercontent.com/${name}?s=48` : null;
  }

  // Label colours are six hex digits from GitHub; text is dark or light by the colour's luminance.
  function labelHtml([name, color]) {
    const hex = /^[0-9a-f]{6}$/i.test(color || "") ? color : "94a3b8";
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
    const light = 0.299 * r + 0.587 * g + 0.114 * b > 150;
    return `<span class="label" style="--label:#${hex};--label-text:${light ? "#1f2937" : "#fff"}">${escapeHtml(name)}</span>`;
  }

  const REVIEW = {
    APPROVED: ["Approved", "ok"],
    CHANGES_REQUESTED: ["Changes requested", "bad"],
    REVIEW_REQUIRED: ["Review required", "wait"],
  };

  function reviewOf(row) {
    if (row.draft) return "draft";
    return row.review || "none";
  }

  // Quick views. The label rules match scripts/fetch_open_work.py (open_summary.json's counts).
  const GOOD_FIRST = /good[\s_-]?first|first[\s_-]?timers?|beginner|\beasy\b|starter|newcomer|low[\s_-]?hanging/i;
  const HELP_WANTED = /help[\s_-]?wanted|contributions?[\s_-]?welcome|up[\s_-]?for[\s_-]?grabs/i;
  const QUICK_LINES = 50;
  // No earlier commit to the repository (GitHub's GraphQL reports most of these as NONE).
  const FIRST_TIME = ["FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "NONE"];
  const isQuick = (r) => num(r.additions) + num(r.deletions) >= 1 && num(r.additions) + num(r.deletions) <= QUICK_LINES;
  const labelled = (r, re) => r.labels.some(([name]) => re.test(name));
  const needsReview = (r) => !r.draft && r.review !== "APPROVED" && r.review !== "CHANGES_REQUESTED";
  const within = (iso, days, now) => now - (Date.parse(iso) || 0) < days * DAY;

  const VIEWS = {
    issues: [
      { id: "all", label: "All open", help: "Every open issue across OWASP projects." },
      { id: "good-first", label: "Good first issues", test: (r) => labelled(r, GOOD_FIRST),
        help: "Labelled for newcomers by their maintainers. Comment on the issue to say you're taking it before you start." },
      { id: "help-wanted", label: "Help wanted", test: (r) => labelled(r, HELP_WANTED),
        help: "Maintainers asked for outside help with these." },
      { id: "unassigned", label: "Unassigned, active", test: (r, now) => !r.assignees.length && within(r.updated_at, 90, now),
        help: "Nobody has claimed them, and they've seen activity in the last 90 days." },
      { id: "fresh", label: "New this month", test: (r, now) => within(r.created_at, 30, now), sort: "created",
        help: "Opened in the last 30 days, newest first." },
      { id: "no-replies", label: "No replies yet", test: (r) => r.comments === 0,
        help: "Nobody has answered these: a first reply, a reproduction or a triage label helps." },
    ],
    prs: [
      { id: "all", label: "All open", help: "Every open pull request across OWASP projects." },
      { id: "needs-review", label: "Needs review", test: needsReview,
        help: "Not a draft, and no approval or change request yet. A review from anyone helps maintainers merge faster." },
      { id: "quick", label: "Quick reviews", test: (r) => needsReview(r) && isQuick(r),
        help: `Waiting for review and ${QUICK_LINES} changed lines or fewer: a few minutes each.` },
      { id: "first-time", label: "New contributors", test: (r) => needsReview(r) && FIRST_TIME.includes(r.role),
        help: "Waiting for review, from people with no earlier commits to the repository. A friendly, prompt review keeps new contributors coming back." },
      { id: "waiting", label: "Waiting longest", test: needsReview, sort: "created", dir: 1,
        help: "Waiting for review, oldest first." },
      { id: "approved", label: "Approved, not merged", test: (r) => !r.draft && r.review === "APPROVED",
        help: "Approved but still open: often only a maintainer's merge away." },
      { id: "changes", label: "Changes requested", test: (r) => r.review === "CHANGES_REQUESTED",
        help: "The author has feedback to address." },
    ],
  };

  function viewOf(kind, id) {
    return VIEWS[kind].find((v) => v.id === id) || VIEWS[kind][0];
  }

  // Columns: label, sort key (a function of the row), default direction, cell renderer, kinds.
  const COLUMNS = [
    { id: "title", label: "Title", key: (r) => r.title.toLowerCase(), dir: 1, cell: titleCell },
    { id: "project", label: "Project", key: (r) => projectName(r).toLowerCase(), dir: 1, cell: projectCell },
    { id: "author", label: "Author", key: (r) => r.author.toLowerCase(), dir: 1, cell: authorCell },
    { id: "review", label: "Review", key: (r) => ["CHANGES_REQUESTED", "REVIEW_REQUIRED", "none", "APPROVED", "draft"].indexOf(reviewOf(r)), dir: 1, cell: reviewCell, kinds: ["prs"] },
    { id: "size", label: "Changes", key: (r) => num(r.additions) + num(r.deletions), dir: -1, cell: sizeCell, kinds: ["prs"], num: true },
    { id: "comments", label: "Comments", key: (r) => num(r.comments), dir: -1, cell: (r) => fmt(r.comments), num: true },
    { id: "assignees", label: "Assignees", key: (r) => r.assignees.length, dir: -1, cell: assigneesCell, kinds: ["issues"] },
    { id: "created", label: "Opened", key: (r) => Date.parse(r.created_at) || 0, dir: -1, cell: (r) => dateCell(r.created_at), num: true },
    { id: "updated", label: "Updated", key: (r) => Date.parse(r.updated_at) || 0, dir: -1, cell: (r) => dateCell(r.updated_at), num: true },
  ];

  function projectName(r) {
    return (r.projects && r.projects[0] && r.projects[0][1]) || r.repo;
  }

  function titleCell(r) {
    const draft = r.draft ? `<span class="badge draft">Draft</span>` : "";
    const labels = r.labels.length ? `<span class="labels">${r.labels.map(labelHtml).join("")}</span>` : "";
    return `<a class="item-title" href="${escapeHtml(safeHref(r.url) || "#")}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.title)}</a>
      <span class="item-meta">${draft}<span class="num">#${escapeHtml(r.number)}</span>${labels}</span>`;
  }

  function projectCell(r) {
    const more = r.projects && r.projects.length > 1 ? ` <span class="muted">+${r.projects.length - 1}</span>` : "";
    return `<span class="cell-stack"><span class="project">${escapeHtml(projectName(r))}${more}</span>
      <a class="repo" href="${escapeHtml(`https://github.com/${r.repo}`)}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.repo)}</a></span>`;
  }

  function authorCell(r) {
    const src = avatarUrl(r.author);
    const pic = src
      ? `<img src="${escapeHtml(src)}" alt="" width="24" height="24" loading="lazy" decoding="async">`
      : `<span class="avatar-blank" aria-hidden="true">?</span>`;
    const href = src ? `https://github.com/${r.author.replace(/\[bot\]$/, "")}` : "";
    const first = r.role && FIRST_TIME.includes(r.role) ? `<span class="badge first" title="No earlier commits to this repository">New</span>` : "";
    return `<span class="who">${pic}${href ? linkHtml(href, r.author) : escapeHtml(r.author)}</span>${first}`;
  }

  function reviewCell(r) {
    const state = reviewOf(r);
    if (state === "draft") return `<span class="badge draft">Draft</span>`;
    if (state === "none") return `<span class="muted">–</span>`;
    const [label, tone] = REVIEW[state] || [state, "wait"];
    return `<span class="badge ${tone}">${escapeHtml(label)}</span>`;
  }

  function sizeCell(r) {
    return `<span class="diff"><span class="add">+${fmt(r.additions)}</span> <span class="del">−${fmt(r.deletions)}</span></span>
      <span class="muted files">${fmt(r.files)} file${r.files === 1 ? "" : "s"}</span>`;
  }

  function assigneesCell(r) {
    if (!r.assignees.length) return `<span class="muted">–</span>`;
    return `<span class="stack">${r.assignees.map((a) => {
      const src = avatarUrl(a);
      return src ? `<img src="${escapeHtml(src)}" alt="${escapeHtml(a)}" title="${escapeHtml(a)}" width="22" height="22" loading="lazy">` : escapeHtml(a);
    }).join("")}</span>`;
  }

  function dateCell(iso) {
    return `<time datetime="${escapeHtml(iso)}" title="${escapeHtml(String(iso).slice(0, 10))}">${escapeHtml(ago(iso))}</time>`;
  }

  function columnsFor(kind) {
    return COLUMNS.filter((c) => !c.kinds || c.kinds.includes(kind));
  }

  function searchText(r) {
    return [r.title, r.repo, r.author, `#${r.number}`, r.lang, ...r.labels.map((l) => l[0]), ...r.assignees,
      ...(r.projects || []).map((p) => p[1])].join(" ").toLowerCase();
  }

  // Everything but the quick view: search, project, language, level, bots.
  function baseRows(rows, { q = "", repo = "", lang = "", level = "", bots = false } = {}) {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return rows
      .filter((r) => bots || !r.bot)
      .filter((r) => !repo || r.repo.toLowerCase() === repo.toLowerCase())
      .filter((r) => !lang || (r.lang || "none") === lang)
      .filter((r) => !level || (r.level || "other") === level)
      .filter((r) => words.every((w) => searchText(r).includes(w)));
  }

  function viewCounts(rows, kind, now = Date.now()) {
    return Object.fromEntries(VIEWS[kind].map((v) => [v.id, v.test ? rows.filter((r) => v.test(r, now)).length : rows.length]));
  }

  function filterRows(rows, state = {}, kind = "issues", now = Date.now()) {
    const { view = "all" } = state;
    const v = viewOf(kind, view);
    // A quick view brings its own order until a column is clicked.
    const sort = state.sort || v.sort || "updated";
    const dir = state.sort ? state.dir || 0 : v.dir || 0;
    const col = columnsFor(kind).find((c) => c.id === sort) || COLUMNS.find((c) => c.id === "updated");
    const d = dir || col.dir;
    return baseRows(rows, state)
      .filter((r) => !v.test || v.test(r, now))
      .map((r) => [col.key(r), r])
      .sort(([a, ra], [b, rb]) => (a < b ? -d : a > b ? d : 0) || (Date.parse(rb.updated_at) || 0) - (Date.parse(ra.updated_at) || 0))
      .map(([, r]) => r);
  }

  function headHtml(kind, sort, dir) {
    return `<tr>${columnsFor(kind).map((c) => {
      const active = c.id === sort;
      const d = active ? dir || c.dir : 0;
      const aria = active ? ` aria-sort="${d > 0 ? "ascending" : "descending"}"` : "";
      return `<th scope="col" class="col-${c.id}${c.num ? " n" : ""}"${aria}><button type="button" data-sort="${c.id}">${escapeHtml(c.label)}<span class="arrow" aria-hidden="true">${active ? (d > 0 ? "↑" : "↓") : "↕"}</span></button></th>`;
    }).join("")}</tr>`;
  }

  function rowHtml(r, kind) {
    return `<tr>${columnsFor(kind).map((c) => `<td class="col-${c.id}${c.num ? " n" : ""}" data-label="${escapeHtml(c.label)}">${c.cell(r)}</td>`).join("")}</tr>`;
  }

  function totalsHtml(rows) {
    const people = new Set(rows.map((r) => r.author));
    const repos = new Set(rows.map((r) => r.repo));
    const month = rows.filter((r) => Date.now() - (Date.parse(r.created_at) || 0) < 30 * DAY).length;
    const quiet = rows.filter((r) => Date.now() - (Date.parse(r.updated_at) || 0) > 180 * DAY).length;
    const stat = (v, l) => `<div class="stat"><dt>${escapeHtml(l)}</dt><dd>${escapeHtml(fmt(v))}</dd></div>`;
    return [stat(rows.length, "Open"), stat(repos.size, "Repositories"), stat(people.size, "Authors"),
      stat(month, "Opened in 30 days"), stat(quiet, "No update in 6 months")].join("");
  }

  async function load(kind) {
    const res = await fetch(`open_${kind}.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const rows = await res.json();
    return { rows: Array.isArray(rows) ? rows : [], updated: res.headers.get("x-data-updated-at") };
  }

  async function main() {
    const $ = (id) => document.getElementById(id);
    const params = new URLSearchParams(location.search);
    const kind = KINDS[params.get("kind")] ? params.get("kind") : "issues";
    const state = {
      view: viewOf(kind, params.get("view") || "all").id,
      q: params.get("q") || "",
      repo: params.get("repo") || "",
      lang: params.get("lang") || "",
      level: params.get("level") || "",
      bots: params.get("bots") === "1",
      sort: params.get("sort") || "",
      dir: Number(params.get("dir")) || 0,
    };
    let limit = PAGE;

    document.title = `${KINDS[kind]} · OWASP Project Matrix`;
    $("heading").textContent = KINDS[kind];
    $(`tab-${kind}`).setAttribute("aria-current", "page");
    // The bar's two links both point at open.html: mark only this kind's.
    for (const a of document.querySelectorAll("blt-nav > a[href^='open.html']")) {
      a.setAttribute("aria-current", a.getAttribute("href").includes(`kind=${kind}`) ? "page" : "false");
    }
    $("q").value = state.q;
    $("level").value = state.level;
    $("bots").checked = state.bots;

    let rows;
    try {
      const data = await load(kind);
      rows = data.rows;
      if (data.updated && !Number.isNaN(Date.parse(data.updated))) $("updated").textContent = `Data refreshed ${ago(data.updated)}.`;
    } catch (e) {
      console.error(`Failed to load open ${kind}:`, e);
      $("count").textContent = "Unable to load the list. Please try again later.";
      return;
    }
    // The other tab's count, without blocking this one.
    const other = kind === "issues" ? "prs" : "issues";
    load(other).then(({ rows: o }) => { $(`n-${other}`).textContent = fmt(o.filter((r) => !r.bot).length); }).catch(() => {});

    if (!rows.length) {
      $("count").textContent = "No data yet.";
      return;
    }

    // Project filter: one option per repository, named after its project; language by count.
    const repos = new Map();
    const langs = new Map();
    for (const r of rows) {
      const k = r.repo.toLowerCase();
      if (!repos.has(k)) repos.set(k, { repo: r.repo, name: projectName(r), n: 0 });
      if (!r.bot) {
        repos.get(k).n += 1;
        langs.set(r.lang || "none", (langs.get(r.lang || "none") || 0) + 1);
      }
    }
    $("project").insertAdjacentHTML("beforeend", [...repos.values()]
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((p) => `<option value="${escapeHtml(p.repo)}">${escapeHtml(p.name === p.repo ? p.repo : `${p.name} · ${p.repo}`)} (${fmt(p.n)})</option>`).join(""));
    if (state.repo && !repos.has(state.repo.toLowerCase())) {
      $("project").insertAdjacentHTML("beforeend", `<option value="${escapeHtml(state.repo)}">${escapeHtml(state.repo)} (0)</option>`);
    }
    $("project").value = [...$("project").options].find((o) => o.value.toLowerCase() === state.repo.toLowerCase())?.value || "";
    $("lang").insertAdjacentHTML("beforeend", [...langs.entries()].sort((a, b) => b[1] - a[1])
      .map(([l, n]) => `<option value="${escapeHtml(l)}">${escapeHtml(l === "none" ? "No language" : l)} (${fmt(n)})</option>`).join(""));
    $("lang").value = state.lang;

    function render() {
      const now = Date.now();
      const base = baseRows(rows, state);
      const counts = viewCounts(base, kind, now);
      const v = viewOf(kind, state.view);
      $("views").innerHTML = VIEWS[kind].map((x) => `<button type="button" class="view${x.id === v.id ? " on" : ""}" data-view="${x.id}" aria-pressed="${x.id === v.id}">${escapeHtml(x.label)} <span>${fmt(counts[x.id])}</span></button>`).join("");
      $("view-help").textContent = v.help;
      const shown = filterRows(rows, state, kind, now);
      $(`n-${kind}`).textContent = fmt(rows.filter((r) => !r.bot).length);
      $("totals").innerHTML = totalsHtml(shown);
      const sort = state.sort || v.sort || "updated";
      $("thead").innerHTML = headHtml(kind, sort, state.sort ? state.dir : v.dir || 0);
      $("tbody").innerHTML = shown.slice(0, limit).map((r) => rowHtml(r, kind)).join("")
        || `<tr><td class="empty" colspan="${columnsFor(kind).length}">Nothing matches. Try another view or clear the filters.</td></tr>`;
      const noun = kind === "prs" ? "pull request" : "issue";
      $("count").textContent = shown.length === base.length
        ? `${fmt(shown.length)} open ${noun}${shown.length === 1 ? "" : "s"}`
        : `${fmt(shown.length)} of ${fmt(base.length)} open ${noun}s`;
      const left = shown.length - limit;
      $("more").hidden = left <= 0;
      $("more").textContent = `Show ${fmt(Math.min(left, PAGE))} more (${fmt(left)} left)`;

      const next = new URLSearchParams({ kind });
      for (const [k, val] of Object.entries(state)) {
        if (val && !(k === "view" && val === "all")) next.set(k, val === true ? "1" : String(val));
      }
      history.replaceState(null, "", `?${next}`);
    }

    const on = (id, event, apply) => $(id).addEventListener(event, () => { apply(); limit = PAGE; render(); });
    on("q", "input", () => { state.q = $("q").value; });
    on("project", "change", () => { state.repo = $("project").value; });
    on("lang", "change", () => { state.lang = $("lang").value; });
    on("level", "change", () => { state.level = $("level").value; });
    on("bots", "change", () => { state.bots = $("bots").checked; });
    $("views").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-view]");
      if (!b) return;
      state.view = b.dataset.view;
      state.sort = "";
      state.dir = 0;
      limit = PAGE;
      render();
      $("views").querySelector(`[data-view="${b.dataset.view}"]`).focus();
    });
    $("more").addEventListener("click", () => { limit += PAGE; render(); });
    $("thead").addEventListener("click", (e) => {
      const button = e.target.closest("button[data-sort]");
      if (!button) return;
      const col = COLUMNS.find((c) => c.id === button.dataset.sort);
      const v = viewOf(kind, state.view);
      const curSort = state.sort || v.sort || "updated";
      const curDir = (state.sort ? state.dir : v.dir) || COLUMNS.find((c) => c.id === curSort).dir;
      state.dir = curSort === col.id ? -curDir : col.dir;
      state.sort = col.id;
      render();
      $("thead").querySelector(`[data-sort="${col.id}"]`).focus();
    });
    render();
  }

  Object.assign(root, { filterRows, baseRows, viewCounts, VIEWS, rowHtml, headHtml, labelHtml, avatarUrl, columnsFor });
  if (typeof document !== "undefined" && document.getElementById("tbody")) main();
})(typeof globalThis !== "undefined" ? globalThis : this);
