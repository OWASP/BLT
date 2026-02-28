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
      btn.href = "report-bug.html?anonymous=true";
      btn.querySelector(".btn-label").textContent = "Report Bug Anonymously";
    } else {
      btn.href = "report-bug.html";
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
  const statOrgs = document.getElementById("stat-orgs");
  const statReporters = document.getElementById("stat-reporters");

  if (!container) return;

  try {
    // Try static JSON first (generated by GitHub Action)
    const res = await fetch("data/leaderboard.json");
    if (!res.ok) throw new Error("No static data");
    const data = await res.json();
    renderLeaderboard(container, data);
    if (statBugs) statBugs.textContent = formatNumber(data.total_bugs || 0);
    if (statReporters) statReporters.textContent = formatNumber(data.leaderboard?.length || 0);
    if (statOrgs) statOrgs.textContent = formatNumber(data.total_orgs || 0);
  } catch {
    // Fall back to GitHub API (subject to rate limits for unauthenticated calls)
    try {
      await loadLeaderboardFromAPI(container, statBugs, statOrgs, statReporters);
    } catch (err) {
      container.innerHTML = `<tr><td colspan="4" class="text-center py-8 text-gray-500 dark:text-gray-400">
        <i class="fa-solid fa-circle-exclamation text-primary mr-2" aria-hidden="true"></i>
        Could not load leaderboard. <a href="https://github.com/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues" class="text-primary underline" target="_blank" rel="noopener noreferrer">View on GitHub</a>
      </td></tr>`;
    }
  }
}

async function loadLeaderboardFromAPI(container, statBugs, statOrgs, statReporters) {
  const url = `https://api.github.com/repos/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues?state=all&labels=bug&per_page=100`;
  const res = await fetch(url, { headers: { Accept: "application/vnd.github+json" } });
  if (!res.ok) throw new Error(`GitHub API error ${res.status}`);
  const issues = await res.json();

  // Build counts map
  const counts = {};
  const orgs = new Set();
  for (const issue of issues) {
    if (issue.pull_request) continue;
    const user = issue.user.login;
    counts[user] = (counts[user] || { count: 0, avatar_url: issue.user.avatar_url, profile_url: issue.user.html_url });
    counts[user].count++;

    // Extract org from body (ORG_NAME field)
    const orgMatch = issue.body?.match(/### Organization Name.*?\n\n(.+)/s);
    if (orgMatch) orgs.add(orgMatch[1].trim().split("\n")[0]);
  }

  const leaderboard = Object.entries(counts)
    .sort(([, a], [, b]) => b.count - a.count)
    .slice(0, 50)
    .map(([login, data], idx) => ({ rank: idx + 1, login, ...data }));

  const data = {
    leaderboard,
    total_bugs: issues.filter((i) => !i.pull_request).length,
    total_orgs: orgs.size,
    updated_at: new Date().toISOString(),
  };

  renderLeaderboard(container, data);
  if (statBugs) statBugs.textContent = formatNumber(data.total_bugs);
  if (statOrgs) statOrgs.textContent = formatNumber(data.total_orgs);
  if (statReporters) statReporters.textContent = formatNumber(leaderboard.length);
}

function renderLeaderboard(container, data) {
  if (!data.leaderboard || data.leaderboard.length === 0) {
    container.innerHTML = `<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">
      <i class="fa-solid fa-trophy text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true"></i>
      No reports yet. Be the first to <a href="report-bug.html" class="text-primary underline hover:no-underline">report a bug</a>!
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
