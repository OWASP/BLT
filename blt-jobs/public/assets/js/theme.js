document.addEventListener("DOMContentLoaded", () => {
  const htmlElement = document.documentElement;

  document.addEventListener("click", (event) => {
    const toggleButton = event.target.closest("#theme-toggle");
    if (toggleButton) {
      const isDark = htmlElement.classList.toggle("dark");
      const newTheme = isDark ? "dark" : "light";
      localStorage.setItem("theme", newTheme);
      return;
    }

    const menuButton = event.target.closest("#mobile-menu-toggle");
    if (menuButton) {
      const menu = document.getElementById("mobile-menu");
      if (menu) {
        menu.classList.toggle("hidden");
      }
    }
  });
});

