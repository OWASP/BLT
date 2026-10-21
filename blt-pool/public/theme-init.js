// Runs before first paint: apply the saved theme (localStorage "theme", shared with the
// <blt-nav> bar from owaspblt.org/_shared/blt-nav.js), or the system preference.
(function () {
  var saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) { saved = null; }
  var dark = saved === "dark" || (saved !== "light" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
})();
