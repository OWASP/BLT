/**
 * OWASP BLT – Application JavaScript
 * Pure vanilla JS, no framework dependencies.
 * License: AGPLv3
 */

/* ────────────────────────────────────────────────────────────
   Bootstrap
──────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initDarkMode();
  initMobileMenu();
  initAnonymousToggle();
  loadLeaderboard();
  loadRecentBugs();
  initSmoothScroll();
  bltCapture("page_viewed", { page: "homepage" });
  initLeaderboardFilters();
});

const FORGE_URL = BLT_CONFIG.FORGE_URL || "https://git.owaspblt.org/BLT";
const FORGE_ORIGIN = new URL(FORGE_URL).origin;
const PROJECT_URL = BLT_CONFIG.PROJECT_URL || `${FORGE_URL}/tree/main/blt-pages`;
const ISSUES_URL = BLT_CONFIG.ISSUES_URL || `${FORGE_URL}/issues?label=blt-pages`;
const NEW_BUG_URL = BLT_CONFIG.NEW_ISSUE_URL || `${FORGE_URL}/issues/new`;

/* ────────────────────────────────────────────────────────────
   Dark Mode
──────────────────────────────────────────────────────────── */
function initDarkMode() {
  // The theme toggle lives in the shared <blt-nav> bar (owaspblt.org/_shared/blt-nav.js), which sets
  // html.dark and localStorage "theme"; the pre-paint script in <head> applies the saved choice.
  window.addEventListener("blt-theme-change", (e) => {
    bltCapture("dark_mode_toggled", { to_dark: !!(e.detail && e.detail.dark), page: "homepage" });
  });
}

/* ────────────────────────────────────────────────────────────
   Mobile Menu
──────────────────────────────────────────────────────────── */
function initMobileMenu() {
  const toggle = document.getElementById("mobile-menu-toggle");
  const menu = document.getElementById("mobile-menu");
  if (!toggle || !menu) return;

  const desktopBreakpoint = window.matchMedia("(min-width: 1024px)");
  const syncMenuState = () => {
    if (desktopBreakpoint.matches) {
      menu.classList.add("hidden");
      toggle.setAttribute("aria-expanded", "false");
    }
  };

  toggle.addEventListener("click", () => {
    const open = menu.classList.toggle("hidden");
    toggle.setAttribute("aria-expanded", String(!open));
  });

  if (typeof desktopBreakpoint.addEventListener === "function") {
    desktopBreakpoint.addEventListener("change", syncMenuState);
  } else {
    desktopBreakpoint.addListener(syncMenuState);
  }

  // Close when a nav link is clicked
  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menu.classList.add("hidden");
      toggle.setAttribute("aria-expanded", "false");
    });
  });

  syncMenuState();
}

/* ────────────────────────────────────────────────────────────
   Anonymous Toggle (index page)
──────────────────────────────────────────────────────────── */
function initAnonymousToggle() {
  const checkbox = document.getElementById("anonymous-toggle");
  const btn = document.getElementById("report-bug-btn");
  if (!checkbox || !btn) return;

  checkbox.addEventListener("change", () => {
    if (checkbox.checked) {
      btn.href = "https://next.owaspblt.org/pages/report-bug";
      btn.querySelector(".btn-label").textContent = "Report Bug Anonymously";
    } else {
      btn.href = "https://git.owaspblt.org/BLT/issues/new";
      btn.querySelector(".btn-label").textContent = "Report a Bug";
    }
    bltCapture("anonymous_reporting_toggled", { enabled: checkbox.checked });
  });

  btn.addEventListener("click", () => {
    bltCapture("report_bug_clicked", { anonymous: checkbox.checked });
  });
}

/* ────────────────────────────────────────────────────────────
   Leaderboard
──────────────────────────────────────────────────────────── */
function updateHeaderBugStats(total, open, closed) {
  const statOpen = document.getElementById("stat-open-bugs");
  const statClosed = document.getElementById("stat-closed-bugs");
  if (statOpen) statOpen.textContent = formatNumber(open != null ? open : 0);
  if (statClosed) statClosed.textContent = formatNumber(closed != null ? closed : 0);
}

