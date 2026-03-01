function stripHtmlComments(str) {
  if (!str) return "";
  // Remove complete HTML comments, then strip any unclosed comment opener
  return str.replace(/<!--[\s\S]*?-->/g, "").replace(/<!--[\s\S]*/g, "").trim();
}

function parseSeekerContent(seeker) {
  const availability = seeker.availability || "";
  const aboutBody = seeker.about || "";

  // Extract availability status (text before first ## heading)
  const firstHashIdx = availability.search(/##\s/);
  const availabilityStatus =
    firstHashIdx === -1 ? availability.trim() : availability.slice(0, firstHashIdx).trim();

  // Extract embedded sections from the availability field
  const skillsMatch = availability.match(/##\s+Skills\s*([\s\S]*?)(?=\s*##|$)/i);
  const aboutMatch = availability.match(/##\s+About\s+Me\s*([\s\S]*?)(?=\s*##|$)/i);
  const expMatch = availability.match(/##\s+Experience\s+Highlights?\s*([\s\S]*?)(?=\s*##|$)/i);
  // Match both straight apostrophe (') and right-single-quotation-mark (\u2019)
  const lookingForMatch = availability.match(/##\s+What\s+I['\u2019]m\s+Looking\s+For\s*([\s\S]*?)(?=\s*##|$)/i);

  // Skills: frontmatter first, then embedded section
  let skills = (seeker.skills || "").trim();
  if (!skills && skillsMatch) {
    skills = stripHtmlComments(skillsMatch[1]);
  }

  // About: embedded section first, then body (skip placeholder)
  let about = "";
  if (aboutMatch) {
    about = stripHtmlComments(aboutMatch[1]);
  }
  if (!about && aboutBody && aboutBody !== "Profile created via issue.") {
    about = aboutBody;
  }

  // Experience highlights from embedded section
  let experience = "";
  if (expMatch) {
    experience = stripHtmlComments(expMatch[1]);
  }

  // "What I'm looking for" from embedded section
  let lookingFor = "";
  if (lookingForMatch) {
    lookingFor = stripHtmlComments(lookingForMatch[1]);
  }

  return { availabilityStatus, skills, about, experience, lookingFor };
}

function getInitials(name) {
  return (name || "?")
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w.charAt(0).toUpperCase())
    .join("");
}

function renderMarkdown(text) {
  if (!text) return "";
  if (typeof marked !== "undefined") {
    return marked.parse(text);
  }
  return text.replace(/\n/g, "<br />");
}

function renderSkillBadges(skillsStr) {
  if (!skillsStr) return "";
  const skills = skillsStr
    .split(/[,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (!skills.length) return "";
  return skills
    .map(
      (s) =>
        `<span class="inline-block rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300">${s}</span>`
    )
    .join(" ");
}

function renderNotFound() {
  const root = document.getElementById("seekerRoot");
  if (!root) return;
  root.innerHTML = `
    <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 text-center">
          <i class="fa-solid fa-user-slash text-4xl text-gray-300 dark:text-gray-600 mb-4" aria-hidden="true"></i>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">Profile not found</h1>
          <p class="text-gray-600 dark:text-gray-400 mb-6">
            This profile may have been removed or does not exist.
          </p>
          <a href="seekers.html"
             class="inline-flex items-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-xl font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
            </svg>
            Back to Seekers
          </a>
        </div>
      </div>
    </div>
  `;
}

function renderSeeker(seeker) {
  const root = document.getElementById("seekerRoot");
  if (!root) return;

  const name = seeker.name || "Anonymous";
  const headline = seeker.headline || "";
  const location = seeker.location || "";
  const profileUrl = seeker.profile_url || "";
  const experienceSummary = seeker.experience_summary || "";
  const createdAtRaw = seeker.created_at || "";
  const createdAt = createdAtRaw
    ? new Date(createdAtRaw).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })
    : "";

  const { availabilityStatus, skills, about, experience, lookingFor } = parseSeekerContent(seeker);
  const initials = getInitials(name);
  const skillBadges = renderSkillBadges(skills);

  // Determine LinkedIn vs GitHub icon using proper hostname parsing
  let profileHostname = "";
  try { profileHostname = new URL(profileUrl).hostname.toLowerCase(); } catch (e) {}
  const isLinkedIn = profileHostname === "linkedin.com" || profileHostname.endsWith(".linkedin.com");
  const isGitHub = profileHostname === "github.com" || profileHostname.endsWith(".github.com");
  const profileLinkIcon = isLinkedIn
    ? `<i class="fa-brands fa-linkedin" aria-hidden="true"></i>`
    : isGitHub
    ? `<i class="fa-brands fa-github" aria-hidden="true"></i>`
    : `<i class="fa-solid fa-link" aria-hidden="true"></i>`;
  const profileLinkLabel = isLinkedIn ? "LinkedIn" : isGitHub ? "GitHub" : "Profile";

  document.title = `${name} — BLT Jobs`;

  root.innerHTML = `
    <div class="min-h-screen">
      <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div class="space-y-6">

          <!-- Profile Header Card -->
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8">
            <div class="flex flex-col sm:flex-row items-start sm:items-center gap-6">
              <!-- Avatar -->
              <div class="flex-shrink-0 flex h-20 w-20 items-center justify-center rounded-full bg-red-600 text-white text-2xl font-bold select-none" aria-hidden="true">
                ${initials}
              </div>
              <!-- Name & Meta -->
              <div class="flex-1 min-w-0">
                <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">${name}</h1>
                ${headline ? `<p class="mt-1 text-lg font-medium text-red-600 dark:text-red-400">${headline}</p>` : ""}
                <div class="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-gray-600 dark:text-gray-400">
                  ${location ? `<span class="flex items-center gap-1.5"><i class="fa-solid fa-location-dot text-gray-400" aria-hidden="true"></i> ${location}</span>` : ""}
                  ${experienceSummary ? `<span class="flex items-center gap-1.5"><i class="fa-solid fa-briefcase text-gray-400" aria-hidden="true"></i> ${experienceSummary}</span>` : ""}
                  ${availabilityStatus ? `<span class="flex items-center gap-1.5"><i class="fa-solid fa-circle-check text-green-500" aria-hidden="true"></i> Available: ${availabilityStatus}</span>` : ""}
                  ${createdAt ? `<span class="flex items-center gap-1.5"><i class="fa-solid fa-calendar text-gray-400" aria-hidden="true"></i> Joined ${createdAt}</span>` : ""}
                </div>
              </div>
            </div>

            <!-- Action Links -->
            ${
              profileUrl
                ? `<div class="mt-6 flex flex-wrap gap-3">
                     <a href="${profileUrl}" target="_blank" rel="noopener noreferrer"
                        class="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700">
                       ${profileLinkIcon} ${profileLinkLabel}
                     </a>
                   </div>`
                : ""
            }
          </div>

          <!-- Skills Card -->
          ${
            skillBadges
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Skills</h2>
                   <div class="flex flex-wrap gap-2">${skillBadges}</div>
                 </div>`
              : ""
          }

          <!-- About Me Card -->
          ${
            about
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">About Me</h2>
                   <div class="prose max-w-none text-gray-700 dark:text-gray-300 prose-a:text-red-600 prose-a:dark:text-red-400">
                     ${renderMarkdown(about)}
                   </div>
                 </div>`
              : ""
          }

          <!-- Experience Highlights Card -->
          ${
            experience
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Experience Highlights</h2>
                   <div class="prose max-w-none text-gray-700 dark:text-gray-300 prose-a:text-red-600 prose-a:dark:text-red-400">
                     ${renderMarkdown(experience)}
                   </div>
                 </div>`
              : ""
          }

          <!-- Looking For Card -->
          ${
            lookingFor
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">What I'm Looking For</h2>
                   <div class="prose max-w-none text-gray-700 dark:text-gray-300 prose-a:text-red-600 prose-a:dark:text-red-400">
                     ${renderMarkdown(lookingFor)}
                   </div>
                 </div>`
              : ""
          }

          <!-- Back Button -->
          <div>
            <a href="seekers.html"
               class="inline-flex items-center gap-2 rounded-xl border border-gray-300 dark:border-gray-600 px-6 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 transition hover:bg-gray-50 dark:hover:bg-gray-700">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
              </svg>
              Back to Seekers
            </a>
          </div>

        </div>
      </div>
    </div>
  `;
}

function initSeekerDetail() {
  const params = new URLSearchParams(window.location.search);
  const idParam = params.get("id");

  if (!idParam) {
    renderNotFound();
    return;
  }

  fetch("data/seekers.json", { cache: "no-cache" })
    .then((res) => {
      if (!res.ok) throw new Error("Failed to load seekers.json");
      return res.json();
    })
    .then((data) => {
      const seekers = Array.isArray(data.seekers) ? data.seekers : [];
      const seeker = seekers.find((s) => String(s.id) === String(idParam));
      if (!seeker) {
        renderNotFound();
        return;
      }
      renderSeeker(seeker);
    })
    .catch((err) => {
      console.error("Error loading seeker details:", err);
      renderNotFound();
    });
}

document.addEventListener("DOMContentLoaded", initSeekerDetail);
