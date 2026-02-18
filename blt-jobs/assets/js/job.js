function normalizeString(value) {
  return (value || "").toString().trim();
}

function renderNotFound() {
  const root = document.getElementById("jobRoot");
  if (!root) return;

  root.innerHTML = `
    <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 text-center">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">Job not found</h1>
          <p class="text-gray-600 dark:text-gray-400 mb-6">
            The job you are looking for may have been removed or is no longer available.
          </p>
          <a
            href="jobs.html"
            class="inline-flex items-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-xl font-medium hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-all duration-200 transform hover:scale-105"
          >
            <svg
              class="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              ></path>
            </svg>
            Back to All Jobs
          </a>
        </div>
      </div>
    </div>
  `;
}

function renderJob(job) {
  const root = document.getElementById("jobRoot");
  if (!root) return;

  const orgName = job.organization_name || "Unknown organization";
  const orgLogo = job.organization_logo || "";
  const orgInitial = orgName.charAt(0).toUpperCase();
  const location = job.location || "";
  const jobType = job.job_type || "";
  const salary = job.salary_range || "";
  const createdAt = job.created_at || "";
  const canApply = Boolean(job.application_email || job.application_url);
  const hasEmail = Boolean(job.application_email);
  const hasUrl = Boolean(job.application_url);
  const description = job.description || "";
  const requirements = job.requirements || "";
  const applicationInstructions = job.application_instructions || "";

  root.innerHTML = `
    <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div class="space-y-8">
          <!-- Job Header Card -->
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 transition-colors duration-200">
            <!-- Company Info -->
            <div class="flex items-center gap-4 mb-6">
              ${
                orgLogo
                  ? `<img src="${orgLogo}"
                           alt="${orgName}"
                           width="64"
                           height="64"
                           class="w-16 h-16 rounded-lg object-cover border border-gray-200 dark:border-gray-600" />`
                  : `<div class="w-16 h-16 bg-[#e74c3c] rounded-lg flex items-center justify-center border border-gray-200 dark:border-gray-600">
                       <span class="text-white font-bold text-2xl">${orgInitial}</span>
                     </div>`
              }
              <div>
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">${orgName}</h2>
              </div>
            </div>

            <!-- Job Title -->
            <h1 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">
              ${job.title || "Untitled job"}
            </h1>

            <!-- Job Meta Info -->
            <div class="flex flex-wrap items-center gap-6 text-gray-700 dark:text-gray-300 mb-8">
              ${
                location
                  ? `<div class="flex items-center gap-2">
                       <svg class="w-5 h-5 text-gray-500 dark:text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
                       </svg>
                       <span class="font-medium">${location}</span>
                     </div>`
                  : ""
              }
              ${
                jobType
                  ? `<div class="flex items-center gap-2">
                       <svg class="w-5 h-5 text-gray-500 dark:text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                       </svg>
                       <span class="font-medium">${jobType}</span>
                     </div>`
                  : ""
              }
              ${
                salary
                  ? `<div class="flex items-center gap-2">
                       <svg class="w-5 h-5 text-gray-500 dark:text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                       </svg>
                       <span class="font-medium">${salary}</span>
                     </div>`
                  : ""
              }
              ${
                createdAt
                  ? `<div class="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                       <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                       </svg>
                       <span>Posted ${createdAt}</span>
                     </div>`
                  : ""
              }
            </div>

            <!-- Apply Buttons -->
            ${
              canApply
                ? `<div class="flex flex-wrap gap-4">
                     ${
                       hasEmail
                         ? `<a href="mailto:${job.application_email}"
                                class="inline-flex items-center px-8 py-3 bg-[#e74c3c] text-white rounded-xl font-medium hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#e74c3c] transition-all duration-200 transform hover:scale-105">
                               <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                               </svg>
                               Apply via Email
                             </a>`
                         : ""
                     }
                     ${
                       hasUrl
                         ? `<a href="${job.application_url}"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="inline-flex items-center px-8 py-3 bg-[#e74c3c] text-white rounded-xl font-medium hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#e74c3c] transition-all duration-200 transform hover:scale-105">
                               <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                               </svg>
                               Apply on Company Website
                             </a>`
                         : ""
                     }
                   </div>`
                : `<div class="inline-flex items-center px-6 py-3 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-xl font-medium border border-gray-200 dark:border-gray-600">
                     <svg class="w-5 h-5 mr-2"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                     </svg>
                     Applications Closed
                   </div>`
            }
          </div>

          <!-- Job Description -->
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 transition-colors duration-200">
            <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">Job Description</h3>
            <div class="prose max-w-none text-gray-700 dark:text-gray-300 prose-headings:text-gray-900 prose-headings:dark:text-gray-100 prose-strong:text-gray-900 prose-strong:dark:text-gray-100 prose-a:text-[#e74c3c] prose-a:dark:text-[#e74c3c] prose-a:hover:text-red-700 prose-a:dark:hover:text-[#f8c471] prose-ul:text-gray-700 prose-ul:dark:text-gray-300 prose-ol:text-gray-700 prose-ol:dark:text-gray-300 prose-li:text-gray-700 prose-li:dark:text-gray-300">
              ${description.replace(/\n/g, "<br />")}
            </div>
          </div>

          <!-- Requirements -->
          ${
            requirements
              ? `<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 transition-colors duration-200">
                   <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">Requirements</h3>
                   <div class="prose max-w-none text-gray-700 dark:text-gray-300 prose-headings:text-gray-900 prose-headings:dark:text-gray-100 prose-strong:text-gray-900 prose-strong:dark:text-gray-100 prose-a:text-[#e74c3c] prose-a:dark:text-[#e74c3c] prose-a:hover:text-red-700 prose-a:dark:hover:text-[#f8c471] prose-ul:text-gray-700 prose-ul:dark:text-gray-300 prose-ol:text-gray-700 prose-ol:dark:text-gray-300 prose-li:text-gray-700 prose-li:dark:text-gray-300">
                     ${requirements.replace(/\n/g, "<br />")}
                   </div>
                 </div>`
              : ""
          }

          <!-- Application Instructions -->
          ${
            applicationInstructions
              ? `<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-8 transition-colors duration-200">
                   <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">How to Apply</h3>
                   <div class="prose max-w-none text-gray-700 dark:text-gray-300 prose-headings:text-gray-900 prose-headings:dark:text-gray-100 prose-strong:text-gray-900 prose-strong:dark:text-gray-100 prose-a:text-[#e74c3c] prose-a:dark:text-[#e74c3c] prose-a:hover:text-red-700 prose-a:dark:hover:text-[#f8c471] prose-ul:text-gray-700 prose-ul:dark:text-gray-300 prose-ol:text-gray-700 prose-ol:dark:text-gray-300 prose-li:text-gray-700 prose-li:dark:text-gray-300">
                     ${applicationInstructions.replace(/\n/g, "<br />")}
                   </div>
                 </div>`
              : ""
          }

          <!-- Back to Jobs Button -->
          <div class="text-center">
            <a
              href="jobs.html"
              class="inline-flex items-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-xl font-medium hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-all duration-200 transform hover:scale-105"
            >
              <svg
                class="w-5 h-5 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                ></path>
              </svg>
              Back to All Jobs
            </a>
          </div>
        </div>
      </div>
    </div>
  `;
}

function initJobDetail() {
  const params = new URLSearchParams(window.location.search);
  const idParam = params.get("id");

  if (!idParam) {
    renderNotFound();
    return;
  }

  fetch("data/jobs.json", { cache: "no-cache" })
    .then((res) => {
      if (!res.ok) throw new Error("Failed to load jobs.json");
      return res.json();
    })
    .then((data) => {
      const jobs = Array.isArray(data.jobs) ? data.jobs : [];
      const job = jobs.find((j) => String(j.id) === String(idParam));

      if (!job) {
        renderNotFound();
        return;
      }

      renderJob(job);
    })
    .catch((err) => {
      console.error("Error loading job details:", err);
      renderNotFound();
    });
}

document.addEventListener("DOMContentLoaded", initJobDetail);

