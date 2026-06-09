(function () {
    var STORAGE_KEY = "blt-theme";
    var root = document.documentElement;
    var storage = null;

    try {
        var testKey = "__blt_theme_test__";
        window.localStorage.setItem(testKey, "1");
        window.localStorage.removeItem(testKey);
        storage = window.localStorage;
    } catch (error) {
        storage = null;
    }

    function readStoredTheme() {
        if (!storage) return null;
        try {
            return storage.getItem(STORAGE_KEY);
        } catch (error) {
            return null;
        }
    }

    function writeStoredTheme(theme) {
        if (!storage) return;
        try {
            storage.setItem(STORAGE_KEY, theme);
        } catch (error) {
            // Ignore persistence failures; the in-page state still updates.
        }
    }

    function currentTheme() {
        return root.classList.contains("dark") ? "dark" : "light";
    }

    function updateControls() {
        var isDark = currentTheme() === "dark";
        var nextTheme = isDark ? "light" : "dark";
        var controls = document.querySelectorAll("[data-theme-toggle]");

        controls.forEach(function (control) {
            control.setAttribute("aria-label", "Switch to " + nextTheme + " theme");
            control.setAttribute("aria-pressed", String(isDark));
            control.setAttribute("title", "Switch to " + nextTheme + " theme");

            var icon = control.querySelector("[data-theme-icon]");
            if (icon) {
                icon.classList.toggle("fa-moon", !isDark);
                icon.classList.toggle("fa-sun", isDark);
            }

            var label = control.querySelector("[data-theme-label]");
            if (label) {
                label.textContent = isDark ? "Light" : "Dark";
            }
        });
    }

    function applyTheme(theme, persist) {
        var normalized = theme === "dark" ? "dark" : "light";
        root.classList.toggle("dark", normalized === "dark");
        root.setAttribute("data-theme", normalized);

        if (persist) {
            writeStoredTheme(normalized);
        }

        updateControls();
    }

    function initControls() {
        updateControls();
        document.querySelectorAll("[data-theme-toggle]").forEach(function (control) {
            control.addEventListener("click", function () {
                applyTheme(currentTheme() === "dark" ? "light" : "dark", true);
            });
        });
    }

    applyTheme(readStoredTheme(), false);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initControls);
    } else {
        initControls();
    }

    window.BLTTheme = {
        applyTheme: function (theme) {
            applyTheme(theme, true);
        },
        getTheme: currentTheme,
    };
})();
