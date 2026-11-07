// Website repositories (projects.html): every OWASP www-project-* repository from
// www_project_repos.json, matched to its owasp.org project through repo_status.json, in one sortable
// table. Every value is escaped (escapeHtml / safeHref from safe-html.js): it comes from GitHub.
(function (root) {
  const DAY = 86400000;
  const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : 0);
  const fmt = (v) => num(v).toLocaleString("en-US");

  function ago(iso, now = Date.now()) {
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return "";
    const days = Math.floor((now - t) / DAY);
    if (days < 1) return "today";
    if (days < 45) return `${days}d ago`;
    if (days < 365) return `${Math.round(days / 30)}mo ago`;
    return `${(days / 365).toFixed(1).replace(/\.0$/, "")}y ago`;
  }

  // "listed" (in the owasp.org inventory), "unlisted" (open, not in it) or "archived".
  const STATUS = {
    listed: ["On owasp.org", "ok"],
    unlisted: ["Not listed", "wait"],
    archived: ["Archived", "muted-badge"],
  };

  function generateRows(repos, projects = []) {
    const byRepo = new Map();
    for (const p of projects) {
      if (p.www_repo) byRepo.set(String(p.www_repo).toLowerCase(), p);
      if (p.repo_name && !byRepo.has(String(p.repo_name).toLowerCase())) byRepo.set(String(p.repo_name).toLowerCase(), p);
    }
    return repos.map((r) => {
      const full = r.full_name || `OWASP/${r.name}`;
      const project = byRepo.get(String(full).toLowerCase()) || null;
      const status = r.archived ? "archived" : project && project.listed !== false ? "listed" : "unlisted";
      return {
        name: String(r.name || ""),
        full,
        url: safeHref(r.html_url) || `https://github.com/${full}`,
        description: r.description || "",
        project: project ? { title: project.title || project.name, url: safeHref(project.url) } : null,
        status,
        created: r.created_at || "",
        pushed: r.pushed_at || "",
        stars: num(r.stargazers_count),
        forks: num(r.forks_count),
        issues: num(r.open_issues_count),
      };
    });
  }

  const COLUMNS = [
    { id: "name", label: "Repository", key: (r) => r.name.toLowerCase(), dir: 1, cell: nameCell },
    { id: "project", label: "Project", key: (r) => (r.project ? r.project.title.toLowerCase() : "~"), dir: 1, cell: projectCell },
    { id: "status", label: "Status", key: (r) => ["listed", "unlisted", "archived"].indexOf(r.status), dir: 1, cell: statusCell },
    { id: "pushed", label: "Last push", key: (r) => Date.parse(r.pushed) || 0, dir: -1, cell: (r) => dateCell(r.pushed), num: true },
    { id: "created", label: "Created", key: (r) => Date.parse(r.created) || 0, dir: -1, cell: (r) => dateCell(r.created, false), num: true },
    { id: "stars", label: "Stars", key: (r) => r.stars, dir: -1, cell: (r) => fmt(r.stars), num: true },
    { id: "forks", label: "Forks", key: (r) => r.forks, dir: -1, cell: (r) => fmt(r.forks), num: true },
    { id: "issues", label: "Open issues", key: (r) => r.issues, dir: -1, cell: (r) => fmt(r.issues), num: true },
  ];

  function nameCell(r) {
    return `<a class="item-title" href="${escapeHtml(r.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.name.replace(/^www-project-/i, ""))}</a>
      <span class="item-meta"><span class="num">${escapeHtml(r.full)}</span></span>
      ${r.description ? `<span class="repo-desc">${escapeHtml(r.description)}</span>` : ""}`;
  }

  function projectCell(r) {
    if (!r.project) return `<span class="muted">–</span>`;
    return r.project.url
      ? `<a class="project-link" href="${escapeHtml(r.project.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.project.title)}</a>`
      : escapeHtml(r.project.title);
  }

  function statusCell(r) {
    const [label, tone] = STATUS[r.status];
    return `<span class="badge ${tone}">${escapeHtml(label)}</span>`;
  }

  // Last pushes over a year (amber) or three years (red) old stand out.
  function dateCell(iso, staleness = true) {
    const days = (Date.now() - (Date.parse(iso) || 0)) / DAY;
    const tone = !staleness ? "" : days > 3 * 365 ? " old" : days > 365 ? " stale" : "";
    return `<time class="when${tone}" datetime="${escapeHtml(iso)}" title="${escapeHtml(String(iso).slice(0, 10))}">${escapeHtml(ago(iso))}</time>`;
  }

  function filterRows(rows, { q = "", status = "", sort = "pushed", dir = 0 } = {}) {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    const col = COLUMNS.find((c) => c.id === sort) || COLUMNS[3];
    const d = dir || col.dir;
    return rows
      .filter((r) => !status || r.status === status)
      .filter((r) => words.every((w) => [r.name, r.description, r.project && r.project.title].join(" ").toLowerCase().includes(w)))
      .map((r) => [col.key(r), r])
      .sort(([a, ra], [b, rb]) => (a < b ? -d : a > b ? d : 0) || ra.name.localeCompare(rb.name))
      .map(([, r]) => r);
  }

  function headHtml(sort, dir) {
    return `<tr>${COLUMNS.map((c) => {
      const active = c.id === sort;
      const d = active ? dir || c.dir : 0;
      const aria = active ? ` aria-sort="${d > 0 ? "ascending" : "descending"}"` : "";
      return `<th scope="col" class="col-${c.id}${c.num ? " n" : ""}"${aria}><button type="button" data-sort="${c.id}">${escapeHtml(c.label)}<span class="arrow" aria-hidden="true">${active ? (d > 0 ? "↑" : "↓") : "↕"}</span></button></th>`;
    }).join("")}</tr>`;
  }

  const rowHtml = (r) => `<tr>${COLUMNS.map((c) => `<td class="col-${c.id}${c.num ? " n" : ""}" data-label="${escapeHtml(c.label)}">${c.cell(r)}</td>`).join("")}</tr>`;

  async function main() {
    const $ = (id) => document.getElementById(id);
    const params = new URLSearchParams(location.search);
    const state = { q: params.get("q") || "", status: params.get("status") || "", sort: params.get("sort") || "pushed", dir: Number(params.get("dir")) || 0 };
    $("q").value = state.q;
    $("status").value = state.status;

    let rows;
    try {
      const [repos, projects] = await Promise.all([
        fetch("www_project_repos.json").then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch("repo_status.json").then((r) => (r.ok ? r.json() : [])).catch(() => []),
      ]);
      rows = generateRows(Array.isArray(repos) ? repos : [], Array.isArray(projects) ? projects : []);
    } catch (e) {
      console.error("Failed to load repositories:", e);
      $("count").textContent = "Unable to load the repositories. Please try again later.";
      return;
    }
    if (!rows.length) {
      $("count").textContent = "No data yet.";
      return;
    }
    const counts = { "": rows.length, listed: 0, unlisted: 0, archived: 0 };
    for (const r of rows) counts[r.status] += 1;
    for (const o of $("status").options) o.textContent = `${o.dataset.label} (${fmt(counts[o.value])})`;

    function render() {
      const shown = filterRows(rows, state);
      $("thead").innerHTML = headHtml(state.sort, state.dir);
      $("tbody").innerHTML = shown.map(rowHtml).join("") || `<tr><td class="empty" colspan="${COLUMNS.length}">Nothing matches.</td></tr>`;
      $("count").textContent = shown.length === rows.length ? `${fmt(rows.length)} repositories` : `${fmt(shown.length)} of ${fmt(rows.length)} repositories`;
      const next = new URLSearchParams();
      for (const [k, v] of Object.entries(state)) if (v && !(k === "sort" && v === "pushed")) next.set(k, String(v));
      history.replaceState(null, "", next.toString() ? `?${next}` : location.pathname);
    }
    $("q").addEventListener("input", () => { state.q = $("q").value; render(); });
    $("status").addEventListener("change", () => { state.status = $("status").value; render(); });
    $("thead").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-sort]");
      if (!b) return;
      const col = COLUMNS.find((c) => c.id === b.dataset.sort);
      state.dir = state.sort === col.id ? -(state.dir || col.dir) : col.dir;
      state.sort = col.id;
      if (state.dir === col.dir) state.dir = 0;
      render();
      $("thead").querySelector(`[data-sort="${col.id}"]`).focus();
    });
    render();
  }

  Object.assign(root, { generateRows, filterRows, rowHtml });
  if (typeof document !== "undefined" && document.getElementById("repo-table")) main();
})(typeof globalThis !== "undefined" ? globalThis : this);
