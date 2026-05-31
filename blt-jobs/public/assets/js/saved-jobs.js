/**
 * Saved Jobs Manager - localStorage-based job bookmarking
 */

const STORAGE_KEY = "blt_saved_jobs";

const SavedJobs = {
  /**
   * Get all saved job IDs
   * @returns {string[]} Array of job IDs
   */
  getAll() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.error("Error reading saved jobs:", e);
      return [];
    }
  },

  /**
   * Check if a job is saved
   * @param {string} jobId - Job ID to check
   * @returns {boolean}
   */
  isSaved(jobId) {
    const saved = this.getAll();
    return saved.includes(String(jobId));
  },

  /**
   * Save a job
   * @param {string} jobId - Job ID to save
   * @returns {boolean} Success status
   */
  save(jobId) {
    try {
      const saved = this.getAll();
      if (!saved.includes(String(jobId))) {
        saved.push(String(jobId));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
        this.dispatchEvent("saved", jobId);
        return true;
      }
      return false;
    } catch (e) {
      console.error("Error saving job:", e);
      return false;
    }
  },

  /**
   * Unsave a job
   * @param {string} jobId - Job ID to remove
   * @returns {boolean} Success status
   */
  unsave(jobId) {
    try {
      const saved = this.getAll();
      const filtered = saved.filter((id) => id !== String(jobId));
      if (filtered.length !== saved.length) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
        this.dispatchEvent("unsaved", jobId);
        return true;
      }
      return false;
    } catch (e) {
      console.error("Error unsaving job:", e);
      return false;
    }
  },

  /**
   * Toggle saved status
   * @param {string} jobId - Job ID to toggle
   * @returns {boolean} New saved status
   */
  toggle(jobId) {
    if (this.isSaved(jobId)) {
      this.unsave(jobId);
      return false;
    } else {
      this.save(jobId);
      return true;
    }
  },

  /**
   * Get count of saved jobs
   * @returns {number}
   */
  count() {
    return this.getAll().length;
  },

  /**
   * Clear all saved jobs
   */
  clear() {
    try {
      localStorage.removeItem(STORAGE_KEY);
      this.dispatchEvent("cleared");
    } catch (e) {
      console.error("Error clearing saved jobs:", e);
    }
  },

  /**
   * Dispatch custom event
   * @param {string} action - Event action (saved, unsaved, cleared)
   * @param {string} jobId - Job ID (optional)
   */
  dispatchEvent(action, jobId = null) {
    const event = new CustomEvent("savedJobsChanged", {
      detail: { action, jobId, count: this.count() },
    });
    window.dispatchEvent(event);
  },

  /**
   * Create a bookmark button element
   * @param {string} jobId - Job ID
   * @param {object} options - Button options
   * @returns {HTMLButtonElement}
   */
  createButton(jobId, options = {}) {
    const {
      showLabel = true,
      size = "md",
      variant = "outline",
    } = options;

    const button = document.createElement("button");
    button.type = "button";
    button.dataset.jobId = jobId;
    button.dataset.savedJobsButton = "true";

    const isSaved = this.isSaved(jobId);

    // Size classes
    const sizeClasses = {
      sm: "px-3 py-1.5 text-xs",
      md: "px-4 py-2 text-sm",
      lg: "px-6 py-3 text-base",
    };

    // Variant classes
    const variantClasses = {
      outline: isSaved
        ? "border-2 border-red-600 bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/30 dark:border-red-500 dark:text-red-400 dark:hover:bg-red-900/50"
        : "border-2 border-slate-300 bg-white text-slate-700 hover:border-red-600 hover:text-red-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-red-500 dark:hover:text-red-400",
      solid: isSaved
        ? "bg-red-600 text-white hover:bg-red-700"
        : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600",
    };

    button.className = `inline-flex items-center gap-2 rounded-lg font-medium transition-all duration-200 ${sizeClasses[size]} ${variantClasses[variant]}`;
    button.setAttribute("aria-label", isSaved ? "Remove from saved jobs" : "Save job");

    const iconClass = isSaved ? "fa-solid fa-bookmark" : "fa-regular fa-bookmark";
    const labelText = isSaved ? "Saved" : "Save Job";

    button.innerHTML = `
      <i class="${iconClass}" aria-hidden="true"></i>
      ${showLabel ? `<span>${labelText}</span>` : ""}
    `;

    // Add click handler
    button.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const newStatus = this.toggle(jobId);
      this.updateButton(button, newStatus, showLabel);
    });

    return button;
  },

  /**
   * Update button appearance
   * @param {HTMLButtonElement} button - Button element
   * @param {boolean} isSaved - Saved status
   * @param {boolean} showLabel - Show label
   */
  updateButton(button, isSaved, showLabel = true) {
    const iconClass = isSaved ? "fa-solid fa-bookmark" : "fa-regular fa-bookmark";
    const labelText = isSaved ? "Saved" : "Save Job";

    // Update classes
    if (isSaved) {
      button.classList.remove("border-slate-300", "bg-white", "text-slate-700", "hover:border-red-600", "hover:text-red-600");
      button.classList.remove("dark:border-gray-600", "dark:bg-gray-800", "dark:text-gray-300", "dark:hover:border-red-500", "dark:hover:text-red-400");
      button.classList.add("border-red-600", "bg-red-50", "text-red-600", "hover:bg-red-100");
      button.classList.add("dark:bg-red-900/30", "dark:border-red-500", "dark:text-red-400", "dark:hover:bg-red-900/50");
    } else {
      button.classList.remove("border-red-600", "bg-red-50", "text-red-600", "hover:bg-red-100");
      button.classList.remove("dark:bg-red-900/30", "dark:border-red-500", "dark:text-red-400", "dark:hover:bg-red-900/50");
      button.classList.add("border-slate-300", "bg-white", "text-slate-700", "hover:border-red-600", "hover:text-red-600");
      button.classList.add("dark:border-gray-600", "dark:bg-gray-800", "dark:text-gray-300", "dark:hover:border-red-500", "dark:hover:text-red-400");
    }

    button.setAttribute("aria-label", isSaved ? "Remove from saved jobs" : "Save job");
    button.innerHTML = `
      <i class="${iconClass}" aria-hidden="true"></i>
      ${showLabel ? `<span>${labelText}</span>` : ""}
    `;
  },

  /**
   * Update all bookmark buttons on the page
   */
  updateAllButtons() {
    const buttons = document.querySelectorAll("[data-saved-jobs-button]");
    buttons.forEach((button) => {
      const jobId = button.dataset.jobId;
      if (jobId) {
        const isSaved = this.isSaved(jobId);
        const showLabel = button.querySelector("span") !== null;
        this.updateButton(button, isSaved, showLabel);
      }
    });
  },
};

// Update buttons when storage changes in another tab
window.addEventListener("storage", (e) => {
  if (e.key === STORAGE_KEY) {
    SavedJobs.updateAllButtons();
  }
});

// Make available globally
window.SavedJobs = SavedJobs;
