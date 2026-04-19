let allJobs = [];

function esc(s) { return window.Sanitize.esc(s); }

function normalizeString(value) {
  return (value || "").toString().toLowerCase();
}

/** Infer remote / hybrid / onsite from location, title, and start of description. */
function inferWorkMode(job) {
  const loc = normalizeString(job.location || "");
  const title = normalizeString(job.title || "");
  const desc = normalizeString((job.description || "").slice(0, 4000));
  const hay = `${loc}\n${title}\n${desc}`;

  if (
    /\bhybrid\b|\bremote\s*\/\s*office\b|\boffice\s*\/\s*remote\b|on-?site.{0,50}remote|remote.{0,50}on-?site|split\s+between|partial(ly)?\s+remote|mix\s+of\s+(remote|on-?site)/i.test(
      hay
    ) ||
    /home.{0,80}office|office.{0,80}(at\s+)?home|flexible\s+work\s+(model|location|arrangement)/i.test(hay)
  ) {
    return "hybrid";
  }

  const negRemote =
    /\bnot\s+(an?\s+)?remote\b|\bno\s+remote\b|\bnon[-\s]?remote\b|\bon[-\s]?site\s+only\b|\bin[-\s]?person\s+only\b|\bnot\s+available\s+for\s+remote\b|\bunfortunately.{0,40}not\s+remote/i.test(
      hay
    );
  const remoteStrong =
    /\b(100%|fully?|all)[\s-]*remote\b|\bremote[\s-]?(only|global|worldwide|world[\s-]wide|first|eligible)\b|\bwork\s+from\s+(anywhere|home)\b|\bdistributed\s+(across|team|company|worldwide)\b|\banywhere\s+in\s+(the\s+)?(world|us|u\.?s\.?|usa|uk|europe)\b|\bremote[\s-]?within\b|\bfully?\s+distributed\b/i.test(
      hay
    );
  const remoteSoft = /\bremote\b|\bwfh\b|\btelecommut/i.test(hay);
  if (!negRemote && (remoteStrong || remoteSoft)) return "remote";

  return "onsite";
}

function workModeBadgeHtml(mode) {
  if (mode === "remote") {
    return `<span class="inline-flex shrink-0 items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"><i class="fa-solid fa-house-laptop" aria-hidden="true"></i> Remote</span>`;
  }
  if (mode === "hybrid") {
    return `<span class="inline-flex shrink-0 items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-900 dark:bg-amber-900/40 dark:text-amber-200"><i class="fa-solid fa-shuffle" aria-hidden="true"></i> Hybrid</span>`;
  }
  return `<span class="inline-flex shrink-0 items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700 dark:bg-gray-700 dark:text-gray-300"><i class="fa-solid fa-building-user" aria-hidden="true"></i> On-site</span>`;
}

function sortJobs(jobs, sortKey) {
  const sorted = jobs.slice();
  const t = (sortKey || "newest").toString();

  function createdMs(job) {
    const d = new Date(job.created_at || 0);
    return Number.isNaN(d.getTime()) ? 0 : d.getTime();
  }

  if (t === "newest") sorted.sort((a, b) => createdMs(b) - createdMs(a));
  else if (t === "oldest") sorted.sort((a, b) => createdMs(a) - createdMs(b));
  else if (t === "title-asc")
    sorted.sort((a, b) => (a.title || "").localeCompare(b.title || "", undefined, { sensitivity: "base" }));
  else if (t === "title-desc")
    sorted.sort((a, b) => (b.title || "").localeCompare(a.title || "", undefined, { sensitivity: "base" }));
  else if (t === "company-asc")
    sorted.sort((a, b) =>
      (a.organization_name || "").localeCompare(b.organization_name || "", undefined, { sensitivity: "base" })
    );
  else if (t === "company-desc")
    sorted.sort((a, b) =>
      (b.organization_name || "").localeCompare(a.organization_name || "", undefined, { sensitivity: "base" })
    );

  return sorted;
}

