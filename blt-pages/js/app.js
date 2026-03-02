/**
 * BLT Pages – Application JavaScript
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
  initPricing();
  loadLeaderboard();
  loadRecentBugs();
  initSmoothScroll();
});

/* ────────────────────────────────────────────────────────────
   Dark Mode
──────────────────────────────────────────────────────────── */
function initDarkMode() {
  const html = document.documentElement;
  const btn = document.getElementById("dark-toggle");
  if (!btn) return;

  // Restore saved preference (or system preference)
  const saved = localStorage.getItem("blt-theme");
  if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
    html.classList.add("dark");
  }

  btn.addEventListener("click", () => {
    html.classList.toggle("dark");
    localStorage.setItem("blt-theme", html.classList.contains("dark") ? "dark" : "light");
  });
}

/* ────────────────────────────────────────────────────────────
   Mobile Menu
──────────────────────────────────────────────────────────── */
function initMobileMenu() {
  const toggle = document.getElementById("mobile-menu-toggle");
  const menu = document.getElementById("mobile-menu");
  if (!toggle || !menu) return;

  toggle.addEventListener("click", () => {
    const open = menu.classList.toggle("hidden");
    toggle.setAttribute("aria-expanded", String(!open));
  });

  // Close when a nav link is clicked
  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menu.classList.add("hidden");
      toggle.setAttribute("aria-expanded", "false");
    });
  });
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
      btn.href = "https://github.com/OWASP-BLT/BLT-Pages/issues/new?template=bug_report.yml&anonymous=true";
      btn.querySelector(".btn-label").textContent = "Report Bug Anonymously";
    } else {
      btn.href = "https://github.com/OWASP-BLT/BLT-Pages/issues/new?template=bug_report.yml";
      btn.querySelector(".btn-label").textContent = "Report a Bug";
    }
  });
}

/* ────────────────────────────────────────────────────────────
   Pricing Section
──────────────────────────────────────────────────────────── */
function initPricing() {
  const section = document.getElementById("pricing");
  const navLink = document.getElementById("pricing-nav-link");
  const navLinkMobile = document.getElementById("pricing-nav-link-mobile");

  if (!section) return;

  if (!BLT_CONFIG.SHOW_PRICING) {
    section.classList.add("hidden");
    if (navLink) navLink.classList.add("hidden");
    if (navLinkMobile) navLinkMobile.classList.add("hidden");
    return;
  }

  // Render pricing plans dynamically
  const grid = document.getElementById("pricing-grid");
  if (!grid) return;

  BLT_CONFIG.PRICING_PLANS.forEach((plan) => {
    const priceText =
      plan.price === null
        ? "Custom"
        : plan.price === 0
        ? "Free"
        : `$${plan.price}`;

    const featuresHtml = plan.features
      .map(
        (f) =>
          `<li class="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
             <i class="fa-solid fa-check text-primary mt-0.5 flex-shrink-0" aria-hidden="true"></i>
             <span>${f}</span>
           </li>`
      )
      .join("");

    const highlightClasses = plan.highlighted
      ? "border-primary shadow-lg ring-2 ring-primary"
      : "border-neutral-border dark:border-gray-700";

    const badgeHtml = plan.highlighted
      ? `<span class="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white text-xs font-bold px-3 py-1 rounded-full">Most Popular</span>`
      : "";

    const ctaClasses = plan.highlighted
      ? "bg-primary hover:bg-primary-hover text-white"
      : "border-2 border-primary text-primary hover:bg-primary hover:text-white";

    const shareHtml =
      plan.id === "pro"
        ? `<p class="text-xs text-center text-gray-500 dark:text-gray-400 mt-3">
             <i class="fa-solid fa-hand-holding-dollar text-primary mr-1" aria-hidden="true"></i>
             Reporters earn <strong class="text-primary">${BLT_CONFIG.REVENUE_SHARE_PERCENT}%</strong> of your subscription
           </p>`
        : "";

    grid.insertAdjacentHTML(
      "beforeend",
      `<div class="relative bg-white dark:bg-dark-surface border ${highlightClasses} rounded-2xl p-8">
         ${badgeHtml}
         <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-1">${plan.name}</h3>
         <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">${plan.description}</p>
         <div class="mb-6">
           <span class="text-4xl font-bold text-gray-900 dark:text-white">${priceText}</span>
           <span class="text-sm text-gray-500 dark:text-gray-400 ml-1">${plan.period}</span>
         </div>
         <ul class="space-y-3 mb-8">${featuresHtml}</ul>
         <a href="${plan.cta_href}" class="flex items-center justify-center w-full font-semibold px-6 py-3 rounded-xl transition-colors ${ctaClasses}">
           ${plan.cta}
         </a>
         ${shareHtml}
       </div>`
    );
  });
}

