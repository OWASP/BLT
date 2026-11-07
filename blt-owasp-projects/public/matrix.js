// The project matrix (index.html): one card per OWASP project from repo_status.json, with search,
// filters and sorting. Every value from the data is escaped (escapeHtml / safeHref from
// safe-html.js): it comes from OWASP project metadata and the GitHub API.
(function (root) {
  const LEVELS = { "4": "flagship", "3.5": "production", "3": "lab", "2": "incubator" };
  const LEVEL_NAMES = { flagship: "Flagship", production: "Production", lab: "Lab", incubator: "Incubator", other: "Other" };
  const DAY = 86400000;

  function levelOf(project) {
    return LEVELS[String(project.level)] || "other";
  }

  // projects.json types are free text ("code, documentation", "Tool", ""); the first match wins.
  function typeOf(project) {
    const t = String(project.type || "").toLowerCase();
    if (t.includes("code")) return "code";
    if (t.includes("tool")) return "tool";
    if (t.includes("doc") || t.includes("standard")) return "documentation";
    return "other";
  }

  function ago(iso, now = Date.now()) {
    const t = Date.parse(iso);
    if (!iso || Number.isNaN(t)) return null;
    const days = Math.floor((now - t) / DAY);
    if (days < 1) return "today";
    if (days < 2) return "yesterday";
    if (days < 45) return `${days} days ago`;
    if (days < 365) return `${Math.round(days / 30)} months ago`;
    const years = Math.round(days / 365);
    return years === 1 ? "a year ago" : `${years} years ago`;
  }

  // Seen on GitHub: "active" (a commit in 30 days), "recent" (90 days), "quiet", or "unknown".
  function pulse(project, now = Date.now()) {
    const t = Date.parse(project.last_commit);
    if (Number.isNaN(t)) return "unknown";
    const days = (now - t) / DAY;
    return days <= 30 ? "active" : days <= 90 ? "recent" : "quiet";
  }

  const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
  const fmt = (v) => (num(v) === null ? "–" : num(v).toLocaleString("en-US"));
  const plural = (n, one, many) => `${fmt(n)} ${n === 1 ? one : many}`;

  // GitHub avatar URLs take a size; anything that isn't http(s) gets no image.
  function avatar(url, size) {
    const href = safeHref(url);
    if (!href) return null;
    const u = new URL(href);
    if (u.hostname.endsWith("githubusercontent.com")) u.searchParams.set("s", String(size));
    return u.href;
  }

  function searchText(p) {
    return [p.name, p.title, p.pitch, p.repo_name, p.top_language, p.type,
      ...(p.top_contributors || []).map((c) => c.login)].join(" ").toLowerCase();
  }

  const SORTS = {
    activity: (a, b) => (num(b.commits_90d) ?? -1) - (num(a.commits_90d) ?? -1),
    recent: (a, b) => (Date.parse(b.last_commit) || 0) - (Date.parse(a.last_commit) || 0),
    stars: (a, b) => (num(b.stars) ?? -1) - (num(a.stars) ?? -1),
    contributors: (a, b) => (num(b.committers) ?? -1) - (num(a.committers) ?? -1),
    issues: (a, b) => (num(b.issues) ?? -1) - (num(a.issues) ?? -1),
    name: () => 0,
  };

  function filterProjects(projects, { q = "", level = "", type = "", active = false, sort = "activity" } = {}, now = Date.now()) {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    const byName = (a, b) => String(a.title || a.name).localeCompare(String(b.title || b.name));
    return projects
      .filter((p) => !level || levelOf(p) === level)
      .filter((p) => !type || typeOf(p) === type)
      .filter((p) => !active || ["active", "recent"].includes(pulse(p, now)))
      .filter((p) => words.every((w) => searchText(p).includes(w)))
      .sort((a, b) => (SORTS[sort] || SORTS.activity)(a, b) || byName(a, b));
  }

  function stat(value, label, title) {
    return `<div class="stat"${title ? ` title="${escapeHtml(title)}"` : ""}><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`;
  }

  function contributorsHtml(p) {
    const people = p.top_contributors || [];
    if (!people.length) return "";
    const rows = people.map((c) => {
      const img = avatar(c.avatar_url, 64);
      const pic = img
        ? `<img src="${escapeHtml(img)}" alt="" width="28" height="28" loading="lazy" decoding="async">`
        : `<span class="avatar-blank" aria-hidden="true">${escapeHtml(String(c.login || "?").slice(0, 1).toUpperCase())}</span>`;
      return `<li>${pic}${linkHtml(c.html_url, c.login)}<span class="commits">${plural(c.contributions, "commit", "commits")}</span></li>`;
    }).join("");
    const more = num(p.committers) > people.length ? ` <span class="muted">of ${fmt(p.committers)}</span>` : "";
    return `<section class="people"><h3>Top contributors${more}</h3><ol>${rows}</ol></section>`;
  }

  function detailsHtml(p) {
    const rows = [
      ["Repository", linkHtml(p.codeurl, p.repo_name)],
      ["Language", escapeHtml(p.top_language)],
      ["License", escapeHtml(p.license)],
      ["Latest release", p.release_version ? `${escapeHtml(p.release_version)}${p.date_released ? ` (${escapeHtml(String(p.date_released).slice(0, 10))})` : ""}` : ""],
      ["Forks", escapeHtml(num(p.forks) === null ? "" : fmt(p.forks))],
      ["Project page created", escapeHtml(p.created)],
      ["Project page updated", escapeHtml(p.updated)],
      ["Page build", escapeHtml(p.build)],
      ["Region", escapeHtml(p.region)],
      ["Meetup group", escapeHtml(p["meetup-group"])],
      ["GitHub status", escapeHtml(p.github_status)],
    ].filter(([, v]) => v);
    return `<details><summary>Details</summary><dl class="facts">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl></details>`;
  }

  function cardHtml(p, now = Date.now()) {
    const level = levelOf(p);
    const state = pulse(p, now);
    const ok = p.github_status === "success";
    const repo = safeHref(p.codeurl);
    const last = ago(p.last_commit, now);
    const capped = p.activity_capped ? "+" : "";
    const tags = [
      `<span class="tag level-${level}">${LEVEL_NAMES[level]}</span>`,
      typeOf(p) !== "other" ? `<span class="tag">${escapeHtml(typeOf(p)[0].toUpperCase() + typeOf(p).slice(1))}</span>` : "",
      p.top_language ? `<span class="tag lang">${escapeHtml(p.top_language)}</span>` : "",
      p.archived ? `<span class="tag archived">Archived</span>` : "",
    ].join("");
    const stats = ok
      ? `<dl class="stats">
          ${stat(fmt(p.stars), "Stars")}
          ${stat(fmt(p.issues), "Open issues")}
          ${stat(fmt(p.prs), "Open PRs")}
          ${stat(`${fmt(p.commits_30d)}${p.commits_30d >= 300 ? capped : ""} / ${fmt(p.commits_90d)}${capped}`, "Commits 30/90d", "Commits in the last 30 and 90 days")}
          ${stat(`${fmt(p.contributors_30d)}${p.commits_30d >= 300 ? capped : ""} / ${fmt(p.contributors_90d)}${capped}`, "People 30/90d", "Distinct commit authors in the last 30 and 90 days, bots excluded")}
          ${stat(fmt(p.committers), "Contributors")}
        </dl>`
      : `<p class="note">GitHub stats unavailable for this repository.</p>`;
    const links = [
      linkHtml(p.url, "Project page"),
      repo ? linkHtml(repo, "Code") : "",
      repo && ok ? linkHtml(`${repo.replace(/\/$/, "")}/issues`, "Issues") : "",
      repo && ok ? linkHtml(`${repo.replace(/\/$/, "")}/pulls`, "Pull requests") : "",
    ].filter(Boolean).join("");
    return `<li class="card">
      <header>
        <div class="title-row">
          <h2>${linkHtml(p.url, p.title || p.name)}</h2>
          <span class="pulse pulse-${state}" title="${escapeHtml(last ? `Last commit ${last}` : "No commit data")}">${escapeHtml(last || "no data")}</span>
        </div>
        <div class="tags">${tags}</div>
      </header>
      ${p.pitch ? `<p class="pitch">${escapeHtml(p.pitch)}</p>` : ""}
      ${stats}
      ${contributorsHtml(p)}
      <footer><nav class="links" aria-label="${escapeHtml(p.title || p.name)} links">${links}</nav>${detailsHtml(p)}</footer>
    </li>`;
  }

  function totalsHtml(projects) {
    const sum = (k) => projects.reduce((s, p) => s + (num(p[k]) || 0), 0);
    const active = projects.filter((p) => pulse(p) === "active").length;
    return [
      stat(fmt(projects.length), "Projects"),
      stat(fmt(active), "Committed to in 30 days"),
      stat(fmt(sum("commits_90d")), "Commits in 90 days"),
      stat(fmt(sum("issues")), "Open issues"),
      stat(fmt(sum("prs")), "Open pull requests"),
    ].join("");
  }

  async function main() {
    const $ = (id) => document.getElementById(id);
    const controls = ["q", "level", "type", "sort", "active"].map($);
    const params = new URLSearchParams(location.search);
    for (const el of controls) {
      const v = params.get(el.id);
      if (v === null) continue;
      if (el.type === "checkbox") el.checked = v === "1"; else el.value = v;
    }

    let projects;
    try {
      const res = await fetch("repo_status.json");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      projects = await res.json();
      const at = res.headers.get("x-data-updated-at");
      if (at && !Number.isNaN(Date.parse(at))) $("updated").textContent = `Data refreshed ${ago(at)}.`;
    } catch (e) {
      console.error("Failed to load project status:", e);
      $("count").textContent = "Unable to load project status. Please try again later.";
      return;
    }
    if (!Array.isArray(projects) || projects.length === 0) {
      $("count").textContent = "No data yet.";
      return;
    }
    $("totals").innerHTML = totalsHtml(projects);

    function render() {
      const state = { q: $("q").value, level: $("level").value, type: $("type").value, sort: $("sort").value, active: $("active").checked };
      const shown = filterProjects(projects, state);
      $("grid").innerHTML = shown.map((p) => cardHtml(p)).join("");
      $("count").textContent = shown.length === projects.length
        ? `${plural(projects.length, "project", "projects")}`
        : `${fmt(shown.length)} of ${plural(projects.length, "project", "projects")}`;
      const next = new URLSearchParams();
      for (const el of controls) {
        const v = el.type === "checkbox" ? (el.checked ? "1" : "") : el.value;
        if (v && !(el.id === "sort" && v === "activity")) next.set(el.id, v);
      }
      history.replaceState(null, "", next.toString() ? `?${next}` : location.pathname);
    }
    for (const el of controls) el.addEventListener(el.tagName === "INPUT" && el.type !== "checkbox" ? "input" : "change", render);
    render();
  }

  Object.assign(root, { levelOf, typeOf, ago, pulse, avatar, filterProjects, cardHtml });
  if (typeof document !== "undefined" && document.getElementById("grid")) main();
})(typeof globalThis !== "undefined" ? globalThis : this);
