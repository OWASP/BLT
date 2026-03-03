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
    const urlMatch = issue.body?.match(/### URL\s*\n\n(\S+)/);
    if (urlMatch) {
      try {
        let rawUrl = urlMatch[1].trim();
        if (rawUrl.startsWith("//")) {
          rawUrl = "https:" + rawUrl;
        } else if (!rawUrl.startsWith("http://") && !rawUrl.startsWith("https://")) {
          rawUrl = "https://" + rawUrl;
        }
        const domain = new URL(rawUrl).hostname;
        if (domain) {
          domainCounts[domain] = (domainCounts[domain] || 0) + 1;
        }
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
  const maxCount = data.leaderboard[0]?.count || 1;

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

      const activityPct = Math.min(100, (entry.count / maxCount) * 100);
      return `<tr class="${rowClass} transition-colors">
        <td class="px-4 py-3 text-center w-12">${rankDisplay}</td>
        <td class="px-4 py-3">
          <a href="${entry.profile_url || `https://github.com/${entry.login}`}"
             target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-3 group min-w-0">
            <img src="${entry.avatar_url || `https://github.com/${entry.login}.png`}"
                 alt="${escapeHtml(entry.login)}'s avatar"
                 class="w-8 h-8 rounded-full border border-neutral-border dark:border-gray-700 flex-shrink-0"
                 loading="lazy"
                 onerror="this.src='https://github.com/identicons/${escapeHtml(entry.login)}.png'" />
            <span class="font-medium text-gray-900 dark:text-white group-hover:text-primary transition-colors truncate min-w-0 flex-1">
              ${escapeHtml(entry.login)}
            </span>
          </a>
          <div class="flex sm:hidden items-center gap-2 mt-1 pl-11">
            <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white text-xs">
              <i class="fa-solid fa-bug text-primary text-xs" aria-hidden="true"></i>
              ${formatNumber(entry.count)}
            </span>
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 flex-1 overflow-hidden">
              <div class="bg-primary h-1.5 rounded-full" style="width:${activityPct}%"></div>
            </div>
          </div>
        </td>
        <td class="hidden px-4 py-3 text-right sm:table-cell">
          <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">
            <i class="fa-solid fa-bug text-primary text-xs" aria-hidden="true"></i>
            ${formatNumber(entry.count)}
          </span>
        </td>
        <td class="px-4 py-3 hidden sm:table-cell">
          <div class="flex justify-end">
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-2 w-24 overflow-hidden">
              <div class="bg-primary h-2 rounded-full" style="width:${activityPct}%"></div>
            </div>
          </div>
        </td>
      </tr>`;
    })
    .join("");

  // Update timestamps if present
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
      const commitUrl = `https://github.com/${encodeURIComponent(BLT_CONFIG.REPO_OWNER)}/${encodeURIComponent(BLT_CONFIG.REPO_NAME)}/commit/${sha}`;
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

  // Always use API to fetch reactions
  try {
    await loadRecentBugsFromAPI(grid);
  } catch {
    // Fall back to static JSON if API fails (but without reactions)
    try {
      const res = await fetch("data/leaderboard.json");
      if (!res.ok) throw new Error("No static data");
      const data = await res.json();

      if (data.recent_bugs && data.recent_bugs.length > 0) {
        renderRecentBugs(data.recent_bugs);
        return;
      }
    } catch {
      renderRecentBugs([]);
    }
  }
}

async function loadRecentBugsFromAPI(grid) {
  const baseUrl = `https://api.github.com/repos/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}`;

  const issuesUrl = `${baseUrl}/issues?state=open&labels=bug&per_page=3&sort=created&direction=desc`;

  const res = await fetch(issuesUrl, {
    headers: { Accept: "application/vnd.github+json" },
  });

  if (!res.ok) throw new Error(`GitHub API error ${res.status}`);

  const issues = await res.json();

  const bugs = await Promise.all(
    issues
      .filter((i) => !i.pull_request)
      .slice(0, 3)
      .map(async (issue) => {
        // -------------------------
        // Extract domain
        // -------------------------
        let domain = null;
        const urlMatch = issue.body?.match(/### URL\s*\n\n(https?:\/\/[^\s\n]+)/);
        if (urlMatch) {
          try {
            domain = new URL(urlMatch[1]).hostname;
          } catch {
            /* ignore invalid URLs */
          }
        }

        // -------------------------
        // Fetch latest comment
        // -------------------------
        let latestComment = null;
        if (issue.comments > 0) {
          try {
            const commentsRes = await fetch(
              `${baseUrl}/issues/${issue.number}/comments?per_page=1&sort=created&direction=desc`,
              { headers: { Accept: "application/vnd.github+json" } }
            );

            if (commentsRes.ok) {
              const commentsData = await commentsRes.json();
              if (commentsData.length > 0) {
                const c = commentsData[0];
                latestComment = {
                  body: c.body,
                  created_at: c.created_at,
                  html_url: c.html_url,
                  user: {
                    login: c.user.login,
                    avatar_url: c.user.avatar_url,
                    profile_url: c.user.html_url,
                  },
                };
              }
            }
          } catch (error) {
            console.warn(
              `Failed to fetch latest comment for issue #${issue.number}`,
              error
            );
          }
        }

        // -------------------------
        // Fetch reactions
        // -------------------------
        let reactions = [];
        try {
          const reactionsRes = await fetch(`${issue.url}/reactions`, {
            headers: { Accept: "application/vnd.github+json" },
          });

          if (reactionsRes.ok) {
            const reactionsData = await reactionsRes.json();
            reactions = aggregateReactions(reactionsData);
          }
        } catch (error) {
          console.warn(
            `Failed to fetch reactions for issue #${issue.number}`,
            error
          );
        }

        return {
          number: issue.number,
          title: issue.title,
          html_url: issue.html_url,
          created_at: issue.created_at,
          comment_count: issue.comments,
          user: {
            login: issue.user.login,
            avatar_url: issue.user.avatar_url,
            profile_url: issue.user.html_url,
          },
          image_url: extractFirstImage(issue.body),
          domain,
          latest_comment: latestComment,
          reactions,
        };
      })
  );

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

      const reactionsHtml = bug.reactions
        ? formatReactions(bug.reactions)
        : "";

      const faviconHtml = bug.domain
        ? `<img src="https://www.google.com/s2/favicons?domain=${encodeURIComponent(bug.domain)}&sz=32"
                alt="${escapeHtml(bug.domain)} favicon"
                class="w-4 h-4 rounded flex-shrink-0 inline-block align-middle mr-1"
                loading="lazy"
                referrerpolicy="no-referrer"
                onerror="this.outerHTML='<i class=\\'fa-solid fa-globe text-gray-400 w-4 h-4\\' aria-hidden=\\'true\\'></i>'" />`
        : "";

      // Comment section
      let commentHtml = "";
      const commentCount = bug.comment_count;
      if (typeof commentCount === "number" && commentCount > 0 && bug.latest_comment) {
        const commenter = bug.latest_comment.user;
        const commenterAvatar = escapeHtml(commenter.avatar_url || `https://github.com/${commenter.login}.png`);
        const commenterProfile = escapeHtml(commenter.profile_url || `https://github.com/${commenter.login}`);
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
                   onerror="this.src='https://github.com/identicons/${commenterLogin}.png'" />
            </a>
            <div class="min-w-0 flex-1">
              <p class="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">${commentBody}</p>
              <a href="${escapeHtml(bug.html_url)}" target="_blank" rel="noopener noreferrer"
                 class="inline-flex items-center gap-1 mt-1 text-xs text-gray-400 hover:text-primary transition-colors">
                <i class="fa-solid fa-comment text-xs" aria-hidden="true"></i>
                ${commentCountLabel}
              </a>
            </div>
          </div>
        </div>`;
      } else if (typeof commentCount === "number" && commentCount === 0) {
        commentHtml = `<div class="mt-3 pt-3 border-t border-neutral-border dark:border-gray-700">
          <a href="${escapeHtml(bug.html_url)}" target="_blank" rel="noopener noreferrer"
             class="inline-flex items-center gap-1 text-xs text-primary hover:underline">
            <i class="fa-solid fa-comment text-xs" aria-hidden="true"></i>
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
                   onerror="this.src='https://github.com/identicons/${login}.png'" />
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

      const activityPct = Math.min(100, (entry.count / maxCount) * 100);
      return `<tr class="${rowClass} transition-colors">
        <td class="px-4 py-3 text-center w-12">${rankDisplay}</td>
        <td class="px-4 py-3">
          <a href="${entry.profile_url || `https://github.com/${entry.login}`}"
             target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-3 group min-w-0">
            <img src="${entry.avatar_url || `https://github.com/${entry.login}.png`}"
                 alt="${escapeHtml(entry.login)}'s avatar"
                 class="w-8 h-8 rounded-full border border-neutral-border dark:border-gray-700 flex-shrink-0"
                 loading="lazy"
                 onerror="this.src='https://github.com/identicons/${escapeHtml(entry.login)}.png'" />
            <span class="font-medium text-gray-900 dark:text-white group-hover:text-primary transition-colors truncate min-w-0 flex-1">
              ${escapeHtml(entry.login)}
            </span>
          </a>
          <div class="flex sm:hidden items-center gap-2 mt-1 pl-11">
            <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white text-xs">
              <i class="fa-solid fa-comment text-primary text-xs" aria-hidden="true"></i>
              ${formatNumber(entry.count)}
            </span>
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 flex-1 overflow-hidden">
              <div class="bg-primary h-1.5 rounded-full" style="width:${activityPct}%"></div>
            </div>
          </div>
        </td>
        <td class="hidden px-4 py-3 text-right sm:table-cell">
          <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">
            <i class="fa-solid fa-comment text-primary text-xs" aria-hidden="true"></i>
            ${formatNumber(entry.count)}
          </span>
        </td>
        <td class="px-4 py-3 hidden sm:table-cell">
          <div class="flex justify-end">
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-2 w-24 overflow-hidden">
              <div class="bg-primary h-2 rounded-full" style="width:${activityPct}%"></div>
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
      const activityPct = Math.min(100, (entry.count / maxCount) * 100);

      return `<tr class="${rowClass} transition-colors">
        <td class="px-4 py-3 text-center w-12">${rankDisplay}</td>
        <td class="px-4 py-3">
          <a href="https://${escapeHtml(entry.domain)}"
             target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-3 group min-w-0">
            <img src="${faviconUrl}"
                 alt="${escapeHtml(entry.domain)} favicon"
                 class="w-5 h-5 rounded flex-shrink-0"
                 loading="lazy"
                 onerror="this.outerHTML='<i class=\\'fa-solid fa-globe text-gray-400 w-5 h-5 flex-shrink-0\\' aria-hidden=\\'true\\'></i>'" />
            <span class="font-medium text-gray-900 dark:text-white group-hover:text-primary transition-colors truncate min-w-0 flex-1">
              ${escapeHtml(entry.domain)}
            </span>
          </a>
          <div class="flex sm:hidden items-center gap-2 mt-1 pl-8">
            <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white text-xs">
              <i class="fa-solid fa-bug text-primary text-xs" aria-hidden="true"></i>
              ${formatNumber(entry.count)}
            </span>
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 flex-1 overflow-hidden">
              <div class="bg-primary h-1.5 rounded-full" style="width:${activityPct}%"></div>
            </div>
          </div>
        </td>
        <td class="hidden px-4 py-3 text-right sm:table-cell">
          <span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">
            <i class="fa-solid fa-bug text-primary text-xs" aria-hidden="true"></i>
            ${formatNumber(entry.count)}
          </span>
        </td>
        <td class="px-4 py-3 hidden sm:table-cell">
          <div class="flex justify-end">
            <div class="bg-gray-100 dark:bg-gray-700 rounded-full h-2 w-24 overflow-hidden">
              <div class="bg-primary h-2 rounded-full" style="width:${activityPct}%"></div>
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
    const type = reaction.content;
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
