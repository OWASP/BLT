const TIMER_KEY = 'blt_timer_active_session';

let currentUser = null;
let logs = [];
let timer = loadTimer();
let ticker = null;
let pendingLog = null;
let searchTimeout = null;

const $ = (selector) => document.querySelector(selector);

function loadTimer() {
  try {
    return JSON.parse(localStorage.getItem(TIMER_KEY)) || emptyTimer();
  } catch (_error) {
    return emptyTimer();
  }
}

function emptyTimer() {
  return { running: false, paused: false, startedAt: null, elapsedBeforePause: 0, pausedAt: null };
}

function saveTimer() {
  localStorage.setItem(TIMER_KEY, JSON.stringify(timer));
}

function clearTimer() {
  timer = emptyTimer();
  localStorage.removeItem(TIMER_KEY);
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const h = String(Math.floor(total / 3600)).padStart(2, '0');
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
  const s = String(total % 60).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function formatShort(seconds) {
  const minutes = Math.round((seconds || 0) / 60);
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h}h ${m}m` : `${m}m`;
}

function nowElapsed() {
  if (!timer.running) return 0;
  if (timer.paused) return timer.elapsedBeforePause || 0;
  return Math.floor((Date.now() - timer.startedAt) / 1000) + (timer.elapsedBeforePause || 0);
}

function showToast(message, isError = false) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.toggle('text-red-700', isError);
  toast.classList.remove('hidden');
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => toast.classList.add('hidden'), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  });
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof data === 'object' ? data.error : data;
    throw new Error(message || 'Request failed');
  }
  return data;
}

async function requireUser() {
  try {
    const data = await api('/api/me');
    currentUser = data.user;
    const name = currentUser.displayName || currentUser.username || currentUser.email;
    $('#user-label').textContent = name;
    $('#sidebar-name').textContent = name;
    $('#avatar-initials').textContent = initials(name);
  } catch (_error) {
    window.location.href = '/login';
  }
}

function initials(name) {
  return String(name || 'U').split(/\s|@|-/).filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join('') || 'U';
}

function rangeStartMs(rangeName) {
  const now = new Date();
  if (rangeName === 'today') {
    return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  }
  if (rangeName === 'week') {
    return Date.now() - 7 * 24 * 60 * 60 * 1000;
  }
  if (rangeName === 'month') {
    return Date.now() - 30 * 24 * 60 * 60 * 1000;
  }
  return null;
}

function buildLogQueryParams() {
  const params = new URLSearchParams({ limit: '100' });
  const range = $('#range-filter')?.value || 'week';
  const start = rangeStartMs(range);
  if (start !== null) params.set('start', String(start));
  const query = ($('#search-input')?.value || '').trim();
  if (query) params.set('q', query);
  return params;
}

async function loadLogs() {
  const params = buildLogQueryParams();
  const data = await api(`/api/logs?${params.toString()}`);
  logs = data.logs || [];
  renderLogs();
  await loadStats();
}

async function loadStats() {
  const week = await api('/api/stats?range=week');
  const today = await api('/api/stats?range=today');
  $('#today-total').textContent = formatShort(today.totalSeconds || 0);
  $('#session-count').textContent = String(today.sessions || 0);
  $('#week-total').textContent = formatShort(week.totalSeconds || 0);
}

function renderLogs() {
  const query = ($('#search-input').value || '').toLowerCase();
  const visible = logs.filter((log) => !query || `${log.title} ${log.project || ''} ${log.notes || ''}`.toLowerCase().includes(query));
  $('#empty-logs').classList.toggle('hidden', visible.length > 0);
  $('#log-list').innerHTML = visible.slice(0, 5).map(renderLogCard).join('');
  $('#history-table').innerHTML = visible.map(renderHistoryRow).join('');
}

function logActions(logId) {
  const safeId = escapeHtml(logId);
  return `<div class="flex flex-wrap gap-2"><button class="btn-secondary px-3 py-2 text-xs" type="button" data-action="edit-log" data-log-id="${safeId}">Edit</button><button class="btn-danger px-3 py-2 text-xs" type="button" data-action="delete-log" data-log-id="${safeId}">Delete</button></div>`;
}

function renderLogCard(log) {
  return `<article class="log-card"><div class="flex flex-col justify-between gap-3 md:flex-row md:items-start"><div><h3 class="font-semibold text-slate-950">${escapeHtml(log.title)}</h3><p class="mt-1 text-sm text-slate-500">${escapeHtml(log.project || 'No project')} · ${escapeHtml(log.referenceUrl || 'No reference')}</p><p class="mt-2 text-sm leading-6 text-slate-600">${escapeHtml(log.notes || 'No notes added.')}</p></div><span class="duration-badge">${formatShort(log.durationSeconds)}</span></div><div class="mt-3 flex flex-col justify-between gap-3 text-xs font-medium uppercase tracking-wide text-slate-400 md:flex-row md:items-center"><span>${formatTime(log.startTime)} — ${formatTime(log.endTime)}</span>${logActions(log.id)}</div></article>`;
}

function renderHistoryRow(log) {
  return `<tr><td class="px-4 py-3 font-medium text-slate-950">${escapeHtml(log.title)}</td><td class="px-4 py-3 text-slate-600">${escapeHtml(log.project || '—')}</td><td class="px-4 py-3 text-slate-500">${formatTime(log.startTime)} — ${formatTime(log.endTime)}</td><td class="px-4 py-3 text-slate-950">${formatShort(log.durationSeconds)}</td><td class="px-4 py-3">${logActions(log.id)}</td></tr>`;
}

function formatTime(ms) {
  if (!ms) return '—';
  return new Date(ms).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function updateTimerUi() {
  $('#timer-display').textContent = formatDuration(nowElapsed());
  $('#timer-state').textContent = !timer.running ? 'Ready to start' : timer.paused ? 'Paused' : 'Tracking now';
  $('#start-button').disabled = timer.running;
  $('#pause-button').disabled = !timer.running || timer.paused;
  $('#stop-button').disabled = !timer.running;
  $('#resume-button').classList.toggle('hidden', !timer.paused);
  $('#pause-button').classList.toggle('hidden', timer.paused);
}

function tick() {
  window.clearInterval(ticker);
  ticker = window.setInterval(() => {
    updateTimerUi();
    saveTimer();
  }, 1000);
  updateTimerUi();
}

function startTimer() {
  timer = { running: true, paused: false, startedAt: Date.now(), elapsedBeforePause: 0, pausedAt: null };
  saveTimer();
  tick();
  showToast('Timer started');
}

function pauseTimer() {
  if (!timer.running || timer.paused) return;
  timer.elapsedBeforePause = nowElapsed();
  timer.paused = true;
  timer.pausedAt = Date.now();
  saveTimer();
  updateTimerUi();
}

function resumeTimer() {
  if (!timer.running || !timer.paused) return;
  timer.paused = false;
  timer.startedAt = Date.now();
  timer.pausedAt = null;
  saveTimer();
  tick();
}

function setModalMode(mode) {
  const isEdit = mode === 'edit';
  $('#save-log-title').textContent = isEdit ? 'Edit work log' : 'Save work log';
  $('#save-log-help').textContent = isEdit
    ? 'Update the saved title, notes, project, or reference. Timer values stay unchanged.'
    : 'Confirm the details before adding this session to history. Edit work log details later from the history table.';
  $('#save-log-button').textContent = isEdit ? 'Update work log' : 'Save work log';
  $('#discard-log-button').textContent = isEdit ? 'Cancel' : 'Discard';
}

function fillModalFromLog(log) {
  $('#modal-title').value = log.title || '';
  $('#modal-project').value = log.project || '';
  $('#modal-reference').value = log.referenceUrl || '';
  $('#modal-notes').value = log.notes || '';
  $('#modal-start').textContent = formatTime(log.startTime);
  $('#modal-end').textContent = formatTime(log.endTime);
  $('#modal-duration').textContent = formatDuration(log.durationSeconds || 0);
}

function stopTimer() {
  if (!timer.running) return;
  const durationSeconds = nowElapsed();
  const endTime = Date.now();
  const startTime = endTime - durationSeconds * 1000;
  pendingLog = { mode: 'create', startTime, endTime, durationSeconds };
  fillModalFromLog({
    title: $('#task-title').value.trim() || 'Untitled BLT work',
    project: $('#project-name').value.trim(),
    referenceUrl: $('#reference-url').value.trim(),
    notes: '',
    startTime,
    endTime,
    durationSeconds
  });
  setModalMode('create');
  openModal();
}

function openManualLog() {
  const endTime = Date.now();
  pendingLog = { mode: 'create', startTime: endTime - 30 * 60 * 1000, endTime, durationSeconds: 1800, manual: true };
  fillModalFromLog({
    title: $('#task-title').value.trim() || '',
    project: $('#project-name').value.trim(),
    referenceUrl: $('#reference-url').value.trim(),
    notes: '',
    startTime: pendingLog.startTime,
    endTime: pendingLog.endTime,
    durationSeconds: pendingLog.durationSeconds
  });
  setModalMode('create');
  openModal();
}

function openEditLog(logId) {
  const log = logs.find((item) => item.id === logId);
  if (!log) {
    showToast('Could not find that log', true);
    return;
  }
  pendingLog = {
    mode: 'edit',
    logId,
    startTime: log.startTime,
    endTime: log.endTime,
    durationSeconds: log.durationSeconds
  };
  fillModalFromLog(log);
  setModalMode('edit');
  openModal();
}

function openModal() {
  $('#save-log-modal').classList.add('active');
}

function closeModal() {
  $('#save-log-modal').classList.remove('active');
}

function logPayloadFromModal() {
  const title = $('#modal-title').value.trim();
  if (!title) {
    throw new Error('Title is required');
  }
  return {
    title,
    notes: $('#modal-notes').value.trim(),
    project: $('#modal-project').value.trim(),
    referenceUrl: $('#modal-reference').value.trim(),
    source: 'web',
    startTime: pendingLog.startTime,
    endTime: pendingLog.endTime,
    durationSeconds: pendingLog.durationSeconds
  };
}

async function saveLog() {
  if (!pendingLog) return;
  let payload;
  try {
    payload = logPayloadFromModal();
  } catch (error) {
    showToast(error.message, true);
    return;
  }

  if (pendingLog.mode === 'edit') {
    await api(`/api/logs/${encodeURIComponent(pendingLog.logId)}`, { method: 'PATCH', body: JSON.stringify(payload) });
    pendingLog = null;
    closeModal();
    await loadLogs();
    showToast('Work log updated');
    return;
  }

  await api('/api/logs', { method: 'POST', body: JSON.stringify(payload) });
  pendingLog = null;
  clearTimer();
  closeModal();
  updateTimerUi();
  await loadLogs();
  showToast('Work log saved');
}

function discardLog() {
  const wasEdit = pendingLog?.mode === 'edit';
  pendingLog = null;
  if (!wasEdit) clearTimer();
  closeModal();
  updateTimerUi();
}

async function deleteLog(logId) {
  const ok = window.confirm('Delete this work log? This cannot be undone.');
  if (!ok) return;
  await api(`/api/logs/${encodeURIComponent(logId)}`, { method: 'DELETE', body: '{}' });
  await loadLogs();
  showToast('Work log deleted');
}

function handleLogAction(event) {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const logId = button.dataset.logId;
  if (!logId) return;
  if (button.dataset.action === 'edit-log') openEditLog(logId);
  if (button.dataset.action === 'delete-log') deleteLog(logId).catch((error) => showToast(error.message, true));
}

async function logout() {
  await api('/api/auth/logout', { method: 'POST', body: '{}' }).catch(() => null);
  window.location.href = '/login';
}

function escapeHtml(value) {
  return String(value || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

function debounceLoadLogs() {
  window.clearTimeout(searchTimeout);
  searchTimeout = window.setTimeout(() => loadLogs().catch((error) => showToast(error.message, true)), 250);
}

function bindEvents() {
  $('#start-button').addEventListener('click', startTimer);
  $('#pause-button').addEventListener('click', pauseTimer);
  $('#resume-button').addEventListener('click', resumeTimer);
  $('#stop-button').addEventListener('click', stopTimer);
  $('#manual-log-button').addEventListener('click', openManualLog);
  $('#close-modal-button').addEventListener('click', closeModal);
  $('#discard-log-button').addEventListener('click', discardLog);
  $('#save-log-button').addEventListener('click', () => saveLog().catch((error) => showToast(error.message, true)));
  $('#logout-button').addEventListener('click', logout);
  $('#search-input').addEventListener('input', debounceLoadLogs);
  $('#range-filter').addEventListener('change', () => loadLogs().catch((error) => showToast(error.message, true)));
  $('#refresh-logs-button').addEventListener('click', () => loadLogs().catch((error) => showToast(error.message, true)));
  $('#log-list').addEventListener('click', handleLogAction);
  $('#history-table').addEventListener('click', handleLogAction);
}

async function boot() {
  bindEvents();
  await requireUser();
  await loadLogs();
  updateTimerUi();
  if (timer.running && !timer.paused) tick();
}

boot().catch((error) => showToast(error.message, true));
