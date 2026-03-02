/**
 * BLT-SafeCloak — notes.js
 * Encrypted AI notes with Web Crypto API (AES-GCM) + client-side AI features
 */

const NotesApp = (() => {
  const STORAGE_KEY = 'safecloak_notes_v1';
  const PASS_KEY = 'safecloak_notes_pass';
  const PREVIEW_LENGTH = 60;
  const STOPWORDS = new Set(['the','a','an','and','or','but','in','on','at','to','for','of','with','by','is','was','are','were','be','been','have','has','had','do','does','did','will','would','could','should','may','might','this','that','these','those','it','its','i','you','we','they','he','she','his','her','our','your','their']);
  let notes = [];
  let activeNoteId = null;
  let passphrase = null;
  let saveTimer = null;

  /* ── Persistence ── */
  function getPassphrase() {
    if (passphrase) return passphrase;
    // Derive a device-session passphrase from a stored random key
    let stored = localStorage.getItem(PASS_KEY);
    if (!stored) {
      stored = Crypto.randomId(24);
      localStorage.setItem(PASS_KEY, stored);
    }
    passphrase = stored;
    return passphrase;
  }

  async function saveNotes() {
    try {
      await Crypto.saveEncrypted(STORAGE_KEY, notes, getPassphrase());
    } catch (err) {
      console.error('Failed to save notes:', err);
    }
  }

  async function loadNotes() {
    try {
      const loaded = await Crypto.loadEncrypted(STORAGE_KEY, getPassphrase());
      notes = loaded || [];
    } catch {
      notes = [];
    }
  }

  /* ── Note CRUD ── */
  function createNote() {
    const note = {
      id: Date.now().toString(),
      title: 'Untitled Note',
      content: '',
      tags: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    notes.unshift(note);
    scheduleSave();
    renderNotesList();
    setActiveNote(note.id);
    document.getElementById('note-title') && document.getElementById('note-title').focus();
    showToast('New note created', 'success');
    return note;
  }

  function deleteNote(id) {
    if (!confirm('Delete this note? This cannot be undone.')) return;
    notes = notes.filter(n => n.id !== id);
    scheduleSave();
    if (activeNoteId === id) {
      activeNoteId = notes[0] ? notes[0].id : null;
    }
    renderNotesList();
    renderEditor();
    showToast('Note deleted', 'info');
  }

  function updateActiveNote() {
    if (!activeNoteId) return;
    const note = notes.find(n => n.id === activeNoteId);
    if (!note) return;
    const title = document.getElementById('note-title');
    const body = document.getElementById('note-body');
    if (title) note.title = title.value || 'Untitled Note';
    if (body) note.content = body.value;
    note.updatedAt = Date.now();
    // Update list without full re-render
    const item = document.querySelector(`.note-item[data-id="${activeNoteId}"]`);
    if (item) {
      item.querySelector('.note-item-title').textContent = note.title;
      item.querySelector('.note-item-preview').textContent = note.content.slice(0, PREVIEW_LENGTH);
      item.querySelector('.note-item-date').textContent = formatDateShort(note.updatedAt);
    }
    scheduleSave();
  }

  function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      saveNotes();
    }, 800);
  }

  /* ── Rendering ── */
  function renderNotesList() {
    const container = document.getElementById('notes-list');
    if (!container) return;
    if (!notes.length) {
      container.innerHTML = `<div class="text-muted text-small" style="padding:1rem;text-align:center">No notes yet.<br>Click <strong>+ New</strong> to create one.</div>`;
      return;
    }
    container.innerHTML = notes.map(n => `
      <div class="note-item${n.id === activeNoteId ? ' active' : ''}" data-id="${n.id}" tabindex="0" role="button">
        <div class="note-item-title">${escHtml(n.title)}</div>
        <div class="note-item-preview">${escHtml(n.content.slice(0, PREVIEW_LENGTH))}</div>
        <div class="note-item-date">${formatDateShort(n.updatedAt)}</div>
      </div>
    `).join('');

    container.querySelectorAll('.note-item').forEach(el => {
      el.addEventListener('click', () => setActiveNote(el.dataset.id));
      el.addEventListener('keydown', e => { if (e.key === 'Enter') setActiveNote(el.dataset.id); });
    });
  }

  function setActiveNote(id) {
    activeNoteId = id;
    renderNotesList();
    renderEditor();
  }

  function renderEditor() {
    const note = notes.find(n => n.id === activeNoteId);
    const title = document.getElementById('note-title');
    const body = document.getElementById('note-body');
    const empty = document.getElementById('editor-empty');
    const editorWrapper = document.getElementById('editor-wrapper');
    const aiOutput = document.getElementById('ai-output');

    if (!note) {
      if (title) title.value = '';
      if (body) body.value = '';
      if (empty) empty.style.display = 'flex';
      if (editorWrapper) editorWrapper.style.display = 'none';
      return;
    }

    if (empty) empty.style.display = 'none';
    if (editorWrapper) editorWrapper.style.display = 'flex';
    if (title) title.value = note.title;
    if (body) body.value = note.content;
    if (aiOutput) aiOutput.textContent = '';

    // Update word count
    updateWordCount(note.content);
  }

  function updateWordCount(text) {
    const wc = document.getElementById('word-count');
    if (!wc) return;
    const words = text.trim().split(/\s+/).filter(Boolean).length;
    const chars = text.length;
    wc.textContent = `${words} words · ${chars} chars`;
  }

  /* ── AI Features (client-side text processing) ── */
  function summarize(text) {
    if (!text.trim()) return '(no content to summarize)';
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
    // Score sentences by keyword frequency
    const words = text.toLowerCase().split(/\s+/).filter(w => w.length > 4);
    const freq = {};
    words.forEach(w => { freq[w] = (freq[w] || 0) + 1; });
    const scored = sentences.map(s => ({
      s,
      score: s.toLowerCase().split(/\s+/).reduce((sum, w) => sum + (freq[w] || 0), 0)
    })).sort((a, b) => b.score - a.score);
    // Top 3 sentences in original order
    const top = scored.slice(0, Math.min(3, scored.length)).map(x => x.s.trim());
    const indices = top.map(t => sentences.indexOf(t)).sort((a, b) => a - b);
    return '📝 Summary:\n' + indices.map(i => sentences[i].trim()).join(' ');
  }

  function extractKeyPoints(text) {
    if (!text.trim()) return '(no content)';
    const lines = text.split('\n').filter(l => l.trim().length > 10);
    // Find lines with action words or emphasis
    const keywords = /\b(must|need|should|important|key|note|action|todo|decision|agree|consent|record|encrypt|secure|protect)\b/i;
    const keyLines = lines.filter(l => keywords.test(l));
    const result = keyLines.length > 0 ? keyLines : lines.slice(0, 5);
    return '🔑 Key Points:\n' + result.slice(0, 7).map(l => `• ${l.trim()}`).join('\n');
  }

  function extractActionItems(text) {
    if (!text.trim()) return '(no content)';
    const actionWords = /\b(todo|action|follow.?up|remind|schedule|send|review|check|complete|assign|deadline)\b/i;
    const lines = text.split('\n').filter(l => actionWords.test(l) && l.trim().length > 5);
    if (!lines.length) return '✅ No explicit action items found.\n\nTip: include words like "todo", "action", "follow up", or "deadline" to auto-detect action items.';
    return '✅ Action Items:\n' + lines.slice(0, 10).map(l => `• ${l.trim()}`).join('\n');
  }

  function wordFrequency(text) {
    if (!text.trim()) return '(no content)';
    const words = text.toLowerCase().match(/\b[a-z]{3,}\b/g) || [];
    const freq = {};
    words.filter(w => !STOPWORDS.has(w)).forEach(w => { freq[w] = (freq[w] || 0) + 1; });
    const top = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 10);
    if (!top.length) return '(no significant words)';
    return '📊 Top Keywords:\n' + top.map(([w, c]) => `• ${w} (${c}x)`).join('\n');
  }

  /* ── Export ── */
  function exportNote(format = 'txt') {
    const note = notes.find(n => n.id === activeNoteId);
    if (!note) return;
    let content, mime, ext;
    if (format === 'json') {
      content = JSON.stringify({ ...note, exported: new Date().toISOString() }, null, 2);
      mime = 'application/json';
      ext = 'json';
    } else if (format === 'md') {
      content = `# ${note.title}\n\n*Created: ${new Date(note.createdAt).toISOString()}*\n*Updated: ${new Date(note.updatedAt).toISOString()}*\n\n---\n\n${note.content}`;
      mime = 'text/markdown';
      ext = 'md';
    } else {
      content = `${note.title}\n${'='.repeat(note.title.length)}\nCreated: ${new Date(note.createdAt).toLocaleString()}\nUpdated: ${new Date(note.updatedAt).toLocaleString()}\n\n${note.content}`;
      mime = 'text/plain';
      ext = 'txt';
    }
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${note.title.replace(/[^a-zA-Z0-9]/g, '_')}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`Note exported as .${ext}`, 'success');
  }

  function exportAllNotes() {
    const content = JSON.stringify({ notes, exported: new Date().toISOString() }, null, 2);
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `safecloak_notes_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`${notes.length} notes exported`, 'success');
  }

  /* ── Utils ── */
  function escHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ── Init ── */
  async function init() {
    await loadNotes();
    renderNotesList();
    if (notes.length > 0) setActiveNote(notes[0].id);

    // Wire up editor inputs
    const titleEl = document.getElementById('note-title');
    const bodyEl = document.getElementById('note-body');
    if (titleEl) titleEl.addEventListener('input', () => { updateActiveNote(); });
    if (bodyEl) bodyEl.addEventListener('input', () => { updateActiveNote(); updateWordCount(bodyEl.value); });

    // Wire up toolbar buttons
    document.getElementById('btn-new-note') && document.getElementById('btn-new-note').addEventListener('click', createNote);
    document.getElementById('btn-delete-note') && document.getElementById('btn-delete-note').addEventListener('click', () => deleteNote(activeNoteId));
    document.getElementById('btn-export-txt') && document.getElementById('btn-export-txt').addEventListener('click', () => exportNote('txt'));
    document.getElementById('btn-export-md') && document.getElementById('btn-export-md').addEventListener('click', () => exportNote('md'));
    document.getElementById('btn-export-json') && document.getElementById('btn-export-json').addEventListener('click', () => exportNote('json'));
    document.getElementById('btn-export-all') && document.getElementById('btn-export-all').addEventListener('click', exportAllNotes);

    // AI buttons
    document.getElementById('btn-summarize') && document.getElementById('btn-summarize').addEventListener('click', () => {
      const note = notes.find(n => n.id === activeNoteId);
      if (!note) return showToast('No note selected', 'warning');
      const out = document.getElementById('ai-output');
      if (out) out.textContent = summarize(note.content);
    });

    document.getElementById('btn-keypoints') && document.getElementById('btn-keypoints').addEventListener('click', () => {
      const note = notes.find(n => n.id === activeNoteId);
      if (!note) return showToast('No note selected', 'warning');
      const out = document.getElementById('ai-output');
      if (out) out.textContent = extractKeyPoints(note.content);
    });

    document.getElementById('btn-actions') && document.getElementById('btn-actions').addEventListener('click', () => {
      const note = notes.find(n => n.id === activeNoteId);
      if (!note) return showToast('No note selected', 'warning');
      const out = document.getElementById('ai-output');
      if (out) out.textContent = extractActionItems(note.content);
    });

    document.getElementById('btn-keywords') && document.getElementById('btn-keywords').addEventListener('click', () => {
      const note = notes.find(n => n.id === activeNoteId);
      if (!note) return showToast('No note selected', 'warning');
      const out = document.getElementById('ai-output');
      if (out) out.textContent = wordFrequency(note.content);
    });
  }

  return { init, createNote, deleteNote, exportNote, exportAllNotes, notes: () => notes };
})();

document.addEventListener('DOMContentLoaded', () => NotesApp.init());
