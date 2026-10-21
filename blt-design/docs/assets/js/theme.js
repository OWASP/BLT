(function () {
  // Same contract as every BLT site: class "dark" on <html>, saved as localStorage "theme".
  var storageKey = "theme";
  var legacyKey = "blt-theme"; // this guide's old key, read once as a fallback
  var root = document.documentElement;

  function getStoredTheme() {
    try {
      var theme = localStorage.getItem(storageKey);
      if (theme) return theme;
      var legacy = localStorage.getItem(legacyKey);
      if (legacy === "dark" || legacy === "light") {
        localStorage.setItem(storageKey, legacy);
        localStorage.removeItem(legacyKey);
        return legacy;
      }
      return null;
    } catch (error) {
      return null;
    }
  }

  function prefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function setMetaColor(theme) {
    var meta = document.querySelector('meta[name="theme-color"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.setAttribute("name", "theme-color");
      document.head.appendChild(meta);
    }
    meta.setAttribute("content", theme === "dark" ? "#030712" : "#f9fafb");
  }

  function applyTheme(theme, persist) {
    var nextTheme = theme === "dark" || theme === "light" ? theme : prefersDark() ? "dark" : "light";
    root.classList.toggle("dark", nextTheme === "dark");
    root.dataset.theme = nextTheme;
    setMetaColor(nextTheme);

    if (persist) {
      try {
        localStorage.setItem(storageKey, nextTheme);
      } catch (error) {}
    }

    syncThemeControls();
  }

  function syncThemeControls() {
    var isDark = root.classList.contains("dark");
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(isDark));
      button.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
      button.querySelectorAll("[data-theme-label]").forEach(function (label) {
        label.textContent = isDark ? "Light" : "Dark";
      });
    });
  }

  applyTheme(getStoredTheme(), false);

  document.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-theme-toggle]");
    if (!toggle) return;
    applyTheme(root.classList.contains("dark") ? "light" : "dark", true);
  });

  document.addEventListener("DOMContentLoaded", syncThemeControls);

  // The OWASP BLT top bar (blt-nav.js) has the site's theme toggle; keep the meta colour
  // and any demo controls in step with it.
  window.addEventListener("blt-theme-change", function (event) {
    applyTheme(event.detail && event.detail.dark ? "dark" : "light", true);
  });

  window.BLTTheme = {
    apply: applyTheme,
    sync: syncThemeControls,
  };
})();
