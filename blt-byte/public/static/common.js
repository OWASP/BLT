/**
 * common.js - Shared logic for BLT Byte
 */

// 1. Initial Theme Setup (Blocking to prevent flicker)
// Same contract as every BLT site: class "dark" on <html>, saved as localStorage "theme"; the
// OWASP BLT top bar (blt-nav.js) has the toggle. "blt-theme" is the key this site used before.
(function () {
    try {
        const savedTheme = localStorage.getItem('theme') || localStorage.getItem('blt-theme');
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
                        'blt-red': '#dc2626',
                    },
                    fontFamily: {
                        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
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
});
