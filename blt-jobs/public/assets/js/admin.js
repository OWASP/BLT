(function () {
  const state = {
    candidates: [],
    selectedEmails: new Set(),
    query: "",
  };

  const loginPanel = document.getElementById("login-panel");
  const adminPanel = document.getElementById("admin-panel");
  const loginForm = document.getElementById("login-form");
  const loginStatus = document.getElementById("login-status");
  const candidateList = document.getElementById("candidate-list");
  const candidateSearch = document.getElementById("candidate-search");
  const selectedCount = document.getElementById("selected-count");
  const selectVisible = document.getElementById("select-visible");
  const clearSelection = document.getElementById("clear-selection");
  const emailForm = document.getElementById("email-form");
  const sendButton = document.getElementById("send-button");
  const sendStatus = document.getElementById("send-status");
  const logoutButton = document.getElementById("logout-button");

  init();

  async function init() {
    const session = await api("/api/admin/session");
    setAuthenticated(Boolean(session.authenticated));
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStatus(loginStatus, "");

    const username = document.getElementById("admin-username").value;
    const password = document.getElementById("admin-password").value;

    const result = await api("/api/admin/login", {
      method: "POST",
      body: { username, password },
    });

    if (result.authenticated) {
      loginForm.reset();
      setAuthenticated(true);
      return;
    }

    setStatus(loginStatus, result.error || "Unable to sign in.", "error");
  });

  logoutButton.addEventListener("click", async () => {
    await api("/api/admin/logout", { method: "POST" });
    setAuthenticated(false);
  });

  candidateSearch.addEventListener("input", () => {
    state.query = candidateSearch.value.trim().toLowerCase();
    renderCandidates();
  });

  selectVisible.addEventListener("click", () => {
    visibleCandidates().forEach((candidate) => state.selectedEmails.add(candidate.email));
    renderCandidates();
  });

  clearSelection.addEventListener("click", () => {
    state.selectedEmails.clear();
    renderCandidates();
  });

  emailForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStatus(sendStatus, "");
    sendButton.disabled = true;

    const manualRecipients = document.getElementById("manual-recipients").value;
    const recipients = Array.from(state.selectedEmails).concat(splitRecipients(manualRecipients));
    const subject = document.getElementById("email-subject").value;
    const message = document.getElementById("email-message").value;

    const result = await api("/api/admin/send", {
      method: "POST",
      body: { recipients, subject, message },
    });

    sendButton.disabled = false;

    if (result.ok) {
      setStatus(sendStatus, `Sent to ${result.sent} recipient${result.sent === 1 ? "" : "s"}.`, "success");
      return;
    }

    setStatus(sendStatus, result.error || "Unable to send email.", "error");
  });

  async function setAuthenticated(isAuthenticated) {
    loginPanel.classList.toggle("hidden", isAuthenticated);
    adminPanel.classList.toggle("hidden", !isAuthenticated);

    if (isAuthenticated && state.candidates.length === 0) {
      await loadCandidates();
    }
  }

  async function loadCandidates() {
    try {
      const response = await fetch("./data/seekers.json", { cache: "no-store" });
      const data = await response.json();
      state.candidates = (data.seekers || [])
        .map((candidate) => ({
          id: candidate.id,
          name: candidate.name || "Unnamed candidate",
          headline: candidate.headline || "",
          email: firstEmail(candidate.email) || firstEmail(candidate.portfolio),
          location: candidate.location || "",
        }))
        .filter((candidate) => candidate.email);
      renderCandidates();
    } catch (error) {
      candidateList.innerHTML = `<p class="text-sm text-red-600 dark:text-red-400">${escapeHtml(error.message)}</p>`;
    }
  }

  function renderCandidates() {
    const candidates = visibleCandidates();
    selectedCount.textContent = `${state.selectedEmails.size} selected`;

    if (candidates.length === 0) {
      candidateList.innerHTML = '<p class="text-sm text-slate-500 dark:text-gray-400">No candidates with email addresses found.</p>';
      return;
    }

    candidateList.innerHTML = candidates
      .map((candidate) => {
        const checked = state.selectedEmails.has(candidate.email) ? "checked" : "";
        return `
          <label class="flex cursor-pointer gap-3 rounded-lg border border-slate-200 p-3 transition hover:bg-slate-50 dark:border-gray-700 dark:hover:bg-gray-700/60">
            <input type="checkbox" data-email="${escapeHtml(candidate.email)}" ${checked} class="mt-1 h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500" />
            <span class="min-w-0">
              <span class="block truncate text-sm font-semibold text-slate-900 dark:text-white">${escapeHtml(candidate.name)}</span>
              <span class="block truncate text-xs text-slate-500 dark:text-gray-400">${escapeHtml(candidate.headline || candidate.location || candidate.email)}</span>
              <span class="block truncate text-xs text-red-600 dark:text-red-400">${escapeHtml(candidate.email)}</span>
            </span>
          </label>
        `;
      })
      .join("");

    candidateList.querySelectorAll("input[type='checkbox']").forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) state.selectedEmails.add(checkbox.dataset.email);
        else state.selectedEmails.delete(checkbox.dataset.email);
        selectedCount.textContent = `${state.selectedEmails.size} selected`;
      });
    });
  }

  function visibleCandidates() {
    if (!state.query) return state.candidates;
    return state.candidates.filter((candidate) =>
      [candidate.name, candidate.headline, candidate.location, candidate.email]
        .join(" ")
        .toLowerCase()
        .includes(state.query),
    );
  }

  async function api(path, options) {
    const response = await fetch(path, {
      method: options?.method || "GET",
      headers: { "Content-Type": "application/json" },
      body: options?.body ? JSON.stringify(options.body) : undefined,
    });

    let data = {};
    try {
      data = await response.json();
    } catch {
      data = {};
    }

    if (!response.ok && !data.error) data.error = `Request failed with ${response.status}.`;
    return data;
  }

  function firstEmail(value) {
    return String(value || "").match(/[^\s@:<>]+@[^\s@:<>]+\.[^\s@:<>]+/)?.[0] || "";
  }

  function splitRecipients(value) {
    return String(value || "")
      .split(/[,\s;]+/)
      .map((email) => email.trim())
      .filter(Boolean);
  }

  function setStatus(element, message, type) {
    if (!message) {
      element.classList.add("hidden");
      element.textContent = "";
      return;
    }

    element.textContent = message;
    element.classList.remove("hidden", "bg-red-50", "text-red-700", "bg-green-50", "text-green-700", "dark:bg-red-900/30", "dark:text-red-300", "dark:bg-green-900/30", "dark:text-green-300");

    if (type === "success") {
      element.classList.add("bg-green-50", "text-green-700", "dark:bg-green-900/30", "dark:text-green-300");
    } else {
      element.classList.add("bg-red-50", "text-red-700", "dark:bg-red-900/30", "dark:text-red-300");
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
})();