async function loadLeaderboard() {
  const container = document.getElementById("leaderboard-rows");
  const statBugs = document.getElementById("stat-total-bugs");
  const statDomains = document.getElementById("stat-domains");
  const statReporters = document.getElementById("stat-reporters");

  if (!container) return;
   // ── FAILSAFE (ensures CI/test always gets at least 1 row) ──
let resolved = false;

const FAILSAFE_TIMEOUT = 5000;

const failSafe = setTimeout(() => {
  if (resolved) return;

  const errorRow = (cols) => `
  <tr>
    <td colspan="${cols}" class="text-center py-8 text-gray-500 dark:text-gray-400">
      Could not load data.
    </td>
  </tr>`;

  if (container && container.childElementCount === 0) {
    container.innerHTML = errorRow(4);
  }

  const commentersEl = document.getElementById("commenters-rows");
  if (commentersEl && commentersEl.childElementCount === 0) {
    commentersEl.innerHTML = errorRow(4);
  }

  const domainsEl = document.getElementById("domains-rows");
  if (domainsEl && domainsEl.childElementCount === 0) {
    domainsEl.innerHTML = errorRow(4);
  }

}, FAILSAFE_TIMEOUT);

  const isHomepage = !!document.getElementById("homepage-leaderboard-limit");
  const limit = isHomepage ? 5 : 0;   // 0 = no limit

  // Skip re-render when content has already been server-side rendered into the HTML,
  // but still update the relative timestamps from the embedded inline data.
  if (container.dataset.preRendered === "true") {
    const inlineData = getLeaderboardData();
    if (inlineData) {
      updateTimestamps(inlineData);
      updateHeaderBugStats(inlineData.total_bugs, inlineData.open_bugs, inlineData.closed_bugs);
      if (isHomepage) {
        renderLeaderboard(container, inlineData, limit);
        renderTopCommenters(document.getElementById("commenters-rows"), inlineData, limit);
        renderTopDomains(document.getElementById("domains-rows"), inlineData, limit);
      }
    }
    bltCapture("leaderboard_loaded", { source: "pre_rendered", entries: container.childElementCount });
     resolved = true;
     clearTimeout(failSafe);
    return;
  }

  try {
    // Use the inline data embedded by the generator if available
    const inlineData = getLeaderboardData();
    if (inlineData && inlineData.leaderboard) {
      currentLeaderboardData = inlineData;
      renderLeaderboard(container, inlineData, limit);
      renderTopCommenters(document.getElementById("commenters-rows"), inlineData, isHomepage ? 5 : 0);
      renderTopDomains(document.getElementById("domains-rows"), inlineData, isHomepage ? 5 : 0);
      if (statBugs) statBugs.textContent = formatNumber(inlineData.total_bugs || 0);
      if (statReporters) statReporters.textContent = formatNumber(inlineData.leaderboard.length || 0);
      if (statDomains) statDomains.textContent = inlineData.total_domains != null ? formatNumber(inlineData.total_domains) : "-";
      updateHeaderBugStats(inlineData.total_bugs, inlineData.open_bugs, inlineData.closed_bugs);
      bltCapture("leaderboard_loaded", { source: "inline_data", entries: inlineData.leaderboard.length });
       resolved = true;
       clearTimeout(failSafe);
      return;
    }
    // data/leaderboard.json, served from KV (refreshed by .forkmesh/blt-pages--update-leaderboard.yml)
    const res = await fetch("data/leaderboard.json");
    if (!res.ok) throw new Error("No static data");
    const data = await res.json();
    currentLeaderboardData = data;
    renderLeaderboard(container, data, limit);
    renderTopCommenters(document.getElementById("commenters-rows"), data, isHomepage ? 5 : 0);
    renderTopDomains(document.getElementById("domains-rows"), data, isHomepage ? 5 : 0);
    if (statBugs) statBugs.textContent = formatNumber(data.total_bugs || 0);
    if (statReporters) statReporters.textContent = formatNumber(data.leaderboard?.length || 0);
    if (statDomains) statDomains.textContent = data.total_domains != null ? formatNumber(data.total_domains) : "-";
    updateHeaderBugStats(data.total_bugs, data.open_bugs, data.closed_bugs);
    bltCapture("leaderboard_loaded", { source: "static_json", entries: data.leaderboard?.length || 0 });
     resolved = true;
     clearTimeout(failSafe);
  } catch (err2) {
  resolved = true;
  clearTimeout(failSafe);
  console.error("Leaderboard data failed to load:", { context: "loadLeaderboard", error: err2 });

  const errorRow = (cols) => `
  <tr>
    <td colspan="${cols}" class="text-center py-8 text-gray-500 dark:text-gray-400">
      <svg class="fa-icon text-primary mr-2" aria-hidden="true">
        <use href="#fa-circle-exclamation"></use>
      </svg>
      Could not load data.
      <a href="${ISSUES_URL}"
         class="text-primary underline" target="_blank" rel="noopener noreferrer">
         View Source
      </a>
    </td>
  </tr>`;

  // Main table
  container.innerHTML = errorRow(4);

  // Other tables for commenters and domains
  const commentersEl = document.getElementById("commenters-rows");
  if (commentersEl) commentersEl.innerHTML = errorRow(4);

  const domainsEl = document.getElementById("domains-rows");
  if (domainsEl) domainsEl.innerHTML = errorRow(4);
 }
}
/**
 * Centralized data access helper for leaderboard information.
 * Returns either the server-side rendered (SSR) inline data or the latest fetched state.
 */
