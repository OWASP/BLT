/**
 * OWASP BLT - Main Application Module
 */
// ===================================
// Configuration    
// Configuration    
// ===================================
const CONFIG = {
    // API endpoint - should be set to your Cloudflare Worker URL
    // For production, use absolute URL like: 'https://api.owaspblt.org'
    // For local development with worker: 'http://localhost:8787'
    API_BASE_URL: window.location.hostname === 'localhost'
        ? 'http://localhost:8787'
        : 'https://api.owaspblt.org', // TODO: Replace with your actual worker URL
    CACHE_DURATION: 5 * 60 * 1000, // 5 minutes
    ENABLE_ANALYTICS: true,
};

const TOKEN_KEY = 'authToken';

function getAuthToken() {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
}

function persistAuthToken(token, remember = true) {
    if (remember) {
        localStorage.setItem(TOKEN_KEY, token);
        sessionStorage.removeItem(TOKEN_KEY);
    } else {
        sessionStorage.setItem(TOKEN_KEY, token);
        localStorage.removeItem(TOKEN_KEY);
    }
}

function clearAuthToken() {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
}

// ===================================
// State Management
// ===================================
class AppState {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.listeners = new Map();
    }

    subscribe(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    emit(event, data) {
        const callbacks = this.listeners.get(event) || [];
        callbacks.forEach(callback => callback(data));
    }

    setUser(user) {
        this.user = user;
        this.isAuthenticated = !!user;
        this.emit('user:changed', user);
    }

    getUser() {
        return this.user;
    }
}

const state = new AppState();

// ===================================
// API Client
// ===================================
class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
        this.cache = new Map();
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        // Add auth token if available
        const token = getAuthToken();
        if (token) {
            defaultOptions.headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async get(endpoint, useCache = false) {
        if (useCache && this.cache.has(endpoint)) {
            const cached = this.cache.get(endpoint);
            if (Date.now() - cached.timestamp < CONFIG.CACHE_DURATION) {
                return cached.data;
            }
        }

        const data = await this.request(endpoint, { method: 'GET' });

        if (useCache) {
            this.cache.set(endpoint, {
                data,
                timestamp: Date.now(),
            });
        }

        return data;
    }

    async post(endpoint, body) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    }

    async put(endpoint, body) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(body),
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE',
        });
    }

    clearCache() {
        this.cache.clear();
    }
}

const api = new APIClient(CONFIG.API_BASE_URL);

// ===================================
// Authentication Module
// ===================================
class AuthModule {
    constructor(apiClient, appState) {
        this.api = apiClient;
        this.state = appState;
    }

