export const TIMER_KEY = 'blt_timer_active_session';

const NAV_ITEMS = [
  { id: 'timer', href: '/dashboard', icon: '◴', label: 'Timer' },
  { id: 'logs', href: '/logs', icon: '◷', label: 'Recent logs' },
  { id: 'history', href: '/history', icon: '▤', label: 'History' },
  { id: 'settings', href: '/settings', icon: '⚙', label: 'Settings' }
];

export async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  });
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(typeof data === 'object' ? data.error : data || 'Request failed');
  }
  return data;
}

export function emptyTimer() {
  return { running: false, paused: false, startedAt: null, elapsedBeforePause: 0, pausedAt: null };
}

export function loadTimer() {
  try {
    return JSON.parse(localStorage.getItem(TIMER_KEY)) || emptyTimer();
  } catch (_error) {
    return emptyTimer();
  }
}

export function saveTimer(timer) {
  localStorage.setItem(TIMER_KEY, JSON.stringify(timer));
}

export function clearTimer() {
  localStorage.removeItem(TIMER_KEY);
}

export function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const hours = String(Math.floor(total / 3600)).padStart(2, '0');
  const minutes = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
  const remainder = String(total % 60).padStart(2, '0');
  return `${hours}:${minutes}:${remainder}`;
}

export function formatShort(seconds) {
  const minutes = Math.round((seconds || 0) / 60);
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return hours ? `${hours}h ${remainder}m` : `${remainder}m`;
}

export function formatDateTime(ms) {
  if (!ms) return 'Not set';
  return new Date(ms).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export function toDateTimeLocalValue(ms) {
  const date = new Date(ms);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function initials(name) {
  return String(name || 'U')
    .split(/\s|@|-/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('') || 'U';
}

export function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function navigationMarkup(pageId) {
  return NAV_ITEMS.map(({ id, href, icon, label }) => {
    const isActive = pageId === id;
    return `<a class="sidebar-item ${isActive ? 'active' : ''}" href="${href}"${isActive ? ' aria-current="page"' : ''}><span aria-hidden="true">${icon}</span><span>${label}</span></a>`;
  }).join('');
}

export function updateDashboardUser(user) {
  const name = user.displayName || user.username || user.email;
  const avatar = initials(name);
  document.querySelectorAll('[data-user-name]').forEach((element) => {
    element.textContent = name;
  });
  document.querySelectorAll('[data-user-initials]').forEach((element) => {
    element.textContent = avatar;
  });
}

export function showPageMessage(message, { isError = false, onRetry = null } = {}) {
  const region = document.querySelector('#page-message');
  if (!region) return;
  region.innerHTML = '';
  region.classList.remove('hidden', 'page-alert-error', 'page-alert-success');
  region.classList.add(isError ? 'page-alert-error' : 'page-alert-success');
  const text = document.createElement('span');
  text.textContent = message;
  region.append(text);
  if (onRetry) {
    const retry = document.createElement('button');
    retry.type = 'button';
    retry.className = 'btn-secondary px-3 py-2 text-xs';
    retry.textContent = 'Retry';
    retry.addEventListener('click', onRetry);
    region.append(retry);
  }
}

export async function logout() {
  await api('/api/auth/logout', { method: 'POST', body: '{}' }).catch(() => null);
  window.location.href = '/login';
}

export async function mountDashboardShell(pageId, { title, content }) {
  const root = document.querySelector('#dashboard-root');
  if (!root) throw new Error('Dashboard root is missing');

  root.innerHTML = `
    <div class="dashboard-shell">
      <aside class="dashboard-sidebar" aria-label="Dashboard navigation">
        <a class="dashboard-brand" href="/dashboard" aria-label="BLT Timer dashboard"><img class="dashboard-brand-logo" src="/assets/logo.png" alt="" /><span>BLT<br />Timer</span></a>
        <p class="sidebar-label">Workspace</p>
        <nav class="dashboard-navigation">${navigationMarkup(pageId)}</nav>
        <div class="dashboard-sidebar-footer">
          <div class="dashboard-user-card"><span class="dashboard-avatar" data-user-initials>--</span><strong data-user-name>Loading</strong></div>
          <button id="logout-button" class="sidebar-item sidebar-button" type="button"><span aria-hidden="true">⇥</span><span>Log out</span></button>
        </div>
      </aside>
      <div class="dashboard-main">
        <header class="dashboard-page-header">
          <div><h1>${title}</h1></div>
          <span class="dashboard-avatar" data-user-initials aria-label="Signed in user">--</span>
        </header>
        <main class="dashboard-page-content">
          <div id="page-message" class="page-alert hidden" role="status" aria-live="polite"></div>
          ${content}
        </main>
      </div>
    </div>`;

  document.querySelector('#logout-button').addEventListener('click', logout);

  try {
    const { user } = await api('/api/me');
    updateDashboardUser(user);
    return user;
  } catch (_error) {
    window.location.href = '/login';
    return null;
  }
}
