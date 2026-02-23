/**
 * Theme Management for OWASP BLT GSoC Pages
 * Handles dark/light mode toggling and persistence
 */

const themeToggle = {
    init() {
        // Apply theme as soon as possible to avoid flash
        this.applyTheme();

        // Setup toggle button listeners when DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupListeners());
        } else {
            this.setupListeners();
        }
    },

    applyTheme() {
        const theme = localStorage.getItem('theme') ||
            (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    },

    toggle() {
        const isDark = document.documentElement.classList.contains('dark');
        const newTheme = isDark ? 'light' : 'dark';

        if (newTheme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }

        localStorage.setItem('theme', newTheme);
        this.updateButtons(newTheme);
    },

    setupListeners() {
        const buttons = document.querySelectorAll('.theme-toggle-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => this.toggle());
        });

        // Initial button state update
        const currentTheme = localStorage.getItem('theme') ||
            (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        this.updateButtons(currentTheme);
    },

    updateButtons(theme) {
        const buttons = document.querySelectorAll('.theme-toggle-btn');
        buttons.forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon) {
                if (theme === 'dark') {
                    icon.className = 'fas fa-sun text-yellow-500';
                    // Optional: update text if present
                    const text = btn.querySelector('span');
                    if (text) text.textContent = 'Light Mode';
                } else {
                    icon.className = 'fas fa-moon text-gray-600';
                    const text = btn.querySelector('span');
                    if (text) text.textContent = 'Dark Mode';
                }
            }
        });
    }
};

// Initialize theme management
themeToggle.init();
window.toggleTheme = () => themeToggle.toggle();