    async login(email, password, remember = false) {
        try {
            const response = await this.api.post('/api/auth/login', { email, password });

            if (response.token) {
                persistAuthToken(response.token, remember);
                this.state.setUser(response.user);
                return { success: true, user: response.user };
            }

            return { success: false, error: 'Invalid credentials' };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async signup(userData) {
        try {
            const response = await this.api.post('/api/auth/signup', userData);

            if (response.token) {
                persistAuthToken(response.token, true);
                this.state.setUser(response.user);
                return { success: true, user: response.user };
            }

            return { success: false, error: 'Signup failed' };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async logout() {
        try {
            await this.api.post('/api/auth/logout', {});
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            clearAuthToken();
            this.state.setUser(null);
            this.api.clearCache();
        }
    }

    async checkAuth() {
        const token = getAuthToken();
        if (!token) {
            this.state.setUser(null);
            return false;
        }

        try {
            const response = await this.api.get('/api/auth/me');
            if (response.user) {
                this.state.setUser(response.user);
                return true;
            }
        } catch (error) {
            // Token invalid, clear it
            clearAuthToken();
            this.state.setUser(null);
        }

        this.state.setUser(null);
        return false;
    }
}

const auth = new AuthModule(api, state);

// ===================================
// UI Components
// ===================================
class UIComponents {
    static showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background-color: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 0.5rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            z-index: 9999;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// ===================================
// Event Handlers
// ===================================
function setupEventHandlers() {
    // Login button (modal only for button elements)
    const loginBtn = document.getElementById('loginBtn');
    if (loginBtn && loginBtn.tagName.toLowerCase() === 'button') {
        loginBtn.addEventListener('click', () => {
            UIComponents.showModal(UIComponents.createLoginForm());

            // Setup form submission
            const form = document.getElementById('loginForm');
            if (form) {
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const formData = new FormData(form);
                    const email = formData.get('email');
                    const password = formData.get('password');

                    const result = await auth.login(email, password);
                    if (result.success) {
                        UIComponents.hideModal();
                        UIComponents.showNotification('Logged in successfully!', 'success');
                        updateUIForAuth();
                    } else {
                        UIComponents.showNotification(result.error, 'error');
                    }
                });
            }
        });
    }

    // Signup buttons (modal only for button elements)
    const signupButtons = ['signupBtn', 'ctaSignupBtn'];
    signupButtons.forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn && btn.tagName.toLowerCase() === 'button') {
            btn.addEventListener('click', () => {
                UIComponents.showModal(UIComponents.createSignupForm());

                // Setup form submission
                const form = document.getElementById('signupForm');
                if (form) {
                    form.addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const formData = new FormData(form);
                        const userData = {
                            username: formData.get('username'),
                            email: formData.get('email'),
                            password: formData.get('password'),
                        };

                        const result = await auth.signup(userData);
                        if (result.success) {
                            UIComponents.hideModal();
                            UIComponents.showNotification('Account created successfully!', 'success');
                            updateUIForAuth();
                        } else {
                            UIComponents.showNotification(result.error, 'error');
                        }
                    });
                }
            });
        }
    });

    // Theme Toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');

            // Re-emit theme change for other components
            if (window.bltApp && window.bltApp.state) {
                window.bltApp.state.emit('theme:changed', isDark ? 'dark' : 'light');
            }
        });
    }

    // Login page handlers (bound in external JS to avoid inline event attributes)
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        const loginEmail = loginForm.querySelector('#email');
        const loginPassword = loginForm.querySelector('#password');
        const loginPasswordToggle = loginForm.querySelector('#loginPasswordToggle');

        if (loginEmail) {
            loginEmail.addEventListener('input', () => {
                if (typeof window.validateLoginEmail === 'function') {
                    window.validateLoginEmail(loginEmail);
                }
            });
            loginEmail.addEventListener('blur', () => {
                if (typeof window.validateLoginEmail === 'function') {
                    window.validateLoginEmail(loginEmail);
                }
            });
        }

        if (loginPassword) {
            loginPassword.addEventListener('input', () => {
                if (typeof window.validateLoginPassword === 'function') {
                    window.validateLoginPassword(loginPassword);
                }
            });
            loginPassword.addEventListener('blur', () => {
                if (typeof window.validateLoginPassword === 'function') {
                    window.validateLoginPassword(loginPassword);
                }
            });
        }

        if (loginPasswordToggle) {
            loginPasswordToggle.addEventListener('click', () => {
                if (typeof window.togglePassword === 'function') {
                    window.togglePassword('password', loginPasswordToggle);
                }
            });
        }

        // Handle submit for standalone login page
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(loginForm);
            const email = formData.get('email');
            const password = formData.get('password');
            const remember = formData.has('remember');

            const result = await auth.login(email, password, remember);
            if (result.success) {
                UIComponents.showNotification('Logged in successfully!', 'success');
                updateUIForAuth();
                // Keep user on the site; redirect to home if on the standalone login page
                if (window.location.pathname.includes('/pages/')) {
                    window.location.href = '../index.html';
                }
            } else {
                UIComponents.showNotification(result.error, 'error');
            }
        });
    }

    // Signup page handlers (bound in external JS to avoid inline event attributes)
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(signupForm);
            const userData = {
                username: formData.get('username'),
                email: formData.get('email'),
                password: formData.get('password'),
            };
            const confirmPassword = formData.get('confirmPassword');

            if (userData.password !== confirmPassword) {
                UIComponents.showNotification('Passwords do not match', 'error');
                return;
            }

            const result = await auth.signup(userData);
            if (result.success) {
                UIComponents.showNotification('Account created successfully!', 'success');
                updateUIForAuth();
                if (window.location.pathname.includes('/pages/')) {
                    window.location.href = '../index.html';
                }
            } else {
                UIComponents.showNotification(result.error, 'error');
            }
        });
    }
}

// ===================================
// UI Updates
// ===================================
function updateUIForAuth() {
    const user = state.getUser();
    const loginBtn = document.getElementById('loginBtn');
    const signupBtn = document.getElementById('signupBtn');

    if (user && state.isAuthenticated) {
        // Update buttons/links to show user menu
        if (loginBtn) {
            loginBtn.textContent = user.username;
            loginBtn.href = '/pages/profile.html';
            loginBtn.onclick = null;
        }
        if (signupBtn) {
            signupBtn.textContent = 'Logout';
            signupBtn.href = '#';
            signupBtn.classList.remove('btn-primary');
            signupBtn.classList.add('btn-secondary');
            signupBtn.onclick = async (e) => {
                e.preventDefault();
                await auth.logout();
                UIComponents.showNotification('Logged out successfully', 'success');
                updateUIForAuth();
            };
        }
    } else {
        // Reset to default unauthenticated state
        if (loginBtn) {
            loginBtn.textContent = 'Login';
            loginBtn.href = 'pages/login.html';
            loginBtn.onclick = null;
        }
        if (signupBtn) {
            signupBtn.textContent = 'Sign Up';
            signupBtn.href = 'pages/signup.html';
            signupBtn.classList.remove('btn-secondary');
            signupBtn.classList.add('btn-primary');
            signupBtn.onclick = null;
        }
    }
}

