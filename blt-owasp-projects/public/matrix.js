// The project matrix (index.html): one card per OWASP project from repo_status.json, with search,
// filters and sorting. Every value from the data is escaped (escapeHtml / safeHref from
// safe-html.js): it comes from OWASP project metadata and the GitHub API.
(function (root) {
  const LEVELS = { "4": "flagship", "3.5": "production", "3": "lab", "2": "incubator" };
  const LEVEL_NAMES = { flagship: "Flagship", production: "Production", lab: "Lab", incubator: "Incubator", other: "Other" };
  const DAY = 86400000;

  // owasp.org's inventory gives a name ("flagship"); projects.json gave a number ("3.5").
  function levelOf(project) {
    const level = String(project.level ?? "").toLowerCase();
    return LEVEL_NAMES[level] ? level : LEVELS[level] || "other";
  }

  // Types are free text ("Tool", "code, documentation", "Standards", ""); the first match wins.
  function typeOf(project) {
    const t = String(project.type || "").toLowerCase();
    if (t.includes("code") || t.includes("framework")) return "code";
    if (t.includes("tool") || t.includes("supply")) return "tool";
    if (t.includes("doc") || t.includes("standard") || t.includes("training")) return "documentation";
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

  // Every card has the same cover: a band in the colour of the repository's main language (GitHub's
  // own colours), a monogram, and GitHub's language bar. Without language data the level picks it.
  const LEVEL_COLORS = { flagship: "#dc2626", production: "#ea580c", lab: "#2563eb", incubator: "#7c3aed", other: "#64748b" };
  const hex = (c) => (/^#[0-9a-f]{6}$/i.test(String(c || "")) ? c : null);

  function languagesOf(p) {
    return (Array.isArray(p.languages) ? p.languages : [])
      .filter((l) => Array.isArray(l) && l[0] && num(l[2]) !== null && l[2] > 0)
      .map(([name, color, share]) => ({ name: String(name), color: hex(color) || "#94a3b8", share }));
  }

  function coverColor(p) {
    const [first] = languagesOf(p);
    return first ? first.color : LEVEL_COLORS[levelOf(p)];
  }

  // Dark or light text on a colour, by its luminance.
  function inkOn(color) {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(color.slice(i, i + 2), 16));
    return 0.299 * r + 0.587 * g + 0.114 * b > 160 ? "#111827" : "#ffffff";
  }

  // "OWASP Juice Shop" -> "JS", "OWASP ZAP" -> "ZA".
  function monogram(p) {
    const words = String(p.title || p.name || "?").replace(/^owasp\s+/i, "").split(/[\s/_-]+/).filter((w) => /[a-z0-9]/i.test(w));
    const letters = words.length > 1 ? words[0][0] + words[1][0] : (words[0] || "?").slice(0, 2);
    return letters.toUpperCase();
  }

  function langBarHtml(p) {
    const langs = languagesOf(p);
    if (!langs.length) {
      return `<div class="langbar empty" role="img" aria-label="No language data"></div><p class="langs muted-langs">${
        p.github_status === "success" ? "No code languages detected" : "No repository data"}</p>`;
    }
    const pct = (share) => `${share >= 0.1 ? Math.round(share * 100) : (share * 100).toFixed(1)}%`;
    const label = langs.map((l) => `${l.name} ${pct(l.share)}`).join(", ");
    const bar = langs.map((l) => `<span style="flex-grow:${l.share};background:${l.color}" title="${escapeHtml(`${l.name} ${pct(l.share)}`)}"></span>`).join("");
    const legend = langs.slice(0, 3).map((l) => `<span><i style="background:${l.color}"></i>${escapeHtml(l.name)} <b>${pct(l.share)}</b></span>`).join("");
    return `<div class="langbar" role="img" aria-label="${escapeHtml(label)}">${bar}</div><p class="langs">${legend}</p>`;
  }

  // open.html lists one repository's open issues or pull requests.
  function openHref(kind, repo) {
    return `open.html?kind=${kind}${repo ? `&repo=${encodeURIComponent(repo)}` : ""}`;
  }

  function searchText(p) {
    return [p.name, p.title, p.pitch, p.repo_name, p.top_language, p.type,
      ...(p.top_contributors || []).map((c) => c.login)].join(" ").toLowerCase();
  }

  const newcomerCount = (p) => (p._work ? p._work.good_first + p._work.help_wanted : 0);

  const SORTS = {
    activity: (a, b) => (num(b.commits_90d) ?? -1) - (num(a.commits_90d) ?? -1),
    recent: (a, b) => (Date.parse(b.last_commit) || 0) - (Date.parse(a.last_commit) || 0),
    stars: (a, b) => (num(b.stars) ?? -1) - (num(a.stars) ?? -1),
    contributors: (a, b) => (num(b.committers) ?? -1) - (num(a.committers) ?? -1),
    issues: (a, b) => (num(b.issues) ?? -1) - (num(a.issues) ?? -1),
    newcomers: (a, b) => newcomerCount(b) - newcomerCount(a),
    name: () => 0,
  };

  function filterProjects(projects, { q = "", level = "", type = "", listed = "", active = false, sort = "activity" } = {}, now = Date.now()) {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    const byName = (a, b) => String(a.title || a.name).localeCompare(String(b.title || b.name));
    return projects
      .filter((p) => !level || levelOf(p) === level)
      .filter((p) => !type || typeOf(p) === type)
      .filter((p) => !listed || (listed === "owasp") === (p.listed !== false))
      .filter((p) => !active || ["active", "recent"].includes(pulse(p, now)))
      .filter((p) => words.every((w) => searchText(p).includes(w)))
      .sort((a, b) => (SORTS[sort] || SORTS.activity)(a, b) || byName(a, b));
  }

  // A stat block; with `href` (a local open.html link) the whole block links there.
  function stat(value, label, title, href) {
    const attrs = title ? ` title="${escapeHtml(title)}"` : "";
    const body = `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`;
    return href
      ? `<div class="stat link"${attrs}><a href="${escapeHtml(href)}">${body}</a></div>`
      : `<div class="stat"${attrs}>${body}</div>`;
  }

  function contributorsHtml(p) {
    const people = (p.top_contributors || []).slice(0, 3);
    if (!people.length) {
      return p.github_status === "success"
        ? `<section class="people"><h3>Top contributors</h3><p class="note">No contributors listed on GitHub yet.</p></section>`
        : "";
    }
    const rows = people.map((c) => {
      const img = avatar(c.avatar_url, 64);
      const pic = img
        ? `<img src="${escapeHtml(img)}" alt="" width="28" height="28" loading="lazy" decoding="async">`
        : `<span class="avatar-blank" aria-hidden="true">${escapeHtml(String(c.login || "?").slice(0, 1).toUpperCase())}</span>`;
      return `<li>${pic}${linkHtml(c.html_url, c.login)}<span class="commits">${plural(c.contributions, "commit", "commits")}</span></li>`;
    }).join("");
    const more = num(p.committers) > people.length ? ` <span class="muted">· ${fmt(p.committers)} in all</span>` : "";
    return `<section class="people"><h3>Top contributors${more}</h3><ol>${rows}</ol></section>`;
  }

  function detailsHtml(p) {
    const rows = [
      ["Repository", linkHtml(p.codeurl, p.repo_name)],
      ["Website repository", p.www_repo && p.www_repo !== p.repo_name ? linkHtml(`https://github.com/${p.www_repo}`, p.www_repo) : ""],
      ["Website", linkHtml(p.website)],
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

  // Links into open.html's quick views for this repository, from open_summary.json.
  function contributeHtml(p, work) {
    if (!work || !p.repo_name) return "";
    const chip = (n, label, kind, view) => (n
      ? `<a class="chip chip-${view}" href="${escapeHtml(`${openHref(kind, p.repo_name)}&view=${view}`)}"><b>${fmt(n)}</b> ${label}</a>` : "");
    const chips = [
      chip(work.good_first, work.good_first === 1 ? "good first issue" : "good first issues", "issues", "good-first"),
      chip(work.help_wanted, "help wanted", "issues", "help-wanted"),
      chip(work.needs_review, work.needs_review === 1 ? "PR to review" : "PRs to review", "prs", "needs-review"),
    ].join("");
    return chips ? `<div class="contribute">${chips}</div>` : "";
  }

  function cardHtml(p, now = Date.now(), work = null) {
    const level = levelOf(p);
    const state = pulse(p, now);
    const ok = p.github_status === "success";
    const repo = safeHref(p.codeurl);
    const last = ago(p.last_commit, now);
    const capped = p.activity_capped ? "+" : "";
    const tags = [
      typeOf(p) !== "other" ? `<span class="tag">${escapeHtml(typeOf(p)[0].toUpperCase() + typeOf(p).slice(1))}</span>` : "",
      p.archived ? `<span class="tag archived">Archived</span>` : "",
      p.listed === false ? `<span class="tag unlisted" title="Has an active www-project repository but is not in the owasp.org project inventory">Not on owasp.org</span>` : "",
    ].join("");
    const color = coverColor(p);
    const stats = ok
      ? `<dl class="stats">
          ${stat(fmt(p.stars), "Stars")}
          ${stat(fmt(p.issues), "Open issues", "List this repository's open issues", openHref("issues", p.repo_name))}
          ${stat(fmt(p.prs), "Open PRs", "List this repository's open pull requests", openHref("prs", p.repo_name))}
          ${stat(`${fmt(p.commits_30d)}${p.commits_30d >= 300 ? capped : ""} / ${fmt(p.commits_90d)}${capped}`, "Commits 30/90d", "Commits in the last 30 and 90 days")}
          ${stat(`${fmt(p.contributors_30d)}${p.commits_30d >= 300 ? capped : ""} / ${fmt(p.contributors_90d)}${capped}`, "People 30/90d", "Distinct commit authors in the last 30 and 90 days, bots excluded")}
          ${stat(fmt(p.committers), "Contributors")}
        </dl>`
      : `<p class="note">${p.github_status === "no repository" ? "No GitHub repository listed for this project." : "GitHub stats unavailable for this repository."}</p>`;
    const links = [
      linkHtml(p.url, "Project page"),
      repo ? linkHtml(repo, "Code") : "",
      ok ? `<a href="${escapeHtml(openHref("issues", p.repo_name))}">Issues</a>` : "",
      ok ? `<a href="${escapeHtml(openHref("prs", p.repo_name))}">Pull requests</a>` : "",
    ].filter(Boolean).join("");
    return `<li class="card" style="--cover:${color};--cover-ink:${inkOn(color)}">
      <div class="cover" aria-hidden="true">
        <span class="mono">${escapeHtml(monogram(p))}</span>
        <span class="cover-meta">
          <span class="tag level level-${level}">${LEVEL_NAMES[level]}</span>
          <span class="pulse pulse-${state}" title="${escapeHtml(last ? `Last commit ${last}` : "No commit data")}">${escapeHtml(last || "no data")}</span>
        </span>
      </div>
      ${langBarHtml(p)}
      <header>
        <h2>${linkHtml(p.url, p.title || p.name)}</h2>
        ${tags ? `<div class="tags">${tags}</div>` : ""}
      </header>
      <p class="pitch">${escapeHtml(p.pitch || "No description on owasp.org yet.")}</p>
      ${stats}
      ${contributorsHtml(p)}
      ${contributeHtml(p, work)}
      <footer><nav class="links" aria-label="${escapeHtml(p.title || p.name)} links">${links}</nav>${detailsHtml(p)}</footer>
    </li>`;
  }

  // The home page's "Find something to work on" strip: totals of open_summary.json.
  function workTotals(rows) {
    const keys = ["issues", "prs", "good_first", "help_wanted", "needs_review", "quick", "first_time"];
    const t = Object.fromEntries(keys.map((k) => [k, 0]));
    for (const r of rows) for (const k of keys) t[k] += num(r[k]) || 0;
    return t;
  }

  function contributeStripHtml(t) {
    const tile = (n, label, sub, href, tone) => `<a class="work-tile ${tone}" href="${escapeHtml(href)}">
      <b>${fmt(n)}</b><span>${escapeHtml(label)}</span><small>${escapeHtml(sub)}</small></a>`;
    return `<h2>Find something to work on</h2><div class="work-tiles">
      ${tile(t.good_first, "Good first issues", "Labelled for newcomers", "open.html?kind=issues&view=good-first", "green")}
      ${tile(t.help_wanted, "Help wanted", "Maintainers asking for help", "open.html?kind=issues&view=help-wanted", "blue")}
      ${tile(t.needs_review, "PRs to review", "Waiting for a review", "open.html?kind=prs&view=needs-review", "amber")}
      ${tile(t.quick, "Quick reviews", "50 lines or fewer", "open.html?kind=prs&view=quick", "violet")}
      ${tile(t.first_time, "New contributors", "PRs from people new to the repo", "open.html?kind=prs&view=first-time", "rose")}
    </div>`;
  }

  // Sums count each repository once (several projects can share one) and are "–" when no project
  // has the field at all, rather than a misleading 0.
  function totalsHtml(projects) {
    const byRepo = new Map(projects.filter((p) => p.repo_name).map((p) => [String(p.repo_name).toLowerCase(), p]));
    const sum = (k) => {
      const values = [...byRepo.values()].map((p) => num(p[k])).filter((v) => v !== null);
      return values.length ? values.reduce((s, v) => s + v, 0) : null;
    };
    const active = projects.filter((p) => pulse(p) === "active").length;
    const unlisted = projects.filter((p) => p.listed === false).length;
    return [
      stat(fmt(projects.length), "Projects", unlisted
        ? `${fmt(projects.length - unlisted)} in the owasp.org inventory and ${fmt(unlisted)} active www-project repositories that are not`
        : ""),
      stat(fmt(active), "Committed to in 30 days"),
      stat(fmt(sum("commits_90d")), "Commits in 90 days"),
      stat(fmt(sum("issues")), "Open issues", "List every open issue", openHref("issues")),
      stat(fmt(sum("prs")), "Open pull requests", "List every open pull request", openHref("prs")),
    ].join("");
  }

  async function main() {
    const $ = (id) => document.getElementById(id);
    const controls = ["q", "level", "type", "listed", "sort", "active"].map($);
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

    // Contribution counts come separately (small, and the cards don't wait for them).
    let work = new Map();
    fetch("open_summary.json").then((r) => (r.ok ? r.json() : [])).then((rows) => {
      if (!Array.isArray(rows) || !rows.length) return;
      work = new Map(rows.map((w) => [String(w.repo).toLowerCase(), w]));
      for (const p of projects) p._work = work.get(String(p.repo_name || "").toLowerCase()) || null;
      $("contribute").innerHTML = contributeStripHtml(workTotals(rows));
      $("contribute").hidden = false;
      render();
    }).catch(() => {});

    function render() {
      const state = { q: $("q").value, level: $("level").value, type: $("type").value, listed: $("listed").value, sort: $("sort").value, active: $("active").checked };
      const shown = filterProjects(projects, state);
      $("grid").innerHTML = shown.map((p) => cardHtml(p, Date.now(), p._work)).join("");
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

  Object.assign(root, { levelOf, typeOf, ago, pulse, avatar, languagesOf, coverColor, monogram, langBarHtml, filterProjects, cardHtml, totalsHtml, workTotals, contributeStripHtml });
  if (typeof document !== "undefined" && document.getElementById("grid")) main();
})(typeof globalThis !== "undefined" ? globalThis : this);
