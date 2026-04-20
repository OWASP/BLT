/**
 * Theme Management - Dark/Light Mode Toggle
 * Manages theme preference with localStorage persistence
 */

const ThemeManager = (() => {
  const STORAGE_KEY = 'blt-theme-preference';
  const DARK_CLASS = 'dark';

  function readStoredTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (error) {
      return null;
    }
  }

  function storeTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (error) {
      // Ignore storage-unavailable errors.
    }
  }

  /**
   * Initialize theme from localStorage or default to light
   */
  function init() {
    const savedTheme = readStoredTheme();
    if (savedTheme === 'dark') {
      document.documentElement.classList.add(DARK_CLASS);
    }

    updateToggleButton(getCurrentTheme());
  }

  /**
   * Apply theme to document
   * @param {string} theme - 'light' or 'dark'
   */
  function applyTheme(theme) {
    const html = document.documentElement;
    if (theme === 'dark') {
      html.classList.add(DARK_CLASS);
    } else {
      html.classList.remove(DARK_CLASS);
    }
    storeTheme(theme);
  }

  /**
   * Toggle between light and dark theme
   */
  function toggle() {
    const html = document.documentElement;
    const isDark = html.classList.contains(DARK_CLASS);
    const newTheme = isDark ? 'light' : 'dark';
    applyTheme(newTheme);
    updateToggleButton(newTheme);
  }

  /**
   * Get current theme
   * @returns {string} 'light' or 'dark'
   */
  function getCurrentTheme() {
    return document.documentElement.classList.contains(DARK_CLASS) ? 'dark' : 'light';
  }

  /**
   * Update toggle button icon based on current theme
   * @param {string} theme - 'light' or 'dark'
   */
  function updateToggleButton(theme) {
    const btn = document.getElementById('theme-toggle-btn');
    if (!btn) return;

    const icon = btn.querySelector('i');

    if (theme === 'dark') {
      if (icon) icon.className = 'fa-solid fa-sun';
      btn.setAttribute('aria-label', 'Switch to light mode');
      btn.title = 'Light mode';
    } else {
      if (icon) icon.className = 'fa-solid fa-moon';
      btn.setAttribute('aria-label', 'Switch to dark mode');
      btn.title = 'Dark mode';
    }
  }

  /**
   * Initialize toggle button click handler
   */
  function initToggleButton() {
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) {
      btn.addEventListener('click', toggle);
      // Set initial icon and label based on current theme
      updateToggleButton(getCurrentTheme());
    }
  }

  // Public API
  return {
    init,
    toggle,
    getCurrentTheme,
    updateToggleButton,
    initToggleButton,
  };
})();

// Initialize theme when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
    ThemeManager.initToggleButton();
  });
} else {
  ThemeManager.init();
  ThemeManager.initToggleButton();
}
