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

        // Initialize button states
        const currentTheme = localStorage.getItem('theme') ||
            (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        this.updateButtons(currentTheme);
    },

    updateButtons(theme) {
        const buttons = document.querySelectorAll('.theme-toggle-btn');
        buttons.forEach(btn => {
            const iconMoon = btn.querySelector('.fa-moon');
            const iconSun = btn.querySelector('.fa-sun');

            if (theme === 'dark') {
                if (iconMoon) iconMoon.classList.add('hidden');
                if (iconSun) iconSun.classList.remove('hidden');
            } else {
                if (iconMoon) iconMoon.classList.remove('hidden');
                if (iconSun) iconSun.classList.add('hidden');
            }
        });
    }
};

// Initialize theme management
themeToggle.init();
window.toggleTheme = () => themeToggle.toggle();
