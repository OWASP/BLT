(function () {
  // Same contract as owaspblt.org and its <blt-nav> bar: class "dark" on <html>, saved as
  // localStorage "theme". "blt-theme" is the key this site used before; still read once.
  var storageKey = "theme";
  var legacyKey = "blt-theme";
  var root = document.documentElement;

  function getStoredTheme() {
    try {
      return localStorage.getItem(storageKey) || localStorage.getItem(legacyKey);
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

  // The bar's toggle has already set html.dark and saved the choice; keep data-theme and
  // the theme-color meta in step.
  window.addEventListener("blt-theme-change", function (event) {
    applyTheme(event.detail && event.detail.dark ? "dark" : "light", false);
  });

  window.BLTTheme = {
    apply: applyTheme,
    sync: syncThemeControls,
  };
})();
