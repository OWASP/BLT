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
    list.classList.add("hidden");
    empty.classList.remove("hidden");
    return;
  }

  list.classList.remove("hidden");
  empty.classList.add("hidden");

  const html = seekers
    .map((s) => {
      const name = s.name || "Anonymous";
      const headline = s.headline || "";
      const location = s.location || "";
      const skills = (s.skills || "")
        .split(/[,;]+/)
        .map((t) => t.trim())
        .filter(Boolean);
      const profileUrl = s.profile_url || "";
      const experienceSummary = s.experience_summary || "";

      return `
        <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-red-600/30 hover:shadow dark:border-gray-700 dark:bg-gray-800 dark:hover:border-red-500/50">
          <a href="seeker.html?id=${s.id}" class="block mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-600 text-white text-xl font-bold select-none" aria-hidden="true">
            ${(name.split(/\s+/).slice(0, 2).map((w) => w.charAt(0).toUpperCase()).join(""))}
          </a>
          <h3 class="text-lg font-semibold dark:text-gray-100"><a href="seeker.html?id=${s.id}" class="hover:text-red-600 dark:hover:text-red-400 transition">${name}</a></h3>
          ${headline ? `<p class="mt-1 text-sm font-medium text-slate-600 dark:text-gray-400">${headline}</p>` : ""}
          <div class="mt-3 space-y-1 text-sm text-slate-600 dark:text-gray-400">
            ${location ? `<div class="flex items-center gap-2"><i class="fa-solid fa-location-dot w-4" aria-hidden="true"></i> ${location}</div>` : ""}
            ${experienceSummary ? `<div class="flex items-center gap-2"><i class="fa-solid fa-briefcase w-4" aria-hidden="true"></i> ${experienceSummary}</div>` : ""}
          </div>
          ${
            skills.length
              ? `
            <div class="mt-3">
              <p class="text-xs font-medium text-slate-500 uppercase dark:text-gray-500">Skills</p>
              <p class="mt-1 text-sm text-slate-600 dark:text-gray-400">${skills.join(", ")}</p>
            </div>
          `
              : ""
          }
          <div class="mt-4 flex gap-2">
            <a href="seeker.html?id=${s.id}" class="inline-flex items-center gap-1 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-red-700"><i class="fa-solid fa-user" aria-hidden="true"></i> View Profile</a>
            ${profileUrl ? `<a href="${profileUrl}" target="_blank" rel="noopener" class="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"><i class="fa-brands fa-linkedin" aria-hidden="true"></i> LinkedIn</a>` : ""}
          </div>
        </div>
      `;
    })
    .join("");

  list.innerHTML = html;
}

function applyFilters() {
  const searchInput = document.getElementById("searchInput");
  if (!searchInput) return;

  const q = normalizeSeekerString(searchInput.value);

  const filtered = allSeekers.filter((seeker) => {
    const name = normalizeSeekerString(seeker.name);
    const headline = normalizeSeekerString(seeker.headline);
    const location = normalizeSeekerString(seeker.location);
    const skills = normalizeSeekerString(seeker.skills);
    const about = normalizeSeekerString(seeker.about);

    return (
      !q ||
      name.includes(q) ||
      headline.includes(q) ||
      location.includes(q) ||
      skills.includes(q) ||
      about.includes(q)
    );
  });

  renderSeekers(filtered);
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
    applyFilters();
  } catch (err) {
    console.error("Error loading seekers:", err);
    allSeekers = [];
    renderSeekers([]);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadSeekers();

  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", applyFilters);
  }
});
