let allSeekers = [];

function normalizeSeekerString(value) {
  return (value || "").toString().toLowerCase();
}

function renderSeekers(seekers) {
  const list = document.getElementById("seekersList");
  const empty = document.getElementById("seekersEmpty");
  if (!list || !empty) return;

  list.innerHTML = "";

  if (!seekers || seekers.length === 0) {
    empty.classList.remove("hidden");
    return;
  }

  empty.classList.add("hidden");

  const html = seekers
    .map((s) => {
      const name = s.name || "Anonymous";
      const headline = s.headline || "";
      const location = s.location || "";
      const skills = (s.skills || "").split(/[,;]+/).map((t) => t.trim()).filter(Boolean);
      const profileUrl = s.profile_url || "";
      const availability = s.availability || "";

      const initial = name.trim().charAt(0).toUpperCase() || "?";

      return `
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div class="flex items-start gap-4">
            <div class="w-12 h-12 rounded-full bg-[#e74c3c] flex items-center justify-center text-white font-semibold text-lg flex-shrink-0">
              ${initial}
            </div>
            <div>
              <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">${name}</h2>
              ${headline ? `<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">${headline}</p>` : ""}
              <div class="flex flex-wrap items-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400">
                ${location ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700">
                  <i class="fa-solid fa-location-dot text-[10px]"></i>
                  <span>${location}</span>
                </span>` : ""}
                ${availability ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200">
                  <i class="fa-solid fa-circle-check text-[10px]"></i>
                  <span>${availability}</span>
                </span>` : ""}
              </div>
              ${skills.length ? `
                <div class="mt-3 flex flex-wrap gap-1">
                  ${skills
                    .map(
                      (skill) =>
                        `<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-xs text-gray-700 dark:text-gray-200">${skill}</span>`
                    )
                    .join("")}
                </div>
              ` : ""}
            </div>
          </div>
          <div class="flex-shrink-0">
            ${
              profileUrl
                ? `<a href="${profileUrl}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-4 py-2 border-2 border-[#e74c3c] text-[#e74c3c] rounded-lg font-semibold hover:bg-[#e74c3c] hover:text-white dark:border-[#e74c3c] dark:text-[#e74c3c] dark:hover:bg-red-600 dark:hover:text-white transition-colors">
                     <i class="fa-solid fa-user mr-2"></i>
                     View profile
                   </a>`
                : ""
            }
          </div>
        </div>
      `;
    })
    .join("\n");

  list.innerHTML = html;
}

async function loadSeekers() {
  const list = document.getElementById("seekersList");
  const empty = document.getElementById("seekersEmpty");
  if (!list || !empty) return;

  try {
    const res = await fetch("data/seekers.json", { cache: "no-cache" });
    if (!res.ok) {
      throw new Error(`Failed to load seekers.json: ${res.status}`);
    }
    const data = await res.json();
    allSeekers = Array.isArray(data.seekers) ? data.seekers : [];
    renderSeekers(allSeekers);
  } catch (err) {
    console.error("Error loading seekers:", err);
    allSeekers = [];
    renderSeekers([]);
  }
}

document.addEventListener("DOMContentLoaded", loadSeekers);

