(function () {
  const links = [
    { name: "Home", href: "./index.html" },
    { name: "Browse Jobs", href: "./jobs.html" },
    { name: "Saved", href: "./saved-jobs.html", icon: "fa-regular fa-bookmark", showBadge: true },
    { name: "Find Talent", href: "./seekers.html" },
    { name: "Leaderboard", href: "./leaderboard.html" },
  ];

  // Helper to determine the repository URL (standard across pages)
  const params = new URLSearchParams(window.location.search);
  const defaultRepo =
    window.location.hostname.indexOf("pritz395.github.io") !== -1
      ? "Pritz395/BLT-Jobs"
      : "OWASP-BLT/BLT-Jobs";
  const repoParam = params.get("repo");
  const repo =
    typeof repoParam === "string" &&
    /^[A-Za-z0-9._-]+\/[A-Za-z0-9._-]+$/.test(repoParam)
      ? repoParam
      : defaultRepo;
  const githubUrl = "https://github.com/" + repo;

  // Determine which page is current to highlight the active link
  const currentPath = window.location.pathname.split("/").pop() || "index.html";

  function getLinkHtml(link, isMobile) {
    const linkPath = link.href.split("/").pop();
    
    // Normalize active state detection
    let isActive = currentPath === linkPath;
    
    // Special case: 'Browse Jobs' should be active when viewing a single 'job.html'
    if (linkPath === "jobs.html" && currentPath === "job.html") {
      isActive = true;
    }
    
    // Special case: 'Find Talent' should be active when viewing a single 'seeker.html'
    if (linkPath === "seekers.html" && currentPath === "seeker.html") {
      isActive = true;
    }

    const baseClasses = "rounded-lg px-3 py-2 text-sm font-medium transition";
    const activeClasses = "bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50";
    const inactiveClasses = "text-slate-700 hover:bg-slate-100 dark:text-gray-300 dark:hover:bg-gray-800";
    
    const classes = `${baseClasses} ${isActive ? activeClasses : inactiveClasses} ${link.showBadge ? "flex items-center gap-1" : ""}`;

    let content = "";
    if (link.icon) content += `<i class="${link.icon} text-xs" aria-hidden="true"></i> `;
    content += isMobile && link.name === "Saved" ? "Saved Jobs" : link.name;
    
    if (link.showBadge) {
      content += ` <span class="saved-count-badge hidden ml-1 inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold leading-none text-white bg-red-600 rounded-full"></span>`;
    }

    return `<a href="${link.href}" class="${classes}">${content}</a>`;
  }

  const desktopLinksHtml = links.map((l) => getLinkHtml(l, false)).join("");
  const mobileLinksHtml = links.map((l) => getLinkHtml(l, true)).join("");

  const githubLinkHtml = `
    <a id="nav-github" href="${githubUrl}" target="_blank" rel="noreferrer noopener" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
      <i class="fa-brands fa-github" aria-hidden="true"></i>
      GitHub
    </a>
  `;

  const navbarHtml = `
    <nav class="border-b fixed w-full z-[100] border-slate-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900/95">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="flex h-16 items-center justify-between">
          <a href="./index.html" class="flex items-center gap-2 select-none">
            <img src="assets/images/blt-logo.png" class="h-9 sm:h-10 w-auto" alt="OWASP BLT Logo" width="50" height="50" />
            <span class="text-xl font-bold text-slate-900 dark:text-white">BLT Jobs</span>
          </a>
          <div class="hidden sm:flex items-center gap-1">
            ${desktopLinksHtml}
            ${githubLinkHtml}
          </div>
          <div class="flex items-center gap-2">
            <button id="theme-toggle" class="relative inline-flex h-10 w-10 items-center justify-center rounded-lg border-2 border-red-600 text-red-600 transition hover:bg-red-600 hover:text-white dark:border-red-500 dark:text-red-500 dark:hover:bg-red-600 dark:hover:text-white" aria-label="Toggle dark mode">
              <i id="sun-icon" class="fas fa-sun text-xl absolute opacity-0 transition-all duration-300 -rotate-90 dark:opacity-100 dark:rotate-0"></i>
              <i id="moon-icon" class="fas fa-moon text-xl absolute opacity-100 transition-all duration-300 rotate-0 dark:opacity-0 dark:rotate-90"></i>
            </button>
            <button id="mobile-menu-toggle" class="sm:hidden inline-flex h-10 w-10 items-center justify-center rounded-lg border-2 border-slate-200 text-slate-700 transition hover:bg-slate-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800" aria-label="Open menu" aria-controls="mobile-menu" aria-expanded="false">
              <i class="fa-solid fa-bars text-lg" aria-hidden="true"></i>
            </button>
          </div>
        </div>
        <div id="mobile-menu" class="hidden border-t border-slate-200 py-3 sm:hidden dark:border-gray-700">
          <div class="flex flex-col gap-1">
            ${mobileLinksHtml}
            <div class="px-3 py-2">
               <a href="${githubUrl}" target="_blank" rel="noreferrer noopener" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
                <i class="fa-brands fa-github" aria-hidden="true"></i>
                GitHub
              </a>
            </div>
          </div>
        </div>
      </div>
    </nav>
  `;

  // Inject the navbar
  const placeholder = document.getElementById("navbar-placeholder");
  if (placeholder) {
    placeholder.innerHTML = navbarHtml;
  } else {
    // Fallback: prepend to body if no placeholder exists
    const div = document.createElement("div");
    div.id = "navbar-placeholder";
    div.innerHTML = navbarHtml;
    document.body.insertBefore(div, document.body.firstChild);
  }

  // Handle saved count badge updates
  function updateSavedCountBadge() {
    const badges = document.querySelectorAll(".saved-count-badge");
    if (badges.length > 0 && typeof SavedJobs !== "undefined") {
      const count = SavedJobs.count();
      badges.forEach((badge) => {
        if (count > 0) {
          badge.textContent = count;
          badge.classList.remove("hidden");
        } else {
          badge.classList.add("hidden");
        }
      });
    }
  }

  // Initial update and event listener
  updateSavedCountBadge();
  window.addEventListener("savedJobsChanged", updateSavedCountBadge);
})();
