// BLT Jobs links in the shared OWASP BLT bar (<blt-nav>, from owaspblt.org/_shared/blt-nav.js).
// This script runs before the bar's deferred script, and puts the <blt-nav> element with the
// BLT Jobs links and buttons where the page's #navbar-placeholder is (first in <body>).
// The bar is the only header: it shows the links, its menu on phones, and the theme toggle.
(function () {
  const links = [
    { name: "Browse Jobs", href: "./jobs.html", also: ["job.html"] },
    { name: "Saved", href: "./saved-jobs.html", showBadge: true },
    { name: "Find Talent", href: "./seekers.html", also: ["seeker.html"] },
    { name: "Leaderboard", href: "./leaderboard.html" },
  ];

  const provider = window.BLTProvider || {
    repositoryUrl: "https://git.owaspblt.org/BLT/tree/main/blt-jobs",
  };

  // The current page's link gets aria-current="page" (a job page marks Browse Jobs,
  // a seeker page marks Find Talent).
  const currentPath = window.location.pathname.split("/").pop() || "index.html";

  const nav = document.createElement("blt-nav");
  nav.setAttribute("project", "blt-jobs");
  nav.setAttribute("name", "Jobs");
  nav.setAttribute("home", "./index.html");
  nav.setAttribute("data-sticky", "");

  function addLink(text, href, attrs) {
    const a = document.createElement("a");
    a.href = href;
    a.textContent = text;
    Object.keys(attrs || {}).forEach((k) => a.setAttribute(k, attrs[k]));
    nav.appendChild(a);
    return a;
  }

  links.forEach((link) => {
    const file = link.href.split("/").pop();
    const active = currentPath === file || (link.also || []).includes(currentPath);
    const a = addLink(link.name, link.href, active ? { "aria-current": "page" } : {});
    if (link.showBadge) {
      const badge = document.createElement("span");
      badge.className =
        "saved-count-badge hidden ml-1 inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold leading-none text-white bg-red-600 rounded-full";
      a.appendChild(badge);
    }
  });
  addLink("Source", provider.repositoryUrl, {
    id: "nav-gitlab",
    slot: "actions",
    "data-provider-repository": "",
    target: "_blank",
    rel: "noreferrer noopener",
  });
  addLink("Post a Job", "./add.html", { slot: "actions", "data-primary": "" });

  const placeholder = document.getElementById("navbar-placeholder");
  if (placeholder) placeholder.replaceWith(nav);
  else document.body.insertBefore(nav, document.body.firstChild);

  // Saved jobs count on the "Saved" link
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

  updateSavedCountBadge();
  window.addEventListener("savedJobsChanged", updateSavedCountBadge);
})();
