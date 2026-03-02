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

  // Extract embedded sections from the availability field (old format)
  const skillsMatch = availability.match(/##\s+Skills\s*([\s\S]*?)(?=\s*##|$)/i);
  const aboutMatch = availability.match(/##\s+About\s+Me\s*([\s\S]*?)(?=\s*##|$)/i);
  const expMatch = availability.match(/##\s+Experience\s+Highlights?\s*([\s\S]*?)(?=\s*##|$)/i);
  const lookingForMatch = availability.match(/##\s+What\s+I['\u2019]m\s+Looking\s+For\s*([\s\S]*?)(?=\s*##|$)/i);

  // Extract sections from body (new format)
  const bodyAboutMatch = aboutBody.match(/##\s+About\s+Me\s*([\s\S]*?)(?=\s*##|$)/i);
  const bodyWorkExpMatch = aboutBody.match(/##\s+Work\s+Experience\s*([\s\S]*?)(?=\s*##|$)/i);
  const bodyProjectsMatch = aboutBody.match(/##\s+Projects\s+&\s+Portfolio\s*([\s\S]*?)(?=\s*##|$)/i);
  const bodyCertsMatch = aboutBody.match(/##\s+Certifications\s+&\s+Education\s*([\s\S]*?)(?=\s*##|$)/i);
  const bodyWorkSamplesMatch = aboutBody.match(/##\s+Work\s+Samples\s*([\s\S]*?)(?=\s*##|$)/i);
  const bodyLookingForMatch = aboutBody.match(/##\s+What\s+I['\u2019]m\s+Looking\s+For\s*([\s\S]*?)(?=\s*##|$)/i);

  // Skills: frontmatter first, then embedded section
  let skills = (seeker.skills || "").trim();
  if (!skills && skillsMatch) {
    skills = stripHtmlComments(skillsMatch[1]);
  }

  // About: new format first, then old format, then body
  let about = "";
  if (bodyAboutMatch) {
    about = stripHtmlComments(bodyAboutMatch[1]);
  } else if (aboutMatch) {
    about = stripHtmlComments(aboutMatch[1]);
  } else if (aboutBody && aboutBody !== "Profile created via issue." && !aboutBody.includes("##")) {
    about = aboutBody;
  }

  // Work Experience: new format first, then old experience highlights
  let workExperience = "";
  if (bodyWorkExpMatch) {
    workExperience = stripHtmlComments(bodyWorkExpMatch[1]);
  } else if (expMatch) {
    workExperience = stripHtmlComments(expMatch[1]);
  }

  // Projects & Portfolio
  let projects = "";
  if (bodyProjectsMatch) {
    projects = stripHtmlComments(bodyProjectsMatch[1]);
  }

  // Certifications & Education
  let certifications = "";
  if (bodyCertsMatch) {
    certifications = stripHtmlComments(bodyCertsMatch[1]);
  }

  // Work Samples
  let workSamples = "";
  if (bodyWorkSamplesMatch) {
    workSamples = stripHtmlComments(bodyWorkSamplesMatch[1]);
  }

  // "What I'm looking for": new format first, then old format
  let lookingFor = "";
  if (bodyLookingForMatch) {
    lookingFor = stripHtmlComments(bodyLookingForMatch[1]);
  } else if (lookingForMatch) {
    lookingFor = stripHtmlComments(lookingForMatch[1]);
  }

  return { 
    availabilityStatus, 
    skills, 
    about, 
    workExperience, 
    projects, 
    certifications, 
    workSamples, 
    lookingFor 
  };
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
  const experienceSummary = seeker.experience_summary || "";
  const createdAtRaw = seeker.created_at || "";
  const createdAt = createdAtRaw
    ? new Date(createdAtRaw).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })
    : "";

  // Get all contact links
  const github = seeker.github || "";
  const linkedin = seeker.linkedin || (seeker.profile_url && seeker.profile_url.includes("linkedin") ? seeker.profile_url : "");
  const portfolio = seeker.portfolio || "";
  const email = seeker.email || "";
  const twitter = seeker.twitter || "";
  const resumeUrl = seeker.resume_url || "";

  const { availabilityStatus, skills, about, workExperience, projects, certifications, workSamples, lookingFor } = parseSeekerContent(seeker);
  const initials = getInitials(name);
  const skillBadges = renderSkillBadges(skills);

  // Build contact links
  const contactLinks = [];
  if (linkedin) contactLinks.push(`<a href="${linkedin}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"><i class="fa-brands fa-linkedin" aria-hidden="true"></i> LinkedIn</a>`);
  if (github) contactLinks.push(`<a href="${github}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 transition hover:bg-gray-50 dark:hover:bg-gray-700"><i class="fa-brands fa-github" aria-hidden="true"></i> GitHub</a>`);
  if (portfolio) contactLinks.push(`<a href="${portfolio}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 transition hover:bg-gray-50 dark:hover:bg-gray-700"><i class="fa-solid fa-globe" aria-hidden="true"></i> Portfolio</a>`);
  if (twitter) contactLinks.push(`<a href="${twitter}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 transition hover:bg-gray-50 dark:hover:bg-gray-700"><i class="fa-brands fa-x-twitter" aria-hidden="true"></i> Twitter</a>`);
  if (resumeUrl) contactLinks.push(`<a href="${resumeUrl}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700"><i class="fa-solid fa-file-pdf" aria-hidden="true"></i> Resume</a>`);
  if (email) contactLinks.push(`<a href="mailto:${email}" class="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 transition hover:bg-gray-50 dark:hover:bg-gray-700"><i class="fa-solid fa-envelope" aria-hidden="true"></i> Email</a>`);

  document.title = `${name} — BLT Jobs`;

  root.innerHTML = `
    <div class="min-h-screen">
      <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div class="space-y-6">

          <!-- Profile Header Card -->
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8">
            <div class="flex flex-col sm:flex-row items-start sm:items-center gap-6">
              <!-- Avatar -->
              <div class="flex-shrink-0 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-red-500 to-red-600 text-white text-2xl font-bold select-none shadow-lg" aria-hidden="true">
                ${initials}
              </div>
              <!-- Name & Meta -->
              <div class="flex-1 min-w-0">
                <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">${name}</h1>
                ${headline ? `<p class="mt-1 text-lg font-medium text-red-600 dark:text-red-400">${headline}</p>` : ""}
                <div class="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-gray-600 dark:text-gray-400">
                  ${location ? `<span class="flex items-center gap-1.5"><i class="fa-solid fa-location-dot text-gray-400" aria-hidden="true"></i> ${location}</span>` : ""}
                  ${experienceSummary ? `<span class="flex items-center gap-1.5"><i class="fa-solid fa-briefcase text-gray-400" aria-hidden="true"></i> ${experienceSummary}</span>` : ""}
                  ${availabilityStatus ? `<span class="flex items-center gap-1.5"><i class="fa-solid fa-circle-check text-green-500" aria-hidden="true"></i> ${availabilityStatus}</span>` : ""}
                  ${createdAt ? `<span class="flex items-center gap-1.5"><i class="fa-solid fa-calendar text-gray-400" aria-hidden="true"></i> Joined ${createdAt}</span>` : ""}
                </div>
              </div>
            </div>

            <!-- Contact Links -->
            ${
              contactLinks.length > 0
                ? `<div class="mt-6 flex flex-wrap gap-3">
                     ${contactLinks.join("")}
                   </div>`
                : ""
            }
          </div>

          <!-- Skills Card -->
          ${
            skillBadges
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
                     <i class="fa-solid fa-code text-red-600 dark:text-red-400" aria-hidden="true"></i>
                     Skills
                   </h2>
                   <div class="flex flex-wrap gap-2">${skillBadges}</div>
                 </div>`
              : ""
          }

          <!-- About Me Card -->
          ${
            about
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
                     <i class="fa-solid fa-user text-red-600 dark:text-red-400" aria-hidden="true"></i>
                     About Me
                   </h2>
                   <div class="profile-content">
                     ${renderMarkdown(about)}
                   </div>
                 </div>`
              : ""
          }

          <!-- Work Experience Card -->
          ${
            workExperience
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
                     <i class="fa-solid fa-briefcase text-red-600 dark:text-red-400" aria-hidden="true"></i>
                     Work Experience
                   </h2>
                   <div class="profile-content">
                     ${renderMarkdown(workExperience)}
                   </div>
                 </div>`
              : ""
          }

          <!-- Projects & Portfolio Card -->
          ${
            projects
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
                     <i class="fa-solid fa-folder-open text-red-600 dark:text-red-400" aria-hidden="true"></i>
                     Projects & Portfolio
                   </h2>
                   <div class="profile-content">
                     ${renderMarkdown(projects)}
                   </div>
                 </div>`
              : ""
          }

          <!-- Certifications & Education Card -->
          ${
            certifications
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
                     <i class="fa-solid fa-graduation-cap text-red-600 dark:text-red-400" aria-hidden="true"></i>
                     Certifications & Education
                   </h2>
                   <div class="profile-content">
                     ${renderMarkdown(certifications)}
                   </div>
                 </div>`
              : ""
          }

          <!-- Work Samples Card -->
          ${
            workSamples
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
                     <i class="fa-solid fa-file-lines text-red-600 dark:text-red-400" aria-hidden="true"></i>
                     Work Samples
                   </h2>
                   <div class="profile-content">
                     ${renderMarkdown(workSamples)}
                   </div>
                 </div>`
              : ""
          }

          <!-- Looking For Card -->
          ${
            lookingFor
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                   <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
                     <i class="fa-solid fa-bullseye text-red-600 dark:text-red-400" aria-hidden="true"></i>
                     What I'm Looking For
                   </h2>
                   <div class="profile-content">
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
