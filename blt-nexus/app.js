/**
 * BLT Nexus – App logic
 * Renders project cards, handles search & category filtering.
 */

(function () {
    "use strict";
  
    const CATEGORY_LABELS = {
      "bug-bounty": "Bug Bounty",
      scanning: "Scanning",
      ctf: "CTF / Labs",
      platform: "Platform",
      framework: "Framework",
      community: "Community",
    };
  
    // ── Utilities ────────────────────────────────────────────────────────────
  
    function initials(name) {
      return name
        .split(/\s+/)
        .map((w) => w[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    }
  
    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#x27;");
    }
  
    // ── Render helpers ───────────────────────────────────────────────────────
  
    function renderAmbassador(amb) {
      const ini = escapeHtml(initials(amb.name));
      const name = escapeHtml(amb.name);
      const role = escapeHtml(amb.role);
      const github = escapeHtml(amb.github);
      const avatarUrl = escapeHtml(amb.avatarUrl || "");
  
      const avatarInner = avatarUrl
        ? `<img src="${avatarUrl}" alt="${name}" loading="lazy" onerror="this.style.display='none';this.parentNode.textContent='${ini}'">`
        : ini;
  
      return `
        <div class="ambassador-item">
          <div class="ambassador-avatar" aria-hidden="true">${avatarInner}</div>
          <div class="ambassador-info">
            <div class="ambassador-name">${name}</div>
            <div class="ambassador-role">${role}</div>
          </div>
          <a
            href="https://github.com/${github}"
            class="ambassador-github"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View ${name}'s GitHub profile"
          >@${github}</a>
        </div>`;
    }
  
    function renderCard(project) {
      const name = escapeHtml(project.name);
      const logo = escapeHtml(project.logo);
      const url = escapeHtml(project.url);
      const category = escapeHtml(project.category);
      const categoryLabel = escapeHtml(CATEGORY_LABELS[project.category] || project.category);
      const desc = escapeHtml(project.description);
      const bltUrl = project.bltUrl ? escapeHtml(project.bltUrl) : null;
  
      const ambassadorsHtml = project.ambassadors.length
        ? `<div class="ambassadors-label">Ambassadors</div>
           <div class="ambassadors-list">${project.ambassadors.map(renderAmbassador).join("")}</div>`
        : `<div class="ambassadors-label">No ambassadors yet</div>
           <p style="font-size:0.83rem;color:var(--text-muted)">Be the first to represent this project!</p>`;
  
      const bltLink = bltUrl
        ? `<a href="${bltUrl}" class="card-link" target="_blank" rel="noopener noreferrer" aria-label="View ${name} on BLT">
             <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
             BLT
           </a>`
        : "";
  
      return `
        <article class="project-card" role="listitem" data-category="${category}" data-id="${escapeHtml(project.id)}">
          <div class="card-header">
            <div class="project-logo emoji-logo" aria-hidden="true">${logo}</div>
            <div class="card-title-group">
              <h3>${name}</h3>
              <a href="${url}" class="project-url" target="_blank" rel="noopener noreferrer">${url.replace(/^https?:\/\//, "")}</a>
            </div>
            <span class="category-badge category-${category}">${categoryLabel}</span>
          </div>
          <div class="card-body">
            <p class="project-desc">${desc}</p>
            ${ambassadorsHtml}
          </div>
          <div class="card-footer">
            <div class="card-links">
              <a href="${url}" class="card-link" target="_blank" rel="noopener noreferrer" aria-label="Visit ${name} website">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                Website
              </a>
              ${bltLink}
            </div>
            <a
              href="https://blt.owasp.org/ambassador"
              class="become-ambassador-btn"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Become an ambassador for ${name}"
            >+ Ambassador</a>
          </div>
        </article>`;
    }
  
    // ── Stats counter animation ──────────────────────────────────────────────
  
    function animateCount(el, target, duration) {
      const start = performance.now();
      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(eased * target);
        if (progress < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    }
  
    // ── Main ─────────────────────────────────────────────────────────────────
  
    function init() {
      const grid = document.getElementById("projects-grid");
      const noResults = document.getElementById("no-results");
      const searchInput = document.getElementById("search");
      const filterButtons = document.querySelectorAll(".filter-tag");
  
      // Populate stats
      const totalAmbassadors = PROJECTS.reduce(
        (sum, p) => sum + p.ambassadors.length,
        0
      );
      const categories = new Set(PROJECTS.map((p) => p.category));
  
      animateCount(document.getElementById("stat-projects"), PROJECTS.length, 900);
      animateCount(document.getElementById("stat-ambassadors"), totalAmbassadors, 900);
      animateCount(document.getElementById("stat-categories"), categories.size, 900);
  
      // Render all cards
      const fragment = document.createDocumentFragment();
      PROJECTS.forEach((project) => {
        const wrapper = document.createElement("div");
        wrapper.innerHTML = renderCard(project).trim();
        fragment.appendChild(wrapper.firstChild);
      });
      grid.insertBefore(fragment, noResults);
  
      // Set footer year
      const yearEl = document.getElementById("footer-year");
      if (yearEl) yearEl.textContent = new Date().getFullYear();
  
      // ── Filtering logic ──────────────────────────────────────────────────
  
      let activeCategory = "all";
      let searchQuery = "";
  
      function applyFilters() {
        const cards = grid.querySelectorAll(".project-card");
        const query = searchQuery.toLowerCase();
        let visibleCount = 0;
  
        cards.forEach((card) => {
          const categoryMatch =
            activeCategory === "all" ||
            card.dataset.category === activeCategory;
  
          const id = card.dataset.id;
          const project = PROJECTS.find((p) => p.id === id);
          const textToSearch = [
            project.name,
            project.description,
            project.category,
            CATEGORY_LABELS[project.category] || "",
            ...project.ambassadors.map((a) => a.name + " " + a.role + " " + a.github),
          ]
            .join(" ")
            .toLowerCase();
  
          const searchMatch = !query || textToSearch.includes(query);
  
          const visible = categoryMatch && searchMatch;
          card.classList.toggle("hidden", !visible);
          if (visible) visibleCount++;
        });
  
        noResults.style.display = visibleCount === 0 ? "block" : "none";
      }
  
      // Filter button clicks
      filterButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          filterButtons.forEach((b) => {
            b.classList.remove("active");
            b.setAttribute("aria-pressed", "false");
          });
          btn.classList.add("active");
          btn.setAttribute("aria-pressed", "true");
          activeCategory = btn.dataset.category;
          applyFilters();
        });
      });
  
      // Search input
      searchInput.addEventListener("input", () => {
        searchQuery = searchInput.value;
        applyFilters();
      });
    }
  
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  })();