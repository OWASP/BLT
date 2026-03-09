/**
 * common.js - Shared logic for BLT Byte
 */

// 1. Initial Theme Setup (Blocking to prevent flicker)
(function () {
    try {
        const savedTheme = localStorage.getItem('blt-theme');
        if (savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        }
    } catch (e) {
        console.error('Failed to initialize theme:', e);
    }
})();

// 2. Shared Tailwind Configuration
if (window.tailwind) {
    tailwind.config = {
        darkMode: 'class',
        theme: {
            extend: {
                colors: {
                    'blt-red': '#E10101',
                },
                fontFamily: {
                    sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
                }
            }
        }
    };
}

// 3. Shared Marked.js Configuration
if (window.marked) {
    marked.setOptions({
        breaks: true,
        gfm: true,
    });
}

// 4. Utility Functions
window.BLT = {
    // Theme Toggle Logic
    initThemeToggle: function (buttonId) {
        const toggleBtn = document.getElementById(buttonId);
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                const isDark = document.documentElement.classList.toggle('dark');
                localStorage.setItem('blt-theme', isDark ? 'dark' : 'light');
            });
        }
    },

    // HTML Escaping
    escHtml: function (str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
};

// Initialize common features when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Current Year for Footer
    const yearEl = document.getElementById('yr') || document.getElementById('year');
    if (yearEl) {
        yearEl.textContent = new Date().getFullYear();
    }

    // Auto-init theme toggle if default ID exists
    BLT.initThemeToggle('dark-toggle');
});
