let allJobs = [];

function normalizeString(value) {
  return (value || "").toString().toLowerCase();
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
    emptyStateMessage.textContent =
      document.getElementById("searchInput").value ||
      document.getElementById("typeFilter").value ||
      document.getElementById("locationFilter").value
        ? "Try adjusting your search terms or filters"
        : "Check back later for new opportunities";

    const anyFilterActive =
      document.getElementById("searchInput").value ||
      document.getElementById("typeFilter").value ||
      document.getElementById("locationFilter").value;

    if (anyFilterActive) {
      clearFiltersButton.classList.remove("hidden");
    } else {
      clearFiltersButton.classList.add("hidden");
    }

    return;
  }

  resultsSummary.classList.remove("hidden");
  emptyState.classList.add("hidden");

  resultsCount.textContent = jobs.length.toString();
  resultsLabel.textContent = jobs.length === 1 ? " job found" : " jobs found";

  const cardsHtml = jobs
    .map((job) => {
      const title = job.title || "Untitled";
      const company = job.organization_name || "";
      const location = job.location || "";
      const jobType = job.job_type || "";
      const addedBy = job.added_by || "";

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
      const addedBySpan = addedBy
        ? `<span class="flex items-center gap-1"><i class="fa-solid fa-user" aria-hidden="true"></i> Added by <a href="https://github.com/${addedBy}" target="_blank" rel="noopener noreferrer" class="font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">@${addedBy}</a></span>`
        : "";

      return `
        <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-red-600/30 hover:shadow dark:border-gray-700 dark:bg-gray-800 dark:hover:border-red-500/50">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="flex-1">
              <h3 class="text-xl font-semibold dark:text-gray-100">${faviconImg}${title}</h3>
              <div class="mt-2 flex flex-wrap gap-3 text-sm text-slate-600 dark:text-gray-400">
                ${companySpan}
                ${locationSpan}
                ${typeSpan}
                ${addedBySpan}
              </div>
              <div class="mt-4">
                <a href="job.html?id=${encodeURIComponent(job.id)}" class="font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                  View Details <i class="fa-solid fa-arrow-right text-xs" aria-hidden="true"></i>
                </a>
              </div>
            </div>
            <a href="https://github.com/OWASP-BLT/BLT-Jobs/blob/main/jobs/${encodeURIComponent(job.id)}.md" target="_blank" rel="noopener" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">
              <i class="fa-brands fa-github" aria-hidden="true"></i> View on GitHub
            </a>
          </div>
        </div>
      `;
    })
    .join("");

  jobList.innerHTML = cardsHtml;
}

function applyFilters() {
  const searchInput = document.getElementById("searchInput");
  const typeFilter = document.getElementById("typeFilter");
  const locationFilter = document.getElementById("locationFilter");

  const q = normalizeString(searchInput.value);
  const type = (typeFilter.value || "").toString();
  const location = normalizeString(locationFilter.value);

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

    return matchesSearch && matchesType && matchesLocation;
  });

  renderJobs(filtered);
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
    // If jobs cannot be loaded, show empty state
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

  if (clearFiltersButton) {
    clearFiltersButton.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      if (typeFilter) typeFilter.value = "";
      if (locationFilter) locationFilter.value = "";
      applyFilters();
    });
  }

  loadJobs();
});