function getLeaderboardData() {
  return window.__BLT_LEADERBOARD__ || currentLeaderboardData;
}

let currentLeaderboardData = null;


function renderLeaderboard(container, data, limit = 0, filter = "") {
  if (!container || !data) return;
  const query = filter.trim().toLowerCase();
  let leaderboard = data.leaderboard || [];

  if (query) {
    leaderboard = leaderboard.filter((e) => e.login.toLowerCase().includes(query));
  }

  if (limit > 0) {
    leaderboard = leaderboard.slice(0, limit);
  }

  if (!data.leaderboard || data.leaderboard.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      <svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true"><use href="#fa-trophy"></use></svg>
      No reports yet. Be the first to <a href="https://git.owaspblt.org/BLT/issues/new" class="text-primary underline hover:no-underline">report a bug</a>!
    </td></tr>`;
    return;
  }

  if (leaderboard.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      No collaborators matched "${escapeHtml(filter)}".
    </td></tr>`;
    return;
  }

  const rankIcons = ["🥇", "🥈", "🥉"];
  const maxCount = leaderboard[0]?.count || 1;

  container.innerHTML = leaderboard
    .map((entry) => {
      const rankDisplay =
        entry.rank <= 3
          ? `<span class="text-xl" aria-label="Rank ${entry.rank}">${rankIcons[entry.rank - 1]}</span>`
          : `<span class="font-bold text-gray-500 dark:text-gray-400">#${entry.rank}</span>`;

      const rowClass =
        entry.rank <= 3
          ? "bg-active-bg dark:bg-red-900/10"
          : "hover:bg-gray-50 dark:hover:bg-gray-800/50";

      const activityPct = Math.min(100, (entry.count / maxCount) * 100);
      const isCompact = limit > 0;

      return `<tr class="${rowClass} transition-colors">
        <td class="px-3 py-2 text-center w-10">${rankDisplay}</td>
        <td class="px-3 py-2">
          <a href="${entry.profile_url || `${FORGE_ORIGIN}/@${entry.login}`}"
             target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-2 group min-w-0">
            <img src="${entry.avatar_url || `${FORGE_ORIGIN}/api/accounts/${String(entry.login).toLowerCase()}/avatar`}"
                 alt="${escapeHtml(entry.login)}'s avatar"
                 class="w-6 h-6 rounded-full border border-neutral-border dark:border-gray-700 flex-shrink-0"
                 loading="lazy"
                 onerror="this.style.visibility='hidden'" />
            <span class="font-medium text-gray-900 dark:text-white group-hover:text-primary transition-colors truncate min-w-0 flex-1 text-sm">
              ${escapeHtml(entry.login)}
            </span>
          </a>
          ${isCompact ? '' : `
          <div class="flex sm:hidden items-center gap-2 mt-1 pl-8">
            <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white text-xs">
              <svg class="fa-icon text-primary text-xs" aria-hidden="true"><use href="#fa-bug"></use></svg>
              ${formatNumber(entry.count)}
            </span>
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-1 flex-1 overflow-hidden">
              <div class="bg-primary h-1 rounded-full" style="width:${activityPct}%"></div>
            </div>
          </div>`}
        </td>
        ${isCompact ? `
        <td class="px-3 py-2 text-right">
          <span class="font-bold text-gray-900 dark:text-white text-sm">${formatNumber(entry.count)}</span>
        </td>` : `
        <td class="hidden px-4 py-3 text-right sm:table-cell">
          <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">
            <svg class="fa-icon text-primary text-xs" aria-hidden="true"><use href="#fa-bug"></use></svg>
            ${formatNumber(entry.count)}
          </span>
        </td>
        <td class="px-4 py-3 hidden sm:table-cell" title="Impact Score: Based on total contributions">
          <div class="flex justify-end">
            <div class="flex gap-0.5 items-end h-4 w-24">
              ${renderActivitySparkline(entry.count, maxCount, 12)}
            </div>
          </div>
        </td>`}
      </tr>`;
    })
    .join("");

  // Update timestamps if present
  updateTimestamps(data);
}