function filtersAreActive() {
  const sortVal = document.getElementById("sortSelect")?.value || "newest";
  return !!(
    (document.getElementById("searchInput")?.value || "").trim() ||
    (document.getElementById("typeFilter")?.value || "") ||
    (document.getElementById("locationFilter")?.value || "").trim() ||
    (document.getElementById("workModeFilter")?.value || "") ||
    (document.getElementById("salaryFilter")?.value || "") ||
    sortVal !== "newest"
  );
}

function isExpiringSoon(expiresAt) {
  if (!expiresAt) return false;
  try {
    const expiryDate = new Date(expiresAt);
    const now = new Date();
    const daysUntilExpiry = (expiryDate - now) / (1000 * 60 * 60 * 24);
    return daysUntilExpiry > 0 && daysUntilExpiry <= 7;
  } catch (e) {
    return false;
  }
}

function isExpired(expiresAt) {
  if (!expiresAt) return false;
  try {
    const expiryDate = new Date(expiresAt);
    return expiryDate < new Date();
  } catch (e) {
    return false;
  }
}

function formatExpiryDate(expiresAt) {
  if (!expiresAt) return "";
  try {
    const expiryDate = new Date(expiresAt);
    const now = new Date();
    const daysUntilExpiry = Math.ceil((expiryDate - now) / (1000 * 60 * 60 * 24));

    if (daysUntilExpiry < 0) return "Expired";
    if (daysUntilExpiry === 0) return "Expires today";
    if (daysUntilExpiry === 1) return "Expires tomorrow";
    if (daysUntilExpiry <= 7) return `Expires in ${daysUntilExpiry} days`;
    return "";
  } catch (e) {
    return "";
  }
}