/* ────────────────────────────────────────────────────────────
   Leaderboard
──────────────────────────────────────────────────────────── */
async function loadLeaderboard() {
  const container = document.getElementById("leaderboard-rows");
  const statBugs = document.getElementById("stat-total-bugs");
  const statDomains = document.getElementById("stat-domains");
  const statReporters = document.getElementById("stat-reporters");

  if (!container) return;

  try {
    // Try static JSON first (generated by GitHub Action)
    const res = await fetch("data/leaderboard.json");
    if (!res.ok) throw new Error("No static data");
    const data = await res.json();
    renderLeaderboard(container, data);
    renderTopCommenters(document.getElementById("commenters-rows"), data);
    renderTopDomains(document.getElementById("domains-rows"), data);
    if (statBugs) statBugs.textContent = formatNumber(data.total_bugs || 0);
    if (statReporters) statReporters.textContent = formatNumber(data.leaderboard?.length || 0);
    if (statDomains) statDomains.textContent = data.total_domains != null ? formatNumber(data.total_domains) : "-";
  } catch {
    // Fall back to GitHub API (subject to rate limits for unauthenticated calls)
    try {
      await loadLeaderboardFromAPI(container, statBugs, statDomains, statReporters);
    } catch (err) {
      container.innerHTML = `<tr><td colspan="4" class="text-center py-8 text-gray-500 dark:text-gray-400">
        <i class="fa-solid fa-circle-exclamation text-primary mr-2" aria-hidden="true"></i>
        Could not load leaderboard. <a href="https://github.com/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues" class="text-primary underline" target="_blank" rel="noopener noreferrer">View on GitHub</a>
      </td></tr>`;
    }
  }
}

