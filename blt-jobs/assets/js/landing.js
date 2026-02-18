(function () {
  const recentListings = document.getElementById("recent-listings");
  if (!recentListings) return;

  const MAX_JOBS = 3;
  const MAX_SEEKERS = 3;

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  Promise.all([
    fetch("data/jobs.json", { cache: "no-cache" }).then((r) => (r.ok ? r.json() : { jobs: [] })),
    fetch("data/seekers.json", { cache: "no-cache" }).then((r) => (r.ok ? r.json() : { seekers: [] })),
  ])
    .then(([jobsData, seekersData]) => {
      const jobs = Array.isArray(jobsData.jobs) ? jobsData.jobs.slice(0, MAX_JOBS) : [];
      const seekers = Array.isArray(seekersData.seekers) ? seekersData.seekers.slice(0, MAX_SEEKERS) : [];

      let html = "";
      if (jobs.length > 0) {
        html += '<div class="mb-6"><h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Recent jobs</h3><ul class="space-y-2">';
        jobs.forEach((j) => {
          const title = escapeHtml(j.title || "Untitled");
          const org = escapeHtml(j.organization_name || "");
          html += `<li><a href="job.html?id=${encodeURIComponent(j.id)}" class="text-[#e74c3c] dark:text-[#e74c3c] hover:underline">${title}</a>${org ? ` – ${org}` : ""}</li>`;
        });
        html += "</ul></div>";
      }
      if (seekers.length > 0) {
        html += '<div><h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Recent profiles</h3><ul class="space-y-2">';
        seekers.forEach((s) => {
          const name = escapeHtml(s.name || "Anonymous");
          const headline = escapeHtml(s.headline || "");
          html += `<li><a href="seekers.html" class="text-[#e74c3c] dark:text-[#e74c3c] hover:underline">${name}</a>${headline ? ` – ${headline}` : ""}</li>`;
        });
        html += "</ul></div>";
      }
      if (!html) html = '<p class="text-gray-600 dark:text-gray-400">No listings yet. Be the first to <a href="add.html" class="text-[#e74c3c] dark:text-[#e74c3c] hover:underline">post a job</a> or <a href="add.html" class="text-[#e74c3c] dark:text-[#e74c3c] hover:underline">create your profile</a>.</p>';
      recentListings.innerHTML = html;
    })
    .catch(() => {
      recentListings.innerHTML = '<p class="text-gray-600 dark:text-gray-400">Loading recent listings…</p>';
    });
})();