function renderJobs(jobs) {
  const jobList = document.getElementById("jobList");
  const resultsSummary = document.getElementById("resultsSummary");
  const resultsCount = document.getElementById("resultsCount");
  const resultsLabel = document.getElementById("resultsLabel");
  const emptyState = document.getElementById("emptyState");
  const emptyStateMessage = document.getElementById("emptyStateMessage");
  const clearFiltersButton = document.getElementById("clearFiltersButton");

  if (!jobList || !resultsSummary || !resultsCount || !resultsLabel || !emptyState) {
    return;
  }

  jobList.innerHTML = "";

  if (!jobs || jobs.length === 0) {
    resultsSummary.classList.add("hidden");
    emptyState.classList.remove("hidden");
    emptyStateMessage.textContent = filtersAreActive()
      ? "Try adjusting your search terms or filters"
      : "Check back later for new opportunities";

    if (filtersAreActive()) {
      clearFiltersButton.classList.remove("hidden");
    } else {
      clearFiltersButton.classList.add("hidden");
    }

    return;
  }

  resultsSummary.classList.remove("hidden");
  emptyState.classList.add("hidden");

  if (clearFiltersButton) {
    if (filtersAreActive()) {
      clearFiltersButton.classList.remove("hidden");
    } else {
      clearFiltersButton.classList.add("hidden");
    }
  }

  resultsCount.textContent = jobs.length.toString();
  resultsLabel.textContent = jobs.length === 1 ? " job found" : " jobs found";

  const cardsHtml = jobs
    .map((job) => {
      const title = esc(job.title || "Untitled");
      const company = esc(job.organization_name || "");
      const location = esc(job.location || "");
      const jobType = esc(job.job_type || "");
      const salary = esc(job.salary_range || "");
      const createdAt = esc(job.created_at || "");
      const addedBy = esc(job.added_by || "");
      const workMode = inferWorkMode(job);
      const workBadge = workModeBadgeHtml(workMode);

      const expiryDate =
        [job.expires_at, job.effective_expires_at].find((value) => {
          if (!value) return false;
          const parsed = new Date(value);
          return !Number.isNaN(parsed.getTime());
        }) || null;
      const expired = isExpired(expiryDate);
      const expiringSoon = isExpiringSoon(expiryDate);
      const expiryText = formatExpiryDate(expiryDate);

      let faviconDomain = "";
      if (job.application_url) {
        try {
          faviconDomain = new URL(job.application_url).hostname;
        } catch (e) {}
      }
      const faviconImg = faviconDomain
        ? `<img src="https://www.google.com/s2/favicons?domain=${encodeURIComponent(faviconDomain)}&sz=32" alt="" width="20" height="20" class="w-5 h-5 rounded inline-block mr-1.5 align-middle" aria-hidden="true" />`
        : "";

      const companySpan = company
        ? `<span class="flex items-center gap-1"><i class="fa-solid fa-building" aria-hidden="true"></i> ${company}</span>`
        : "";
      const locationSpan = location
        ? `<span class="flex items-center gap-1"><i class="fa-solid fa-location-dot" aria-hidden="true"></i> ${location}</span>`
        : "";
      const typeSpan = jobType
        ? `<span class="flex items-center gap-1"><i class="fa-solid fa-clock" aria-hidden="true"></i> ${jobType}</span>`
        : "";
      const salarySpan = salary
        ? `<span class="flex items-center gap-1"><i class="fa-solid fa-dollar-sign" aria-hidden="true"></i> ${salary}</span>`
        : "";
      const createdAtSpan = createdAt
        ? `<span class="flex items-center gap-1 text-gray-500 dark:text-gray-500"><i class="fa-solid fa-calendar" aria-hidden="true"></i> Posted ${createdAt}</span>`
        : "";
      const addedBySpan = addedBy
        ? `<span class="flex items-center gap-1"><i class="fa-solid fa-user" aria-hidden="true"></i> Added by <a href="https://github.com/${encodeURIComponent(job.added_by)}" target="_blank" rel="noopener noreferrer" class="font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">@${addedBy}</a></span>`
        : "";

      const expiryBadge = expired
        ? `<span class="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
             <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
             </svg>
             Expired
           </span>`
        : expiringSoon
        ? `<span class="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
             <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
             </svg>
             ${esc(expiryText)}
           </span>`
        : "";

      const borderClass = expired
        ? "border-gray-300 dark:border-gray-600 opacity-60"
        : expiringSoon
        ? "border-orange-300 dark:border-orange-700"
        : "border-slate-200 dark:border-gray-700";

      return `
        <div class="rounded-xl border ${borderClass} bg-white p-6 shadow-sm transition hover:border-red-600/30 hover:shadow dark:bg-gray-800 dark:hover:border-red-500/50">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="flex-1">
              <div class="flex flex-wrap items-start justify-between gap-2 mb-2">
                <h3 class="text-xl font-semibold dark:text-gray-100 flex min-w-0 flex-1 flex-wrap items-center gap-2">${faviconImg}<span class="min-w-0">${title}</span></h3>
                <div class="flex flex-wrap items-center justify-end gap-2">
                  ${workBadge}
                  ${expiryBadge}
                </div>
              </div>
              <div class="mt-2 flex flex-wrap gap-3 text-sm text-slate-600 dark:text-gray-400">
                ${companySpan}
                ${locationSpan}
                ${typeSpan}
                ${salarySpan}
                ${createdAtSpan}
                ${addedBySpan}
              </div>
              <div class="mt-4">
                <a href="job.html?id=${encodeURIComponent(job.id)}" class="font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                  View Details <i class="fa-solid fa-arrow-right text-xs" aria-hidden="true"></i>
                </a>
              </div>
            </div>
            <div class="flex gap-2">
              <div id="bookmark-${job.id}"></div>
              <a href="https://github.com/OWASP-BLT/BLT-Jobs/blob/main/jobs/${encodeURIComponent(job.id)}.md" target="_blank" rel="noopener" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">
                <i class="fa-brands fa-github" aria-hidden="true"></i> View on GitHub
              </a>
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  jobList.innerHTML = cardsHtml;

  jobs.forEach((job) => {
    const container = document.getElementById(`bookmark-${job.id}`);
    if (container && window.SavedJobs) {
      const button = window.SavedJobs.createButton(job.id, { showLabel: false, size: "md" });
      container.appendChild(button);
    }
  });
}

function applyFilters() {
  const searchInput = document.getElementById("searchInput");
  const typeFilter = document.getElementById("typeFilter");
  const locationFilter = document.getElementById("locationFilter");
  const workModeFilter = document.getElementById("workModeFilter");
  const salaryFilter = document.getElementById("salaryFilter");
  const sortSelect = document.getElementById("sortSelect");

  const q = normalizeString(searchInput?.value);
  const type = (typeFilter?.value || "").toString();
  const location = normalizeString(locationFilter?.value);
  const workMode = (workModeFilter?.value || "").toString();
  const salaryOpt = (salaryFilter?.value || "").toString();
  const sortKey = (sortSelect?.value || "newest").toString();

  const filtered = allJobs.filter((job) => {
    const title = normalizeString(job.title);
    const description = normalizeString(job.description);
    const orgName = normalizeString(job.organization_name);
    const jobLocation = normalizeString(job.location);
    const jobType = (job.job_type || "").toString();

    const matchesSearch =
      !q ||
      title.includes(q) ||
      description.includes(q) ||
      orgName.includes(q) ||
      jobLocation.includes(q);

    const matchesType = !type || jobType === type;

    const matchesLocation = !location || jobLocation.includes(location);

    const mode = inferWorkMode(job);
    const matchesWorkMode = !workMode || mode === workMode;

    const hasSalaryListed = !!(job.salary_range && String(job.salary_range).trim());
    const matchesSalary =
      !salaryOpt || (salaryOpt === "listed" && hasSalaryListed) || (salaryOpt === "none" && !hasSalaryListed);

    return matchesSearch && matchesType && matchesLocation && matchesWorkMode && matchesSalary;
  });

  const sorted = sortJobs(filtered, sortKey);
  renderJobs(sorted);
}

async function loadJobs() {
  try {
    const response = await fetch("data/jobs.json", { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`Failed to load jobs.json: ${response.status}`);
    }
    const data = await response.json();
    allJobs = Array.isArray(data.jobs) ? data.jobs : [];
    applyFilters();
  } catch (error) {
    console.error("Error loading jobs:", error);
    allJobs = [];
    renderJobs([]);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const filtersForm = document.getElementById("filtersForm");
  const searchInput = document.getElementById("searchInput");
  const typeFilter = document.getElementById("typeFilter");
  const locationFilter = document.getElementById("locationFilter");
  const workModeFilter = document.getElementById("workModeFilter");
  const salaryFilter = document.getElementById("salaryFilter");
  const sortSelect = document.getElementById("sortSelect");
  const clearFiltersButton = document.getElementById("clearFiltersButton");

  if (filtersForm) {
    filtersForm.addEventListener("submit", (event) => {
      event.preventDefault();
      applyFilters();
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      applyFilters();
    });
  }

  if (typeFilter) {
    typeFilter.addEventListener("change", () => {
      applyFilters();
    });
  }

  if (locationFilter) {
    locationFilter.addEventListener("input", () => {
      applyFilters();
    });
  }

  if (workModeFilter) {
    workModeFilter.addEventListener("change", () => {
      applyFilters();
    });
  }

  if (salaryFilter) {
    salaryFilter.addEventListener("change", () => {
      applyFilters();
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener("change", () => {
      applyFilters();
    });
  }

  if (clearFiltersButton) {
    clearFiltersButton.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      if (typeFilter) typeFilter.value = "";
      if (locationFilter) locationFilter.value = "";
      if (workModeFilter) workModeFilter.value = "";
      if (salaryFilter) salaryFilter.value = "";
      if (sortSelect) sortSelect.value = "newest";
      applyFilters();
    });
  }

  loadJobs();
});
