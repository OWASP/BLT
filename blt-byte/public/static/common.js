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

// 2. Shared Tailwind Configuration (Fix Issue 6: Race condition)
function applyTailwindConfig() {
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
        return true;
    }
    return false;
}

if (!applyTailwindConfig()) {
    const twInterval = setInterval(() => {
        if (applyTailwindConfig()) clearInterval(twInterval);
    }, 50);
    setTimeout(() => clearInterval(twInterval), 2000); // Stop after 2s
}

// 3. Shared Marked.js Configuration (Fix Issue 3 & 5)
if (window.marked) {
    const renderer = new marked.Renderer();
    const linkRenderer = renderer.link;
    renderer.link = (href, title, text) => {
        const localLink = href.startsWith('/') || href.startsWith(window.location.origin);
        const html = linkRenderer.call(renderer, href, title, text);
        return localLink ? html : html.replace(/^<a /, '<a target="_blank" rel="noopener noreferrer" ');
    };

    marked.setOptions({
        renderer: renderer,
        breaks: true,
        gfm: true,
        headerIds: false, // Fix Issue 5
        mangle: false     // Disable for security/simplicity
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
    },

    /**
     * Issue 4: Central Sanitization
     * Scopes DOMPurify to allowed markdown tags for security.
     */
    sanitize: function (html) {
        if (!window.DOMPurify) return html;
        return DOMPurify.sanitize(html, {
            ALLOWED_TAGS: [
                'b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li',
                'code', 'pre', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'img'
            ],
            ALLOWED_ATTR: ['href', 'title', 'target', 'rel', 'src', 'alt', 'class']
        });
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
