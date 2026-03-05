/**
 * Saved Jobs Page Logic
 */

let allJobs = [];

function normalizeString(value) {
  return (value || "").toString().toLowerCase();
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

function renderSavedJobs() {
  const savedJobsList = document.getElementById("savedJobsList");
  const emptyState = document.getElementById("emptyState");
  const countNumber = document.getElementById("countNumber");
  const clearAllButton = document.getElementById("clearAllButton");

  if (!savedJobsList || !emptyState || !countNumber) return;

  const savedIds = SavedJobs.getAll();
  const savedJobs = allJobs.filter((job) => savedIds.includes(job.id));

  countNumber.textContent = savedJobs.length;

  if (savedJobs.length === 0) {
    savedJobsList.innerHTML = "";
    emptyState.classList.remove("hidden");
    clearAllButton.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  clearAllButton.classList.remove("hidden");

  const cardsHtml = savedJobs
    .map((job) => {
      const title = job.title || "Untitled";
      const company = job.organization_name || "";
      const location = job.location || "";
      const jobType = job.job_type || "";
      const salary = job.salary_range || "";
      const createdAt = job.created_at || "";
      
      const expired = isExpired(job.expires_at);
      const expiringSoon = isExpiringSoon(job.expires_at);
      const expiryText = formatExpiryDate(job.expires_at);

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
             ${expiryText}
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
              <div class="flex items-start justify-between gap-2 mb-2">
                <h3 class="text-xl font-semibold dark:text-gray-100 flex-1">${faviconImg}${title}</h3>
                ${expiryBadge}
              </div>
              <div class="mt-2 flex flex-wrap gap-3 text-sm text-slate-600 dark:text-gray-400">
                ${companySpan}
                ${locationSpan}
                ${typeSpan}
                ${salarySpan}
                ${createdAtSpan}
              </div>
              <div class="mt-4 flex flex-wrap gap-3">
                <a href="job.html?id=${encodeURIComponent(job.id)}" class="font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                  View Details <i class="fa-solid fa-arrow-right text-xs" aria-hidden="true"></i>
                </a>
              </div>
            </div>
            <div class="flex gap-2">
              <div id="bookmark-${job.id}"></div>
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  savedJobsList.innerHTML = cardsHtml;

  // Add bookmark buttons
  savedJobs.forEach((job) => {
    const container = document.getElementById(`bookmark-${job.id}`);
    if (container) {
      const button = SavedJobs.createButton(job.id, { showLabel: false, size: "md" });
      container.appendChild(button);
    }
  });
}

async function loadJobs() {
  try {
    const response = await fetch("data/jobs.json", { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`Failed to load jobs.json: ${response.status}`);
    }
    const data = await response.json();
    allJobs = Array.isArray(data.jobs) ? data.jobs : [];
    renderSavedJobs();
  } catch (error) {
    console.error("Error loading jobs:", error);
    allJobs = [];
    renderSavedJobs();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const clearAllButton = document.getElementById("clearAllButton");

  if (clearAllButton) {
    clearAllButton.addEventListener("click", () => {
      if (confirm("Are you sure you want to remove all saved jobs?")) {
        SavedJobs.clear();
        renderSavedJobs();
      }
    });
  }

  // Listen for saved jobs changes
  window.addEventListener("savedJobsChanged", () => {
    renderSavedJobs();
  });

  loadJobs();
});
