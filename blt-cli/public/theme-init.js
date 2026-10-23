// Runs before first paint: apply the saved theme, or the system preference.
// Same contract as owaspblt.org and the BLT top bar: class "dark" on <html>, localStorage "theme".
(function () {
  var saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) { saved = null; }
  var dark = saved === "dark" || (saved !== "light" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
})();
