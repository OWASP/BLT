let allSeekers = [];

function esc(s) { return window.Sanitize.esc(s); }
function safeUrl(url) { return window.Sanitize.safeUrl(url); }

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
      
      // Extract skills from availability field if skills field is empty (old profiles)
      let skillsText = s.skills || "";
      if (!skillsText && s.availability) {
        const skillsMatch = s.availability.match(/## Skills\s+([^#]+)/);
        if (skillsMatch) {
          skillsText = skillsMatch[1].replace(/<!--.*?-->/g, "").trim();
        }
      }
      
      const skills = skillsText
        .split(/[,;]+/)
        .map((t) => t.trim())
        .filter(Boolean)
        .filter(skill => skill.length > 1 && skill.length < 50); // Filter out junk
      
      const experienceYears = s.experience_years || "";
      let experienceSummary = "";
      if (experienceYears) {
        experienceSummary = `${experienceYears} years experience`;
      } else if (s.experience_summary) {
        experienceSummary = s.experience_summary.split(/##|\n/)[0].trim();
      }
      
      // Clean availability - only show the first word/phrase before any markdown
      let availability = "";
      if (s.availability) {
        availability = s.availability.split(/##/)[0].trim();
        // If it's too long, it's probably junk from old format
        if (availability.length > 50) {
          availability = "";
        }
      }
      
      // Extract links - handle both new format and old profile_url
      const github = s.github || "";
      const linkedin = s.linkedin || (s.profile_url && s.profile_url.includes("linkedin") ? s.profile_url : "");
      const portfolio = s.portfolio || "";
      const email = s.email || "";
      const twitter = s.twitter || "";
      const resumeUrl = s.resume_url || "";
      
      // Build social links
      const socialLinks = [];
      if (safeUrl(linkedin)) socialLinks.push(`<a href="${esc(linkedin)}" target="_blank" rel="noopener" class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600" title="LinkedIn Profile"><i class="fa-brands fa-linkedin" aria-hidden="true"></i></a>`);
      if (safeUrl(github)) socialLinks.push(`<a href="${esc(github)}" target="_blank" rel="noopener" class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600" title="GitHub Profile"><i class="fa-brands fa-github" aria-hidden="true"></i></a>`);
      if (safeUrl(portfolio)) socialLinks.push(`<a href="${esc(portfolio)}" target="_blank" rel="noopener" class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600" title="Portfolio"><i class="fa-solid fa-globe" aria-hidden="true"></i></a>`);
      if (safeUrl(twitter)) socialLinks.push(`<a href="${esc(twitter)}" target="_blank" rel="noopener" class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600" title="Twitter/X"><i class="fa-brands fa-x-twitter" aria-hidden="true"></i></a>`);
      if (safeUrl(resumeUrl)) socialLinks.push(`<a href="${esc(resumeUrl)}" target="_blank" rel="noopener" class="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 transition hover:bg-red-100 dark:border-red-800 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50" title="Download Resume"><i class="fa-solid fa-file-pdf" aria-hidden="true"></i></a>`);
      if (email) socialLinks.push(`<a href="mailto:${esc(email)}" class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600" title="Email"><i class="fa-solid fa-envelope" aria-hidden="true"></i></a>`);

      return `
        <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-red-600/30 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-red-500/50">
          <a href="seeker.html?id=${encodeURIComponent(s.id)}" class="block mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-red-500 to-red-600 text-white text-xl font-bold select-none shadow-lg" aria-hidden="true">
            ${esc(name.split(/\s+/).slice(0, 2).map((w) => w.charAt(0).toUpperCase()).join(""))}
          </a>
          <h3 class="text-lg font-bold text-gray-900 dark:text-gray-100"><a href="seeker.html?id=${encodeURIComponent(s.id)}" class="hover:text-red-600 dark:hover:text-red-400 transition">${esc(name)}</a></h3>
          ${headline ? `<p class="mt-1 text-sm font-medium text-slate-600 dark:text-gray-400">${esc(headline)}</p>` : ""}
          <div class="mt-3 space-y-1.5 text-sm text-slate-600 dark:text-gray-400">
            ${location ? `<div class="flex items-center gap-2"><i class="fa-solid fa-location-dot w-4 text-slate-400 dark:text-gray-500" aria-hidden="true"></i> <span>${esc(location)}</span></div>` : ""}
            ${experienceSummary ? `<div class="flex items-center gap-2"><i class="fa-solid fa-briefcase w-4 text-slate-400 dark:text-gray-500" aria-hidden="true"></i> <span>${esc(experienceSummary)}</span></div>` : ""}
            ${availability ? `<div class="flex items-center gap-2"><i class="fa-solid fa-clock w-4 text-slate-400 dark:text-gray-500" aria-hidden="true"></i> <span>${esc(availability)}</span></div>` : ""}
          </div>
          ${
            skills.length
              ? `
            <div class="mt-4">
              <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide dark:text-gray-500 mb-2">Skills</p>
              <div class="flex flex-wrap gap-1.5">
                ${skills.slice(0, 6).map(skill => `<span class="inline-flex items-center rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 dark:bg-gray-700 dark:text-gray-300">${esc(skill)}</span>`).join("")}
                ${skills.length > 6 ? `<span class="inline-flex items-center rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500 dark:bg-gray-700 dark:text-gray-400">+${skills.length - 6} more</span>` : ""}
              </div>
            </div>
          `
              : ""
          }
          <div class="mt-5 flex flex-wrap gap-2">
            <a href="seeker.html?id=${encodeURIComponent(s.id)}" class="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-red-700"><i class="fa-solid fa-user" aria-hidden="true"></i> View Profile</a>
            ${socialLinks.join("")}
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
