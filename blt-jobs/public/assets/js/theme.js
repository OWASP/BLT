// Theme: the shared OWASP BLT bar (<blt-nav>) owns the dark/light toggle; it sets class
// "dark" on <html> and saves localStorage "theme", which each page's pre-paint script reads.
// This file only handles the BLT Jobs mobile menu button.
document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("click", (event) => {
    const menuButton = event.target.closest("#mobile-menu-toggle");
    if (menuButton) {
      const menu = document.getElementById("mobile-menu");
      if (menu) {
        const open = menu.classList.toggle("hidden") === false;
        menuButton.setAttribute("aria-expanded", String(open));
      }
    }
  });
});
