/**
 * BLT-SafeCloak — consent.js
 * Consent protection: record, timestamp, hash, store, and export consent events
 */

const ConsentManager = (() => {
  const STORAGE_KEY = 'safecloak_consent_log_v1';
  let log = [];

  /* ── Load / Save ── */
  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      log = raw ? JSON.parse(raw) : [];
    } catch { log = []; }
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(log));
    } catch (err) {
      console.error('Failed to save consent log:', err);
    }
  }

  /* ── Record a consent event ── */
  async function record(event) {
    const ts = Date.now();
    const entry = {
      id: ts.toString() + Math.random().toString(36).slice(2, 7),
      type: event.type || 'recorded',        // 'given' | 'withdrawn' | 'recorded'
      name: event.name || 'Unnamed event',
      details: event.details || '',
      purpose: event.purpose || '',
      participants: event.participants || [],
      timestamp: ts,
      isoTime: new Date(ts).toISOString(),
      userAgent: navigator.userAgent.slice(0, 100),
    };
    // Create a tamper-evident hash of the entry data
    try {
      const data = `${entry.type}|${entry.name}|${entry.isoTime}|${entry.details}`;
      entry.hash = await Crypto.sha256(data);
    } catch { entry.hash = 'hash-unavailable'; }

    log.unshift(entry);
    save();
    return entry;
  }

  /* ── Rendering ── */
  function renderLog(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!log.length) {
      container.innerHTML = `<div class="text-muted text-small" style="padding:1rem;text-align:center">No consent events recorded yet.</div>`;
      return;
    }
    container.innerHTML = log.map(entry => `
      <div class="consent-entry" data-id="${entry.id}">
        <div class="consent-entry-header">
          <span class="consent-entry-type ${entry.type}">${capitalise(entry.type)}</span>
          <span class="consent-entry-time">${formatDateTime(entry.timestamp)}</span>
        </div>
        <div class="consent-entry-name">${escHtml(entry.name)}</div>
        ${entry.details ? `<div class="consent-entry-details">${escHtml(entry.details)}</div>` : ''}
        ${entry.purpose ? `<div class="consent-entry-details text-secondary" style="margin-top:0.2rem">Purpose: ${escHtml(entry.purpose)}</div>` : ''}
        <div class="consent-entry-hash" title="Integrity hash">🔏 ${entry.hash}</div>
        <div style="margin-top:0.5rem;display:flex;gap:0.5rem">
          <button class="btn btn-sm btn-secondary" onclick="ConsentManager.verifyEntry('${entry.id}')">Verify</button>
          <button class="btn btn-sm btn-danger" onclick="ConsentManager.deleteEntry('${entry.id}')">Delete</button>
        </div>
      </div>
    `).join('');
  }

  /* ── Verify a specific entry ── */
  async function verifyEntry(id) {
    const entry = log.find(e => e.id === id);
    if (!entry) return showToast('Entry not found', 'error');
    try {
      const data = `${entry.type}|${entry.name}|${entry.isoTime}|${entry.details}`;
      const hash = await Crypto.sha256(data);
      if (hash === entry.hash) {
        showToast('✅ Entry integrity verified — untampered', 'success');
      } else {
        showToast('⚠️ Hash mismatch — entry may have been tampered with!', 'error');
      }
    } catch {
      showToast('Verification failed', 'error');
    }
  }

  /* ── Delete entry ── */
  function deleteEntry(id) {
    if (!confirm('Delete this consent record? This cannot be undone.')) return;
    log = log.filter(e => e.id !== id);
    save();
    renderLog('consent-log');
    showToast('Consent record deleted', 'info');
    updateStats();
  }

  /* ── Export ── */
  function exportLog(format = 'json') {
    const exportData = {
      exportedAt: new Date().toISOString(),
      exportedBy: 'BLT-SafeCloak',
      version: '1.0',
      totalEntries: log.length,
      entries: log
    };

    let content, mime, ext;
    if (format === 'csv') {
      const headers = 'ID,Type,Name,Details,Purpose,Timestamp,ISO Time,Hash';
      const rows = log.map(e =>
        [e.id, e.type, `"${e.name.replace(/"/g, '""')}"`, `"${e.details.replace(/"/g, '""')}"`,
         `"${e.purpose.replace(/"/g, '""')}"`, e.timestamp, e.isoTime, e.hash].join(',')
      );
      content = [headers, ...rows].join('\n');
      mime = 'text/csv';
      ext = 'csv';
    } else {
      content = JSON.stringify(exportData, null, 2);
      mime = 'application/json';
      ext = 'json';
    }

    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `safecloak_consent_${Date.now()}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`Consent log exported as .${ext}`, 'success');
  }

  /* ── Stats ── */
  function updateStats() {
    const totalEl = document.getElementById('stat-total');
    const givenEl = document.getElementById('stat-given');
    const withdrawnEl = document.getElementById('stat-withdrawn');
    const recordedEl = document.getElementById('stat-recorded');
    if (totalEl) totalEl.textContent = log.length;
    if (givenEl) givenEl.textContent = log.filter(e => e.type === 'given').length;
    if (withdrawnEl) withdrawnEl.textContent = log.filter(e => e.type === 'withdrawn').length;
    if (recordedEl) recordedEl.textContent = log.filter(e => e.type === 'recorded').length;
  }

  /* ── Utils ── */
  function capitalise(s) { return s ? s[0].toUpperCase() + s.slice(1) : ''; }
  function escHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ── Init ── */
  async function init() {
    load();
    renderLog('consent-log');
    updateStats();

    // Record form
    const form = document.getElementById('consent-form');
    if (form) {
      form.addEventListener('submit', async e => {
        e.preventDefault();
        const fd = new FormData(form);
        const entry = await record({
          type: fd.get('consent-type'),
          name: fd.get('participant-name'),
          details: fd.get('details'),
          purpose: fd.get('purpose'),
        });
        renderLog('consent-log');
        updateStats();
        form.reset();
        showToast('Consent recorded & hashed', 'success');
      });
    }

    // Export buttons
    document.getElementById('btn-export-json') && document.getElementById('btn-export-json').addEventListener('click', () => exportLog('json'));
    document.getElementById('btn-export-csv') && document.getElementById('btn-export-csv').addEventListener('click', () => exportLog('csv'));

    // Clear all
    document.getElementById('btn-clear-log') && document.getElementById('btn-clear-log').addEventListener('click', () => {
      if (!confirm('Clear ALL consent records? This cannot be undone.')) return;
      log = [];
      save();
      renderLog('consent-log');
      updateStats();
      showToast('Consent log cleared', 'info');
    });
  }

  return { init, record, verifyEntry, deleteEntry, exportLog, getLog: () => log, renderLog, updateStats };
})();

document.addEventListener('DOMContentLoaded', () => ConsentManager.init());
