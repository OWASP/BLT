let allJobs = [];

function normalizeString(value) {
  return (value || "").toString().toLowerCase();
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
      const orgName = job.organization_name || "Unknown organization";
      const orgLogo = job.organization_logo || "";
      const orgInitial = orgName.charAt(0).toUpperCase();
      const location = job.location || "";
      const jobType = job.job_type || "";
      const salary = job.salary_range || "";
      const createdAt = job.created_at || "";
      const expired = isExpired(job.expires_at);
      const expiringSoon = isExpiringSoon(job.expires_at);
      const expiryText = formatExpiryDate(job.expires_at);

      return `
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border ${
          expired
            ? "border-gray-300 dark:border-gray-600 opacity-60"
            : expiringSoon
            ? "border-orange-300 dark:border-orange-700"
            : "border-gray-200 dark:border-gray-700"
        } hover:shadow-md transition-all duration-200 p-6 hover:border-gray-300 dark:hover:border-gray-600">
          <div class="flex flex-col lg:flex-row justify-between items-start gap-6">
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-3">
                ${
                  orgLogo
                    ? `<img src="${orgLogo}"
                             alt="${orgName}"
                             width="48"
                             height="48"
                             class="w-12 h-12 rounded-lg object-cover border border-gray-200 dark:border-gray-600" />`
                    : `<div class="w-12 h-12 bg-[#e74c3c] rounded-lg flex items-center justify-center border border-gray-200 dark:border-gray-600">
                         <span class="text-white font-bold text-lg">${orgInitial}</span>
                       </div>`
                }
                <div>
                  <p class="text-sm text-gray-600 dark:text-gray-400">${orgName}</p>
                </div>
              </div>

              <div class="flex items-start justify-between gap-2 mb-2">
                <h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 flex-1">
                  <a href="job.html?id=${encodeURIComponent(job.id)}"
                     class="hover:text-[#e74c3c] dark:hover:text-[#f8c471] transition-colors duration-200">
                    ${job.title || "Untitled job"}
                  </a>
                </h2>
                ${
                  expired
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
                         ${expiryText}
                       </span>`
                    : ""
                }
              </div>

              <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-gray-600 dark:text-gray-400 mb-3">
                ${
                  location
                    ? `<span class="flex items-center gap-1">
                         <svg class="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
                         </svg>
                         ${location}
                       </span>`
                    : ""
                }
                ${
                  jobType
                    ? `<span class="flex items-center gap-1">
                         <svg class="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                         </svg>
                         ${jobType}
                       </span>`
                    : ""
                }
                ${
                  salary
                    ? `<span class="flex items-center gap-1">
                         <svg class="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                         </svg>
                         ${salary}
                       </span>`
                    : ""
                }
                ${
                  createdAt
                    ? `<span class="flex items-center gap-1 text-gray-500 dark:text-gray-500">
                         <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                         </svg>
                         Posted ${createdAt}
                       </span>`
                    : ""
                }
              </div>

              <p class="text-gray-700 dark:text-gray-300 line-clamp-2">
                ${job.description ? job.description : ""}
              </p>
            </div>
            <div class="flex-shrink-0 mt-4 lg:mt-0">
              <a
                href="job.html?id=${encodeURIComponent(job.id)}"
                class="inline-flex items-center px-6 py-2.5 bg-[#e74c3c] text-white rounded-lg font-semibold hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#e74c3c] transition-all duration-200 transform hover:scale-105"
              >
                View Details
                <svg
                  class="w-4 h-4 ml-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M14 5l7 7m0 0l-7 7m7-7H3"
                  ></path>
                </svg>
              </a>
            </div>
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