// ===================================
// Footer Last Updated
// ===================================
function updateFooterLastUpdated() {
    const el = document.getElementById('footer-last-updated');
    //document.body.addEventListener("htmx:afterSwap", updateFooterLastUpdated);
    if (!el) return;

    const lastModified = new Date(document.lastModified);
    const now = new Date();
    const diffMins = Math.max(0, Math.floor((now - lastModified) / 60000));
    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;

    const dateStr = lastModified.toLocaleString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    });

    let agoStr;
    if (hours > 0 && mins > 0) {
        agoStr = `${hours} hour${hours !== 1 ? 's' : ''} and ${mins} minute${mins !== 1 ? 's' : ''} ago`;
    } else if (hours > 0) {
        agoStr = `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    } else if (mins > 0) {
        agoStr = `${mins} minute${mins !== 1 ? 's' : ''} ago`;
    } else {
        agoStr = 'just now';
    }

    el.textContent = `Last updated: ${dateStr} (${agoStr})`;
}

document.body.addEventListener("htmx:afterSwap", function (event) {
    if (document.getElementById("footer-last-updated")) {
        updateFooterLastUpdated();
    }
});

// ===================================
// Initialization
// ===================================
async function init() {
    // Setup event handlers immediately so UI is responsive
    try {
        setupEventHandlers();
    } catch (error) {
        // Silently fail or log sparingly in production
    }

    // Check authentication status in background
    try {
        await auth.checkAuth();
        updateUIForAuth();
    } catch (error) {
        // Auth check failure is handled by UI state
    }

    // Update footer with last modified date
    updateFooterLastUpdated();

    // Update state to ready
    state.emit('app:ready');

    // Add CSS animations
    if (!document.getElementById('blt-animations')) {
        const style = document.createElement('style');
        style.id = 'blt-animations';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

// ===================================
// Export to window for global access
// ===================================
window.bltApp = {
    state,
    api,
    auth,
};

window.uiComponents = UIComponents;

// ===================================
// Start the application
// ===================================
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// ===================================
// Bug Report Form Validation
// ===================================
window.addEventListener('htmx:beforeRequest', (event) => {
    // Reference the element triggering the HTMX request
    const form = event.detail.elt;

    // Validate only if the request originates from the bug report form
    if (form && form.id === 'bugReportForm') {
        const description = document.getElementById('bugDescription');
        const errorBox = document.getElementById('custom-error-box');

        // Check for empty input or strings containing only whitespace
        if (description && description.value.trim().length === 0) {
            // Cancel the request to prevent unnecessary 405 errors
            event.preventDefault();

            if (errorBox) {
                // Display the custom Tailwind error alert
                errorBox.classList.remove('hidden');

                // Auto-hide the alert after 5 seconds for a cleaner UI
                setTimeout(() => {
                    errorBox.classList.add('hidden');
                }, 5000);
            }
        }
    }
});

const rowsPerPage = 5;
let currentPage = 1;
let totalResearchers = 3500;

function updateLeaderboardPagination() {
  const rows = document.querySelectorAll("#leaderboard-body .leaderboard-row");

  const start = (currentPage - 1) * rowsPerPage;
  const end = start + rowsPerPage;

  rows.forEach((row, index) => {
    if (index >= start && index < end) {
      row.style.display = "";
    } else {
      row.style.display = "none";
    }
  });

  const info = document.getElementById("pagination-info");

  if (info) {
    const displayStart = start + 1;
    const displayEnd = Math.min(end, totalResearchers);
    info.textContent = `Showing ${displayStart}-${displayEnd} of ${totalResearchers} researchers`;
  }
}

function updateActiveButton() {
  const buttons = document.querySelectorAll(".page-btn");

  buttons.forEach((btn) => {
    btn.classList.remove("bg-red-600", "text-white");

    const page = parseInt(btn.textContent.trim());

    if (page === currentPage) {
      btn.classList.add("bg-red-600", "text-white");
    }
  });
}

document.addEventListener("htmx:afterSwap", () => {
  updateLeaderboardPagination();
  updateActiveButton();
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".page-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const page = parseInt(btn.dataset.page);
      if (!isNaN(page)) {
        currentPage = page;
        updateLeaderboardPagination();
        updateActiveButton();
      }
    });
  });
});

document.getElementById("next-page")?.addEventListener("click", () => {
  const maxPage = Math.ceil(totalResearchers / rowsPerPage);
  if (currentPage < maxPage) {
    currentPage++;
    updateLeaderboardPagination();
    updateActiveButton();
  }
});

document.getElementById("prev-page")?.addEventListener("click", () => {
  if (currentPage > 1) {
    currentPage--;
    updateLeaderboardPagination();
    updateActiveButton();
  }
});