/**
 * BLT-SafeCloak — ui.js
 * Shared UI utilities: toasts, navbar toggle, modal helpers
 */

/* ── Toast notifications ── */
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container') || (() => {
    const el = document.createElement('div');
    el.id = 'toast-container';
    document.body.appendChild(el);
    return el;
  })();

  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const toast = document.createElement('div');
  toast.className = `toast toast-${type === 'error' ? 'error' : type === 'success' ? 'success' : 'info'}`;
  toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* ── Navbar toggle ── */
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('navbar-toggle');
  const nav = document.getElementById('navbar-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
    // Close on outside click
    document.addEventListener('click', e => {
      if (!toggle.contains(e.target) && !nav.contains(e.target)) {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Mark active nav link
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  const links = document.querySelectorAll('.navbar-nav a');
  links.forEach(link => {
    const href = link.getAttribute('href');
    if (link.href === window.location.href || href === currentPage) {
      link.classList.add('active');
    }
  });
});

/* ── Modal helpers ── */
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = 'flex';
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = 'none';
}

// Close modal on overlay click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.style.display = 'none';
  }
});

/* ── Copy to clipboard ── */
async function copyToClipboard(text, label = 'Copied') {
  try {
    await navigator.clipboard.writeText(text);
    showToast(`${label} copied to clipboard`, 'success');
  } catch {
    showToast('Copy failed — please copy manually', 'error');
  }
}

/* ── Format date/time ── */
function formatDateTime(ts) {
  return new Date(ts).toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
}

function formatDateShort(ts) {
  const d = new Date(ts);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString();
}
