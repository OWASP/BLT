// Runs before first paint: apply the saved theme, or the system preference.
// Same contract as owaspblt.org and the BLT top bar: class "dark" on <html>, localStorage "theme".
// The old "blt-dark" key is still read once so returning visitors keep their choice.
(function () {
  var saved = null;
  try { saved = localStorage.getItem("theme") || localStorage.getItem("blt-dark"); } catch (e) { saved = null; }
  var dark = saved === "dark" || (saved !== "light" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
})();