async function loadLeaderboardFromAPI(container, statBugs, statDomains, statReporters) {
  const url = `https://api.github.com/repos/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues?state=all&labels=bug&per_page=100`;
  const res = await fetch(url, { headers: { Accept: "application/vnd.github+json" } });
  if (!res.ok) throw new Error(`GitHub API error ${res.status}`);
  const issues = await res.json();

  // Build counts map
  const counts = {};
  const domainCounts = {};

  for (const issue of issues) {
    if (issue.pull_request) continue;
    const user = issue.user.login;
    counts[user] = (counts[user] || { count: 0, avatar_url: issue.user.avatar_url, profile_url: issue.user.html_url });
    counts[user].count++;

    // Extract domain from URL field
    const urlMatch = issue.body?.match(/### URL\s*\n\n(https?:\/\/[^\s\n]+)/);
    if (urlMatch) {
      try {
        const domain = new URL(urlMatch[1]).hostname;
        domainCounts[domain] = (domainCounts[domain] || 0) + 1;
      } catch { /* ignore malformed URLs */ }
    }
  }

  const leaderboard = Object.entries(counts)
    .sort(([, a], [, b]) => b.count - a.count)
    .slice(0, 50)
    .map(([login, data], idx) => ({ rank: idx + 1, login, ...data }));

  const topDomains = Object.entries(domainCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 20)
    .map(([domain, count], idx) => ({ rank: idx + 1, domain, count }));

  const data = {
    leaderboard,
    // Commenters require per-issue API calls; omit in the live-API fallback
    // to avoid rate-limit exhaustion. Full data is available via static JSON.
    top_commenters: [],
    top_domains: topDomains,
    total_bugs: issues.filter((i) => !i.pull_request).length,
    total_domains: Object.keys(domainCounts).length,
    updated_at: new Date().toISOString(),
  };

  renderLeaderboard(container, data);
  renderTopCommenters(document.getElementById("commenters-rows"), data);
  renderTopDomains(document.getElementById("domains-rows"), data);
  if (statBugs) statBugs.textContent = formatNumber(data.total_bugs);
  if (statDomains) statDomains.textContent = data.total_domains != null ? formatNumber(data.total_domains) : "-";
  if (statReporters) statReporters.textContent = formatNumber(leaderboard.length);
}

function renderLeaderboard(container, data) {
  if (!data.leaderboard || data.leaderboard.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      <i class="fa-solid fa-trophy text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true"></i>
      No reports yet. Be the first to <a href="https://github.com/OWASP-BLT/BLT-Pages/issues/new?template=bug_report.yml" class="text-primary underline hover:no-underline">report a bug</a>!
    </td></tr>`;
    return;
  }

  const rankIcons = ["🥇", "🥈", "🥉"];

  container.innerHTML = data.leaderboard
    .map((entry) => {
      const rankDisplay =
        entry.rank <= 3
          ? `<span class="text-xl" aria-label="Rank ${entry.rank}">${rankIcons[entry.rank - 1]}</span>`
          : `<span class="font-bold text-gray-500 dark:text-gray-400">#${entry.rank}</span>`;

      const rowClass =
        entry.rank <= 3
          ? "bg-active-bg dark:bg-red-900/10"
          : "hover:bg-gray-50 dark:hover:bg-gray-800/50";

      return `<tr class="${rowClass} transition-colors">
        <td class="px-4 py-3 text-center w-12">${rankDisplay}</td>
        <td class="px-4 py-3">
          <a href="${entry.profile_url || `https://github.com/${entry.login}`}"
             target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-3 group">
            <img src="${entry.avatar_url || `https://github.com/${entry.login}.png`}"
                 alt="${entry.login}'s avatar"
                 class="w-8 h-8 rounded-full border border-neutral-border dark:border-gray-700"
                 loading="lazy"
                 onerror="this.src='https://github.com/identicons/${entry.login}.png'" />
            <span class="font-medium text-gray-900 dark:text-white group-hover:text-primary transition-colors">
              ${escapeHtml(entry.login)}
            </span>
          </a>
        </td>
        <td class="px-4 py-3 text-right">
          <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">
            <i class="fa-solid fa-bug text-primary text-xs" aria-hidden="true"></i>
            ${formatNumber(entry.count)}
          </span>
        </td>
        <td class="px-4 py-3 hidden sm:table-cell">
          <div class="flex justify-end">
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-2 w-24 overflow-hidden">
              <div class="bg-primary h-2 rounded-full" style="width:${Math.min(100, data.leaderboard[0]?.count ? (entry.count / data.leaderboard[0].count) * 100 : 0)}%"></div>
            </div>
          </div>
        </td>
      </tr>`;
    })
    .join("");

  // Update timestamp if present
  const ts = document.getElementById("leaderboard-updated");
  if (ts && data.updated_at) {
    ts.textContent = `Updated ${new Date(data.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;
  }
}

/* ────────────────────────────────────────────────────────────
   Recent Bug Reports
──────────────────────────────────────────────────────────── */
async function loadRecentBugs() {
  const grid = document.getElementById("recent-bugs-grid");
  if (!grid) return;

  try {
    // Try static JSON first (generated by GitHub Action)
    const res = await fetch("data/leaderboard.json");
    if (!res.ok) throw new Error("No static data");
    const data = await res.json();

    if (data.recent_bugs && data.recent_bugs.length > 0) {
      renderRecentBugs(data.recent_bugs);
      return;
    }
    // Fall back to API if recent_bugs not in static data
    throw new Error("No recent_bugs in static data");
  } catch {
    try {
      await loadRecentBugsFromAPI(grid);
    } catch {
      renderRecentBugs([]);
    }
  }
}

async function loadRecentBugsFromAPI(grid) {
  const url = `https://api.github.com/repos/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues?state=all&labels=bug&per_page=3&sort=created&direction=desc`;
  const res = await fetch(url, { headers: { Accept: "application/vnd.github+json" } });
  if (!res.ok) throw new Error(`GitHub API error ${res.status}`);
  const issues = await res.json();

  const bugs = issues
    .filter((i) => !i.pull_request)
    .slice(0, 3)
    .map((issue) => ({
      number: issue.number,
      title: issue.title,
      html_url: issue.html_url,
      created_at: issue.created_at,
      user: {
        login: issue.user.login,
        avatar_url: issue.user.avatar_url,
        profile_url: issue.user.html_url,
      },
      image_url: extractFirstImage(issue.body),
    }));

  renderRecentBugs(bugs);
}

function extractFirstImage(body) {
  if (!body) return null;
  const mdMatch = body.match(/!\[.*?\]\((https?:\/\/[^\s)]+)\)/);
  if (mdMatch) return mdMatch[1];
  const htmlMatch = body.match(/<img[^>]+src=["'](https?:\/\/[^\s"']+)["']/i);
  if (htmlMatch) return htmlMatch[1];
  return null;
}

function renderRecentBugs(bugs) {
  const grid = document.getElementById("recent-bugs-grid");
  if (!grid) return;

  if (!bugs || bugs.length === 0) {
    grid.innerHTML = `<div class="col-span-3 text-center py-12 text-gray-400 dark:text-gray-500">
      <i class="fa-solid fa-bug text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true"></i>
      No bug reports yet. <a href="https://github.com/OWASP-BLT/BLT-Pages/issues/new?template=bug_report.yml" class="text-primary hover:underline">Be the first to report!</a>
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
             <i class="fa-solid fa-bug text-4xl text-gray-300 dark:text-gray-600" aria-hidden="true"></i>
           </div>`;

      const date = new Date(bug.created_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });

      const avatarUrl = escapeHtml(
        bug.user.avatar_url || `https://github.com/${bug.user.login}.png`
      );
      const profileUrl = escapeHtml(
        bug.user.profile_url || `https://github.com/${bug.user.login}`
      );
      const login = escapeHtml(bug.user.login);

      return `<div class="bg-white dark:bg-dark-base border border-neutral-border dark:border-gray-700 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col">
        ${imgHtml}
        <h3 class="font-semibold text-gray-900 dark:text-white mb-3 line-clamp-2 flex-1">
          <a href="${escapeHtml(bug.html_url)}" target="_blank" rel="noopener noreferrer"
             class="hover:text-primary transition-colors">
            ${escapeHtml(bug.title)}
          </a>
        </h3>
        <div class="flex items-center justify-between mt-auto pt-3 border-t border-neutral-border dark:border-gray-700">
          <a href="${profileUrl}" target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-2 group">
            <img src="${avatarUrl}"
                 alt="${login}'s avatar"
                 class="w-7 h-7 rounded-full border border-neutral-border dark:border-gray-700"
                 loading="lazy"
                 onerror="this.src='https://github.com/identicons/${login}.png'" />
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-primary transition-colors">
              ${login}
            </span>
          </a>
          <span class="text-xs text-gray-400 dark:text-gray-500">${date}</span>
        </div>
      </div>`;
    })
    .join("");
}