function updateTimestamps(data) {
  const ts = document.getElementById("leaderboard-updated");
  if (ts && data.updated_at) {
    ts.textContent = `Updated ${new Date(data.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;
  }
  const homepageTs = document.getElementById("homepage-updated");
  if (homepageTs && data.updated_at) {
    const ago = timeAgo(data.updated_at);
    const sha = typeof data.commit_sha === "string" && /^[0-9a-f]{7,40}$/i.test(data.commit_sha)
      ? data.commit_sha
      : null;
    if (sha) {
      const commitUrl = `${FORGE_URL}/commit/${sha}`;
      const shortSha = escapeHtml(sha.slice(0, 7));
      homepageTs.innerHTML = `Last updated: ${escapeHtml(ago)} &mdash; <a href="${escapeHtml(commitUrl)}" target="_blank" rel="noopener noreferrer" class="hover:underline">${shortSha}</a>`;
    } else {
      homepageTs.textContent = `Last updated: ${ago}`;
    }
  }
}

/* ────────────────────────────────────────────────────────────
   Recent Bug Reports
──────────────────────────────────────────────────────────── */
async function loadRecentBugs() {
  const grid = document.getElementById("recent-bugs-grid");
  if (!grid) return;

  // Skip re-render when content has already been server-side rendered into the HTML
  if (grid.dataset.preRendered === "true") return;

  // Not pre-rendered: use the inline data, else data/leaderboard.json (served from KV).
  const inlineData = getLeaderboardData();
  if (inlineData && Array.isArray(inlineData.recent_bugs)) {
    renderRecentBugs(inlineData.recent_bugs);
    bltCapture("recent_bugs_loaded", { source: "inline_data", count: inlineData.recent_bugs.length });
    return;
  }
  try {
    const res = await fetch("data/leaderboard.json");
    if (!res.ok) throw new Error("No static data");
    const data = await res.json();
    renderRecentBugs(data.recent_bugs || []);
    bltCapture("recent_bugs_loaded", { source: "static_json", count: (data.recent_bugs || []).length });
  } catch {
    renderRecentBugs([]);
  }
}

function renderRecentBugs(bugs) {
  const grid = document.getElementById("recent-bugs-grid");
  if (!grid) return;

  if (!bugs || bugs.length === 0) {
    grid.innerHTML = `<div class="col-span-3 text-center py-12 text-gray-400 dark:text-gray-500">
      <svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true"><use href="#fa-bug"></use></svg>
      No bug reports yet. <a href="https://git.owaspblt.org/BLT/issues/new" class="text-primary hover:underline">Be the first to report!</a>
    </div>`;
    return;
  }

  grid.innerHTML = bugs
    .map((bug) => {
      const imgHtml = bug.image_url
        ? `<div class="aspect-video bg-gray-100 dark:bg-gray-800 rounded-xl mb-4 overflow-hidden flex-shrink-0">
             <img src="${escapeHtml(bug.image_url)}"
                  alt="Bug screenshot"
                  class="w-full h-full object-cover"
                  loading="lazy"
                  onerror="this.parentElement.classList.add('hidden')" />
           </div>`
        : `<div class="aspect-video bg-gray-100 dark:bg-gray-800 rounded-xl mb-4 flex items-center justify-center flex-shrink-0">
             <svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600" aria-hidden="true"><use href="#fa-bug"></use></svg>
           </div>`;

      const date = new Date(bug.created_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });

      const avatarUrl = escapeHtml(
        bug.user.avatar_url || `${FORGE_ORIGIN}/api/accounts/${String(bug.user.login).toLowerCase()}/avatar`
      );
      const profileUrl = escapeHtml(
        bug.user.profile_url || `${FORGE_ORIGIN}/@${bug.user.login}`
      );
      const login = escapeHtml(bug.user.login);

      const reactionsHtml = bug.reactions
        ? formatReactions(bug.reactions)
        : "";

      const faviconHtml = bug.domain
        ? `<img src="https://www.google.com/s2/favicons?domain=${encodeURIComponent(bug.domain)}&sz=32"
                alt="${escapeHtml(bug.domain)} favicon"
                class="w-4 h-4 rounded flex-shrink-0 inline-block align-middle mr-1"
                loading="lazy"
                referrerpolicy="no-referrer"
                onerror="this.outerHTML='<svg class=\'fa-icon text-gray-400 w-4 h-4\' aria-hidden=\'true\'><use href=\'#fa-globe\'></use></svg>'" />`
        : "";

      // Comment section
      let commentHtml = "";
      const commentCount = bug.comment_count;
      if (typeof commentCount === "number" && commentCount > 0 && bug.latest_comment) {
        const commenter = bug.latest_comment.user;
        const commenterAvatar = escapeHtml(commenter.avatar_url || `${FORGE_ORIGIN}/api/accounts/${String(commenter.login).toLowerCase()}/avatar`);
        const commenterProfile = escapeHtml(commenter.profile_url || `${FORGE_ORIGIN}/@${commenter.login}`);
        const commenterLogin = escapeHtml(commenter.login);
        const commentBody = escapeHtml((bug.latest_comment.body || "").replace(/\s+/g, " ").trim());
        const commentCountLabel = commentCount === 1 ? "1 comment" : `${formatNumber(commentCount)} comments`;
        commentHtml = `<div class="mt-3 pt-3 border-t border-neutral-border dark:border-gray-700">
          <div class="flex items-start gap-2">
            <a href="${commenterProfile}" target="_blank" rel="noopener noreferrer" class="flex-shrink-0">
              <img src="${commenterAvatar}"
                   alt="${commenterLogin}'s avatar"
                   class="w-6 h-6 rounded-full border border-neutral-border dark:border-gray-700"
                   loading="lazy"
                   onerror="this.style.visibility='hidden'" />
            </a>
            <div class="min-w-0 flex-1">
              <p class="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">${commentBody}</p>
              <a href="${escapeHtml(bug.html_url)}" target="_blank" rel="noopener noreferrer"
                 class="inline-flex items-center gap-1 mt-1 text-xs text-gray-400 hover:text-primary transition-colors">
                <svg class="fa-icon text-xs" aria-hidden="true"><use href="#fa-comment"></use></svg>
                ${commentCountLabel}
              </a>
            </div>
          </div>
        </div>`;
      } else if (typeof commentCount === "number" && commentCount === 0) {
        commentHtml = `<div class="mt-3 pt-3 border-t border-neutral-border dark:border-gray-700">
          <a href="${escapeHtml(bug.html_url)}" target="_blank" rel="noopener noreferrer"
             class="inline-flex items-center gap-1 text-xs text-primary hover:underline">
            <svg class="fa-icon text-xs" aria-hidden="true"><use href="#fa-comment"></use></svg>
            Be the first to comment
          </a>
        </div>`;
      }

      return `<div class="bg-white dark:bg-dark-base border border-neutral-border dark:border-gray-700 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col">
        ${imgHtml}
        <h3 class="font-semibold text-gray-900 dark:text-white mb-3 line-clamp-2 flex-1">
          <a href="${escapeHtml(bug.html_url)}" target="_blank" rel="noopener noreferrer"
             class="hover:text-primary transition-colors">
            ${faviconHtml}${escapeHtml(bug.title)}
          </a>
        </h3>
        <div class="flex items-center justify-between gap-3 mt-auto pt-3 border-t border-neutral-border dark:border-gray-700 flex-wrap">
          <div class="flex items-center gap-3">
            <a href="${profileUrl}" target="_blank" rel="noopener noreferrer"
               class="flex items-center gap-2 group">
              <img src="${avatarUrl}"
                   alt="${login}'s avatar"
                   class="w-7 h-7 rounded-full border border-neutral-border dark:border-gray-700"
                   loading="lazy"
                   onerror="this.style.visibility='hidden'" />
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-primary transition-colors">
                ${login}
              </span>
            </a>
            ${reactionsHtml}
          </div>
          <span class="text-xs text-gray-400 dark:text-gray-500">${date}</span>
        </div>
        ${commentHtml}
      </div>`;
    })
    .join("");
}

/* ────────────────────────────────────────────────────────────
   Top Commenters
──────────────────────────────────────────────────────────── */
function renderTopCommenters(container, data, limit = 0, filter = "") {
  if (!container || !data) return;

  const query = filter.trim().toLowerCase();
  let commenters = data.top_commenters || [];

  if (query) {
    commenters = commenters.filter((e) => e.login.toLowerCase().includes(query));
  }

  if (limit > 0) {
    commenters = commenters.slice(0, limit);
  }

  if (!data.top_commenters || data.top_commenters.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      <svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true"><use href="#fa-comment"></use></svg>
      No comments yet. Start a conversation on a <a href="${ISSUES_URL}" class="text-primary underline hover:no-underline" target="_blank" rel="noopener noreferrer">bug report</a>!
    </td></tr>`;
    return;
  }

  if (commenters.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      No collaborators matched "${escapeHtml(filter)}".
    </td></tr>`;
    return;
  }

  const rankIcons = ["🥇", "🥈", "🥉"];
  const maxCount = commenters[0]?.count || 1;

  const isCompact = limit > 0;

  container.innerHTML = commenters
    .map((entry) => {
      const rankDisplay =
        entry.rank <= 3
          ? `<span class="text-xl" aria-label="Rank ${entry.rank}">${rankIcons[entry.rank - 1]}</span>`
          : `<span class="font-bold text-gray-500 dark:text-gray-400">#${entry.rank}</span>`;

      const rowClass =
        entry.rank <= 3
          ? "bg-active-bg dark:bg-red-900/10"
          : "hover:bg-gray-50 dark:hover:bg-gray-800/50";

      const activityPct = Math.min(100, (entry.count / maxCount) * 100);

      return `<tr class="${rowClass} transition-colors">
        <td class="px-3 py-2 text-center w-10">${rankDisplay}</td>
        <td class="px-3 py-2">
          <a href="${entry.profile_url || `${FORGE_ORIGIN}/@${entry.login}`}"
             target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-2 group min-w-0">
            <img src="${entry.avatar_url || `${FORGE_ORIGIN}/api/accounts/${String(entry.login).toLowerCase()}/avatar`}"
                 alt="${escapeHtml(entry.login)}'s avatar"
                 class="w-6 h-6 rounded-full border border-neutral-border dark:border-gray-700 flex-shrink-0"
                 loading="lazy"
                 onerror="this.style.visibility='hidden'" />
            <span class="font-medium text-gray-900 dark:text-white group-hover:text-primary transition-colors truncate min-w-0 flex-1 text-sm">
              ${escapeHtml(entry.login)}
            </span>
          </a>
          ${isCompact ? '' : `
          <div class="flex sm:hidden items-center gap-2 mt-1 pl-8">
            <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white text-xs">
              <svg class="fa-icon text-primary text-xs" aria-hidden="true"><use href="#fa-comment"></use></svg>
              ${formatNumber(entry.count)}
            </span>
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-1 flex-1 overflow-hidden">
              <div class="bg-primary h-1 rounded-full" style="width:${activityPct}%"></div>
            </div>
          </div>`}
        </td>
        <td class="${isCompact ? 'px-3 py-2' : 'hidden px-4 py-3 sm:table-cell'} text-right">
          <span class="font-bold text-gray-900 dark:text-white ${isCompact ? 'text-sm' : ''}">
            ${isCompact ? '' : `<svg class="fa-icon text-primary text-xs mr-1" aria-hidden="true"><use href="#fa-comment"></use></svg>`}
            ${formatNumber(entry.count)}
          </span>
        </td>
        ${isCompact ? '' : `
        <td class="px-4 py-3 hidden sm:table-cell" title="Impact Score: Based on total contributions">
          <div class="flex justify-end">
            <div class="flex gap-0.5 items-end h-4 w-24">
              ${renderActivitySparkline(entry.count, maxCount, 12)}
            </div>
          </div>
        </td>`}
      </tr>`;
    })
    .join("");
}

