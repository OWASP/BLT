// Open issues and pull requests (open.html): every row of open_issues.json or open_prs.json in one
// sortable table, with search, a project filter and, for pull requests, the review state. Every
// value from the data is escaped (escapeHtml / safeHref from safe-html.js): it comes from GitHub.
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

  // GitHub logins are [A-Za-z0-9-] (bots add "[bot]"); anything else gets no avatar.
  function avatarUrl(login) {
    const name = String(login || "").replace(/\[bot\]$/, "");
    return /^[A-Za-z0-9-]+$/.test(name) ? `https://github.com/${name}.png?size=48` : null;
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
    return `<span class="who">${pic}${href ? linkHtml(href, r.author) : escapeHtml(r.author)}</span>`;
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
    return [r.title, r.repo, r.author, `#${r.number}`, ...r.labels.map((l) => l[0]), ...r.assignees,
      ...(r.projects || []).map((p) => p[1])].join(" ").toLowerCase();
  }

  function filterRows(rows, { q = "", repo = "", review = "", bots = false, sort = "updated", dir = 0 } = {}, kind = "issues") {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    const col = columnsFor(kind).find((c) => c.id === sort) || COLUMNS.find((c) => c.id === "updated");
    const d = dir || col.dir;
    return rows
      .filter((r) => bots || !r.bot)
      .filter((r) => !repo || r.repo.toLowerCase() === repo.toLowerCase())
      .filter((r) => !review || reviewOf(r) === review)
      .filter((r) => words.every((w) => searchText(r).includes(w)))
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
      q: params.get("q") || "",
      repo: params.get("repo") || "",
      review: kind === "prs" ? params.get("review") || "" : "",
      bots: params.get("bots") === "1",
      sort: params.get("sort") || "updated",
      dir: Number(params.get("dir")) || 0,
    };
    let limit = PAGE;

    document.title = `${KINDS[kind]} · OWASP Project Matrix`;
    $("heading").textContent = KINDS[kind];
    $(`tab-${kind}`).setAttribute("aria-current", "page");
    $("review-field").hidden = kind !== "prs";
    $("q").value = state.q;
    $("review").value = state.review;
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

    // Project filter: one option per repository, named after its project.
    const repos = new Map();
    for (const r of rows) {
      const k = r.repo.toLowerCase();
      if (!repos.has(k)) repos.set(k, { repo: r.repo, name: projectName(r), n: 0 });
      if (!r.bot) repos.get(k).n += 1;
    }
    $("project").insertAdjacentHTML("beforeend", [...repos.values()]
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((p) => `<option value="${escapeHtml(p.repo)}">${escapeHtml(p.name === p.repo ? p.repo : `${p.name} · ${p.repo}`)} (${fmt(p.n)})</option>`).join(""));
    if (state.repo && !repos.has(state.repo.toLowerCase())) {
      $("project").insertAdjacentHTML("beforeend", `<option value="${escapeHtml(state.repo)}">${escapeHtml(state.repo)} (0)</option>`);
    }
    $("project").value = [...$("project").options].find((o) => o.value.toLowerCase() === state.repo.toLowerCase())?.value || "";

    function render() {
      const shown = filterRows(rows, state, kind);
      const base = rows.filter((r) => state.bots || !r.bot);
      $(`n-${kind}`).textContent = fmt(rows.filter((r) => !r.bot).length);
      $("totals").innerHTML = totalsHtml(shown);
      $("thead").innerHTML = headHtml(kind, state.sort, state.dir);
      $("tbody").innerHTML = shown.slice(0, limit).map((r) => rowHtml(r, kind)).join("")
        || `<tr><td class="empty" colspan="${columnsFor(kind).length}">Nothing matches these filters.</td></tr>`;
      const noun = kind === "prs" ? "pull request" : "issue";
      $("count").textContent = shown.length === base.length
        ? `${fmt(shown.length)} open ${noun}${shown.length === 1 ? "" : "s"}`
        : `${fmt(shown.length)} of ${fmt(base.length)} open ${noun}s`;
      const left = shown.length - limit;
      $("more").hidden = left <= 0;
      $("more").textContent = `Show ${fmt(Math.min(left, PAGE))} more (${fmt(left)} left)`;

      const next = new URLSearchParams({ kind });
      for (const [k, v] of Object.entries(state)) {
        if (v && !(k === "sort" && v === "updated")) next.set(k, v === true ? "1" : String(v));
      }
      history.replaceState(null, "", `?${next}`);
    }

    $("q").addEventListener("input", () => { state.q = $("q").value; limit = PAGE; render(); });
    $("project").addEventListener("change", () => { state.repo = $("project").value; limit = PAGE; render(); });
    $("review").addEventListener("change", () => { state.review = $("review").value; limit = PAGE; render(); });
    $("bots").addEventListener("change", () => { state.bots = $("bots").checked; limit = PAGE; render(); });
    $("more").addEventListener("click", () => { limit += PAGE; render(); });
    $("thead").addEventListener("click", (e) => {
      const button = e.target.closest("button[data-sort]");
      if (!button) return;
      const col = COLUMNS.find((c) => c.id === button.dataset.sort);
      state.dir = state.sort === col.id ? -(state.dir || col.dir) : col.dir;
      state.sort = col.id;
      if (state.dir === col.dir) state.dir = 0;
      render();
      $("thead").querySelector(`[data-sort="${col.id}"]`).focus();
    });
    render();
  }

  Object.assign(root, { filterRows, rowHtml, headHtml, labelHtml, avatarUrl, columnsFor });
  if (typeof document !== "undefined" && document.getElementById("tbody")) main();
})(typeof globalThis !== "undefined" ? globalThis : this);