/* ────────────────────────────────────────────────────────────
   Top Commenters
──────────────────────────────────────────────────────────── */
function renderTopCommenters(container, data) {
  if (!container) return;

  const commenters = data.top_commenters || [];
  if (commenters.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      <i class="fa-solid fa-comment text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true"></i>
      No comments yet. Start a conversation on a <a href="https://github.com/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues" class="text-primary underline hover:no-underline" target="_blank" rel="noopener noreferrer">bug report</a>!
    </td></tr>`;
    return;
  }

  const rankIcons = ["🥇", "🥈", "🥉"];
  const maxCount = commenters[0]?.count || 1;

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

      return `<tr class="${rowClass} transition-colors">
        <td class="px-4 py-3 text-center w-12">${rankDisplay}</td>
        <td class="px-4 py-3">
          <a href="${entry.profile_url || `https://github.com/${entry.login}`}"
             target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-3 group">
            <img src="${entry.avatar_url || `https://github.com/${entry.login}.png`}"
                 alt="${escapeHtml(entry.login)}'s avatar"
                 class="w-8 h-8 rounded-full border border-neutral-border dark:border-gray-700"
                 loading="lazy"
                 onerror="this.src='https://github.com/identicons/${escapeHtml(entry.login)}.png'" />
            <span class="font-medium text-gray-900 dark:text-white group-hover:text-primary transition-colors">
              ${escapeHtml(entry.login)}
            </span>
          </a>
        </td>
        <td class="px-4 py-3 text-right">
          <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">
            <i class="fa-solid fa-comment text-primary text-xs" aria-hidden="true"></i>
            ${formatNumber(entry.count)}
          </span>
        </td>
        <td class="px-4 py-3 hidden sm:table-cell">
          <div class="flex justify-end">
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-2 w-24 overflow-hidden">
              <div class="bg-primary h-2 rounded-full" style="width:${Math.min(100, (entry.count / maxCount) * 100)}%"></div>
            </div>
          </div>
        </td>
      </tr>`;
    })
    .join("");
}

/* ────────────────────────────────────────────────────────────
   Top Domains
──────────────────────────────────────────────────────────── */
function renderTopDomains(container, data) {
  if (!container) return;

  const domains = data.top_domains || [];
  if (domains.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      <i class="fa-solid fa-globe text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true"></i>
      No domain data yet. <a href="https://github.com/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues/new?template=bug_report.yml" class="text-primary underline hover:no-underline">Be the first to report a bug!</a>
    </td></tr>`;
    return;
  }

  const rankIcons = ["🥇", "🥈", "🥉"];
  const maxCount = domains[0]?.count || 1;

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

      return `<tr class="${rowClass} transition-colors">
        <td class="px-4 py-3 text-center w-12">${rankDisplay}</td>
        <td class="px-4 py-3">
          <a href="https://${escapeHtml(entry.domain)}"
             target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-3 group">
            <img src="${faviconUrl}"
                 alt="${escapeHtml(entry.domain)} favicon"
                 class="w-5 h-5 rounded flex-shrink-0"
                 loading="lazy"
                 onerror="this.outerHTML='<i class=\\'fa-solid fa-globe text-gray-400 w-5 h-5 flex-shrink-0\\' aria-hidden=\\'true\\'></i>'" />
            <span class="font-medium text-gray-900 dark:text-white group-hover:text-primary transition-colors">
              ${escapeHtml(entry.domain)}
            </span>
          </a>
        </td>
        <td class="px-4 py-3 text-right">
          <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">
            <i class="fa-solid fa-bug text-primary text-xs" aria-hidden="true"></i>
            ${formatNumber(entry.count)}
          </span>
        </td>
        <td class="px-4 py-3 hidden sm:table-cell">
          <div class="flex justify-end">
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-2 w-24 overflow-hidden">
              <div class="bg-primary h-2 rounded-full" style="width:${Math.min(100, (entry.count / maxCount) * 100)}%"></div>
            </div>
          </div>
        </td>
      </tr>`;
    })
    .join("");
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
