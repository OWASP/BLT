document.addEventListener("DOMContentLoaded", () => {
  const htmlElement = document.documentElement;

  document.addEventListener("click", (event) => {
    const toggleButton = event.target.closest("#theme-toggle");
    if (!toggleButton) {
      return;
    }

    const isDark = htmlElement.classList.toggle("dark");
    const newTheme = isDark ? "dark" : "light";

    // Save user preference
    localStorage.setItem("theme", newTheme);
  });
});