/* ────────────────────────────────────────────────────────────
   Top Domains
──────────────────────────────────────────────────────────── */
function renderTopDomains(container, data, limit = 0, filter = "") {
  if (!container || !data) return;

  const query = filter.trim().toLowerCase();
  let domains = data.top_domains || [];

  if (query) {
    domains = domains.filter((e) => e.domain.toLowerCase().includes(query));
  }

  if (limit > 0) {
    domains = domains.slice(0, limit);
  }

  if (!data.top_domains || data.top_domains.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      <svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true"><use href="#fa-globe"></use></svg>
      No domain data yet. <a href="${NEW_BUG_URL}" class="text-primary underline hover:no-underline">Be the first to report a bug!</a>
    </td></tr>`;
    return;
  }

  if (domains.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      No domains matched "${escapeHtml(filter)}".
    </td></tr>`;
    return;
  }

  const rankIcons = ["🥇", "🥈", "🥉"];
  const maxCount = domains[0]?.count || 1;

  const isCompact = limit > 0;

  container.innerHTML = domains
    .map((entry) => {
      const rankDisplay =
        entry.rank <= 3
          ? `<span class="text-xl" aria-label="Rank ${entry.rank}">${rankIcons[entry.rank - 1]}</span>`
          : `<span class="font-bold text-gray-500 dark:text-gray-400">#${entry.rank}</span>`;

      const rowClass =
        entry.rank <= 3
          ? "bg-active-bg dark:bg-red-900/10"
          : "hover:bg-gray-50 dark:hover:bg-gray-800/50";

      const faviconUrl = `https://www.google.com/s2/favicons?domain=${encodeURIComponent(entry.domain)}&sz=32`;
      const activityPct = Math.min(100, (entry.count / maxCount) * 100);

      return `<tr class="${rowClass} transition-colors">
        <td class="px-3 py-2 text-center w-10">${rankDisplay}</td>
        <td class="px-3 py-2">
        <a href="${FORGE_URL}/issues?label=${encodeURIComponent(`domain: ${entry.domain}`)}"
             target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-2 group min-w-0">
            <img src="${faviconUrl}"
                 alt="${escapeHtml(entry.domain)} favicon"
                 class="w-5 h-5 rounded flex-shrink-0"
                 loading="lazy"
                 onerror="this.outerHTML='<svg class=\'fa-icon text-gray-400 w-5 h-5 flex-shrink-0\' aria-hidden=\'true\'><use href=\'#fa-globe\'></use></svg>'" />
            <span class="font-medium text-gray-900 dark:text-white group-hover:text-primary transition-colors truncate min-w-0 flex-1 text-sm">
              ${escapeHtml(entry.domain)}
            </span>
          </a>
        </td>
        <td class="px-3 py-2 text-right">
          <span class="font-bold text-gray-900 dark:text-white text-sm">${formatNumber(entry.count)}</span>
        </td>
        ${isCompact ? '' : `
        <td class="px-4 py-3 hidden sm:table-cell" title="Impact Score: Based on total contributions">
          <div class="flex justify-end">
            <div class="flex gap-0.5 items-end h-4 w-24">
              ${renderActivitySparkline(entry.count, maxCount, 12)}
            </div>
          </div>
        </td>`}
      </tr>`;
    })
    .join("");
}

