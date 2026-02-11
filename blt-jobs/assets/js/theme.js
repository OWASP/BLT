function applyStoredTheme() {
  const stored = localStorage.getItem("theme");
  const prefersDark = window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;

  const isDark = stored === "dark" || (!stored && prefersDark);

  document.documentElement.classList.toggle("dark", isDark);

  const icon = document.getElementById("themeToggleIcon");
  if (icon) {
    icon.textContent = isDark ? "☀️" : "🌙";
  }
}

function initThemeToggle() {
  applyStoredTheme();

  const button = document.getElementById("themeToggle");
  if (!button) return;

  button.addEventListener("click", () => {
    const isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("theme", isDark ? "dark" : "light");

    const icon = document.getElementById("themeToggleIcon");
    if (icon) {
      icon.textContent = isDark ? "☀️" : "🌙";
    }
  });
}

document.addEventListener("DOMContentLoaded", initThemeToggle);

