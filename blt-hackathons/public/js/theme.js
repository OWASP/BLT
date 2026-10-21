// Runs before first paint: apply the saved theme, or the system preference.
// Same contract as owaspblt.org and the shared <blt-nav> bar (which owns the toggle):
// class "dark" on <html>, saved as localStorage "theme" = "dark" | "light".
// The old key "blt-theme" is read once as a fallback so an earlier choice carries over.
(function () {
    var root = document.documentElement;
    var saved = null;
    try {
        saved = window.localStorage.getItem("theme") || window.localStorage.getItem("blt-theme");
    } catch (error) {
        saved = null;
    }
    var dark = saved === "dark" ||
        (saved !== "light" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);

    function apply(isDark) {
        root.classList.toggle("dark", isDark);
        root.setAttribute("data-theme", isDark ? "dark" : "light");
    }

    apply(dark);

    window.addEventListener("blt-theme-change", function (event) {
        apply(!!(event.detail && event.detail.dark));
    });

    window.BLTTheme = {
        getTheme: function () {
            return root.classList.contains("dark") ? "dark" : "light";
        },
    };
})();