/* ────────────────────────────────────────────────────────────
   Leaderboard Filters
──────────────────────────────────────────────────────────── */
function initLeaderboardFilters() {
  const searchInput = document.getElementById("leaderboard-search");
  if (!searchInput) return;

  let debounceTimer;
  searchInput.addEventListener("input", (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const data = getLeaderboardData();
      if (!data) return;

      const query = e.target.value;
      renderLeaderboard(document.getElementById("leaderboard-rows"), data, 0, query);
      renderTopCommenters(document.getElementById("commenters-rows"), data, 0, query);
      renderTopDomains(document.getElementById("domains-rows"), data, 0, query);
    }, 150);
  });
}

/* ────────────────────────────────────────────────────────────
   Smooth Scroll (for hash links)
──────────────────────────────────────────────────────────── */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", (e) => {
      const target = document.querySelector(anchor.getAttribute("href"));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
}

/* ────────────────────────────────────────────────────────────
   Helpers
──────────────────────────────────────────────────────────── */
/**
 * Renders a stable, deterministic activity sparkline based on contribution count.
 */
function renderActivitySparkline(count, maxCount, totalBars = 12) {
  // Calculate how many bars should be "active" (colored) based on the score relative to the leader
  const activeBars = Math.max(1, Math.min(totalBars, Math.ceil((count / maxCount) * totalBars)));

  return Array.from({ length: totalBars }).map((_, i) => {
    const isActive = i < activeBars;

    // Math: Predefined professional "growth" pattern for the bars.
    // baseHeight (25%) provides a minimum visibility for even low counts.
    // growthFactor (0-40%) adds an upward slope from left to right.
    // last term (0-20%) adjusts the overall height based on the user's relative score to maxCount.
    const baseHeight = 25;
    const growthFactor = (i / totalBars) * 40;
    const finalHeight = isActive ? Math.min(100, baseHeight + growthFactor + ((count / maxCount) * 20)) : 10;

    const colorClass = isActive ? 'bg-primary' : 'bg-gray-200 dark:bg-gray-700';
    return `<div class="w-full rounded-t-sm ${colorClass} transition-all duration-500" style="height: ${finalHeight}%"></div>`;
  }).join('');
}

function formatNumber(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + "k";
  return String(n);
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* ────────────────────────────────────────────────────────────
   Reactions Helpers
──────────────────────────────────────────────────────────── */
const REACTION_EMOJIS = {
  "+1": "👍",
  "-1": "👎",
  "laugh": "😄",
  "hooray": "🎉",
  "confused": "😕",
  "heart": "❤️",
  "rocket": "🚀",
  "eyes": "👀"
};

function aggregateReactions(reactions) {
  const counts = {};
  reactions.forEach((reaction) => {
    let type = reaction.content || reaction.name;
    if (type === "thumbsup") type = "+1";
    if (type === "thumbsdown") type = "-1";
    counts[type] = (counts[type] || 0) + 1;
  });
  return counts;
}

function formatReactions(reactions) {
  const items = Object.entries(reactions)
    .filter(([type, count]) => count > 0)
    .map(([type, count]) => {
      const emoji = REACTION_EMOJIS[type] || "❓";
      const label = `${type}: ${count}`;
      return `<span class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded-full text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors align-middle" title="${label}" aria-label="${label}">
        <span aria-hidden="true">${emoji}</span>
        <span class="font-medium">${count}</span>
      </span>`;
    });

  if (items.length === 0) return '';

  return items.join(' ');
}

function timeAgo(dateString) {
  const seconds = Math.floor((Date.now() - new Date(dateString)) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks} week${weeks === 1 ? "" : "s"} ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`;
  const years = Math.floor(days / 365);
  return `${years} year${years === 1 ? "" : "s"} ago`;
}
