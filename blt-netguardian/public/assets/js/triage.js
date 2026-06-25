(function () {
    "use strict";

    document.addEventListener('DOMContentLoaded', function () {
        const authOverlay    = document.getElementById('auth-overlay');
        const tokenInput     = document.getElementById('api-token');
        const saveTokenBtn   = document.getElementById('save-token');
        const authError      = document.getElementById('auth-error');
        const connPill       = document.getElementById('conn-pill');
        const connDot        = document.getElementById('conn-dot');
        const connLabel      = document.getElementById('conn-label');
        const btnAvatar      = document.getElementById('btn-avatar');
        const changeTokenBtn = document.getElementById('change-token-btn');
        const refreshBtn     = document.getElementById('refresh-btn');
        const findingsBody   = document.getElementById('findings-body');
        const findingsCount  = document.getElementById('findings-count');
        const severityFilter = document.getElementById('filter-severity');
        const cveFilter      = document.getElementById('filter-cve');
        const applyBtn       = document.getElementById('apply-filters');
        const viewTableBtn   = document.getElementById('view-table');
        const viewListBtn    = document.getElementById('view-list');
        const toast          = document.getElementById('toast');

        const IS_LOCAL   = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
        const DEMO_TOKEN = 'triage-token';

        let selectedRawId = null;
        let toastTimer = null;
        let currentFindings = [];
        let idIndexMap = {};

        // ── Single permanent delegation listener on tbody ──────────
        if (findingsBody) {
            findingsBody.addEventListener('click', function (e) {
                const row = e.target.closest('tr[data-id]');
                if (!row) return;

                findingsBody.querySelectorAll('tr').forEach(function (r) {
                    r.classList.remove('selected');
                });
                row.classList.add('selected');

                selectedRawId = row.getAttribute('data-raw-id');
                const id       = row.getAttribute('data-id');
                const rule     = row.getAttribute('data-rule');
                const severity = row.getAttribute('data-severity');
                const target   = row.getAttribute('data-target');
                const cve      = row.getAttribute('data-cve') || '—';
                const status   = row.getAttribute('data-status') || 'open';
                const score    = row.getAttribute('data-score') || '—';
                showDetail(id, rule, severity, target, cve, status, score);
            });
        }

        function openDatePicker(input) {
            if (!input) return;
            if (typeof input.showPicker === 'function') {
                try {
                    input.showPicker();
                    return;
                } catch (_) {}
            }
            input.focus();
        }

        document.querySelectorAll('.date-wrap').forEach(function (wrap) {
            const input = wrap.querySelector('input[type="date"]');
            if (!input) return;
            wrap.addEventListener('click', function (e) {
                if (e.target === input) return;
                openDatePicker(input);
            });
            input.addEventListener('click', function () {
                openDatePicker(input);
            });
        });

        function resetDetailPanel() {
            const panel = document.getElementById('detail-panel-content');
            if (!panel) return;
            panel.innerHTML =
                '<div class="detail-placeholder">' +
                '<i class="fa-solid fa-shield-halved"></i>' +
                '<span>Select a finding to view details</span>' +
                '</div>';
        }

        function showDetail(id, rule, severity, target, cve, status, score) {
            const panel = document.getElementById('detail-panel-content');
            if (!panel) return;

            const safeCve = (cve && cve !== '—') ? cve : '';
            const sevKey = String(severity || 'info').toLowerCase();
            const riskNum = score && score !== '—' ? score : (SEV_SCORE[sevKey] || 1);
            const riskWord = riskNum >= 9 ? 'Critical' : riskNum >= 7 ? 'High' : riskNum >= 4 ? 'Medium' : 'Low';
            const statusLabel = status ? (status.charAt(0).toUpperCase() + status.slice(1)) : 'Open';

            panel.innerHTML = `
              <div class="finding-card">
                <div class="finding-card-title">${esc(id)} · ${esc(rule)}</div>

                <div class="detail-tabs">
                  <span class="detail-tab active">Evidence</span>
                  <span class="detail-tab">Risk</span>
                  <span class="detail-tab">Status</span>
                </div>

                <div class="evidence-section">
                  <div class="evidence-label">Redacted Evidence Snippet</div>
                  <div class="evidence-label-small">Evidence</div>
                  <div class="evidence-box">
                    <div class="evidence-text">████████ ███ ████████ ██████</div>
                    <div class="evidence-text">████ ████████████ ████ ████</div>
                    <div class="evidence-text">██████ ████ ███████████ ██</div>
                    <div class="confidential-stamp">confidential</div>
                    <span class="magnify-icon">🔍</span>
                  </div>
                </div>

                <div class="risk-row">
                  <div class="risk-block">
                    <div class="field-label">Likelihood</div>
                    <div class="risk-value risk-num-${riskClass(Number(riskNum)).replace('risk-','')}">${esc(String(riskNum))} ${esc(riskWord)}</div>
                    <ul class="risk-list">
                      <li>Internet exposed surface</li>
                      <li>Active in target environment</li>
                      <li>${esc(safeCve || 'No mapped CVE')}</li>
                    </ul>
                  </div>
                  <div class="risk-block">
                    <div class="field-label">Impact</div>
                    <div class="risk-value risk-num-${sevKey}">${esc(severity)}</div>
                    <ul class="risk-list">
                      <li>${esc(target)}</li>
                      <li>Production-facing</li>
                      <li>Sensitive data path</li>
                    </ul>
                  </div>
                </div>

                <div class="reason-box">
                  <div class="field-label">Reason</div>
                  <div class="summary-text">
                    ${esc(rule)} detected on ${esc(target)}. Severity ${esc(severity)}, status ${esc(statusLabel)}. Immediate review recommended.
                  </div>
                </div>

                <button id="detail-convert-btn" type="button" class="convert-btn">
                  <span>📋</span>
                  <span class="cve-badge">CVE</span>
                  <span>Convert to Issue</span>
                </button>
                <div class="field-label">CVE Link</div>
                <input type="text" class="cve-input" value="${esc(safeCve)}"
                       placeholder="https://cve.mitre.org/..." readonly />
                <button id="detail-export-btn" type="button" class="export-btn">📄 Export CSV</button>
              </div>
            `;

            const convertBtn = document.getElementById('detail-convert-btn');
            const exportBtn = document.getElementById('detail-export-btn');
            if (convertBtn) {
                convertBtn.addEventListener('click', function () {
                    if (selectedRawId) handleConvert(selectedRawId, id);
                });
            }
            if (exportBtn) {
                exportBtn.addEventListener('click', handleExport);
            }

            panel.querySelectorAll('.detail-tab').forEach(function (tab) {
                tab.addEventListener('click', function () {
                    panel.querySelectorAll('.detail-tab').forEach(function (t) { t.classList.remove('active'); });
                    tab.classList.add('active');
                });
            });
        }

        function esc(v) {
            return String(v == null ? '' : v)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        }

        function readStoredToken() {
            try { return localStorage.getItem('ng_api_token'); } catch (_) { return null; }
        }

        function writeStoredToken(t) {
            try { localStorage.setItem('ng_api_token', t); } catch (_) {}
        }

        function showToast(text, kind) {
            if (!toast) return;
            clearTimeout(toastTimer);
            toast.textContent = text;
            toast.className = 'toast show ' + (kind || '');
            toastTimer = setTimeout(function () {
                toast.className = 'toast ' + (kind || '');
            }, 3500);
        }

        function setConnected(ok, label) {
            connDot.className = 'conn-dot' + (ok ? ' live' : '');
            connLabel.textContent = label || (ok ? 'Connected' : 'Offline');
            connPill.classList.toggle('visible', ok);
        }

        function getToken() {
            return tokenInput.value.trim();
        }

        function authHeaders() {
            const t = getToken();
            if (!t) throw new Error('No token.');
            return { Authorization: 'Bearer ' + t };
        }

        async function apiRequest(path, opts) {
            opts = opts || {};
            const res = await fetch(path, {
                method: opts.method || 'GET',
                headers: authHeaders(),
            });
            if (opts.raw) {
                if (!res.ok) throw new Error('Request failed (' + res.status + ')');
                return res;
            }
            let data = {};
            try { data = await res.json(); } catch (_) {}
            if (!res.ok) {
                throw new Error(data.message || data.error || 'Request failed (' + res.status + ')');
            }
            return data;
        }

        function apiErrorMsg(err) {
            if (err && err.message === 'Failed to fetch') {
                return 'Cannot reach the API — run: python3 local_dev/serve.py';
            }
            return err.message || String(err);
        }

        const SEV_MAP = {
            critical: 'sev-critical',
            high: 'sev-high',
            medium: 'sev-medium',
            low: 'sev-low',
            info: 'sev-info',
        };

        const SEV_SCORE = {
            critical: 9,
            high: 7,
            medium: 5,
            low: 3,
            info: 1,
        };

        function sevBadge(v) {
            const key = String(v || 'info').toLowerCase();
            const cls = SEV_MAP[key] || 'sev-info';
            return '<span class="sev ' + cls + '">' + esc(key) + '</span>';
        }

        function riskScore(f) {
            if (f && f.cve_score != null && !isNaN(f.cve_score)) {
                return Math.max(1, Math.min(10, Math.round(Number(f.cve_score))));
            }
            const key = String((f && f.severity) || 'info').toLowerCase();
            return SEV_SCORE[key] || 1;
        }

        function riskClass(score) {
            if (score >= 9) return 'risk-critical';
            if (score >= 7) return 'risk-high';
            if (score >= 4) return 'risk-medium';
            return 'risk-low';
        }

        function riskBadge(f) {
            const score = riskScore(f);
            return '<span class="risk-score ' + riskClass(score) + '">' + score + '</span>';
        }

        function statusPill(s) {
            const key = String(s || 'open').toLowerCase();
            const label = key.charAt(0).toUpperCase() + key.slice(1);
            return '<span class="status-pill status-' + esc(key) + '">' + esc(label) + '</span>';
        }

        function displayId(id) {
            if (!id) return '—';
            if (/^NG-\d{3}$/i.test(id)) return id.toUpperCase();
            if (idIndexMap[id] != null) {
                return 'NG-' + String(idIndexMap[id]).padStart(3, '0');
            }
            return id;
        }

        function buildListQuery() {
            const p = new URLSearchParams({ limit: '100' });
            if (severityFilter.value) p.set('severity', severityFilter.value);
            if (cveFilter.value.trim()) p.set('cve_id', cveFilter.value.trim());
            return p.toString();
        }

        function renderFindings(findings) {
            if (!findingsBody) return;
            currentFindings = findings;
            idIndexMap = {};
            findings.forEach(function (f, i) { idIndexMap[f.id] = i + 1; });

            const stillVisible = findings.some(function (f) { return f.id === selectedRawId; });
            if (!stillVisible) {
                selectedRawId = null;
                resetDetailPanel();
            }

            findingsBody.innerHTML = '';
            if (!findings.length) {
                findingsBody.innerHTML =
                    '<tr><td colspan="7"><div class="empty-state">No findings match the current filters.</div></td></tr>';
                return;
            }

            for (const f of findings) {
                const tr = document.createElement('tr');
                tr.className = 'finding-row';
                if (f.id === selectedRawId) tr.classList.add('selected');
                tr.setAttribute('data-id', displayId(f.id));
                tr.setAttribute('data-raw-id', f.id);
                tr.setAttribute('data-rule', f.rule_id || '—');
                tr.setAttribute('data-severity', String(f.severity || 'info').toUpperCase());
                tr.setAttribute('data-target', f.target || '—');
                tr.setAttribute('data-cve', f.cve_id || '—');
                tr.setAttribute('data-status', f.status || 'open');
                tr.setAttribute('data-score', riskScore(f));
                tr.style.cursor = 'pointer';
                tr.innerHTML =
                    '<td class="cell-id">' + esc(displayId(f.id)) + '</td>' +
                    '<td class="cell-rule" title="' + esc(f.rule_id) + '">' + esc(f.rule_id || '—') + '</td>' +
                    '<td>' + sevBadge(f.severity) + '</td>' +
                    '<td>' + riskBadge(f) + '</td>' +
                    '<td class="cell-target" title="' + esc(f.target) + '">' + esc(f.target || '—') + '</td>' +
                    '<td>' + statusPill(f.status) + '</td>' +
                    '<td class="cell-cve">' + esc(f.cve_id || '—') + '</td>';
                findingsBody.appendChild(tr);
            }
        }

        async function loadList() {
            if (!findingsBody) return;
            findingsBody.innerHTML =
                '<tr><td colspan="7"><div class="empty-state"><div class="spinner"></div>Loading findings…</div></td></tr>';
            try {
                const data = await apiRequest('/api/findings?' + buildListQuery());
                renderFindings(data.findings || []);
                findingsCount.textContent = (data.total || 0) + ' total';
                setConnected(true, data.org_id || 'connected');
                showToast('Loaded ' + (data.findings ? data.findings.length : 0) + ' findings.', 'success');
            } catch (err) {
                setConnected(false, 'Offline');
                findingsBody.innerHTML =
                    '<tr><td colspan="7"><div class="empty-state">' + esc(apiErrorMsg(err)) + '</div></td></tr>';
                findingsCount.textContent = '—';
                throw err;
            }
        }

        async function handleConvert(rawId, displayLabel) {
            if (!rawId) return;
            try {
                const data = await apiRequest(
                    '/api/findings/' + encodeURIComponent(rawId) + '/convert-to-issue',
                    { method: 'POST' }
                );
                const verb = data.status === 'existing' ? 'already linked to' : 'converted to';
                showToast('Finding ' + verb + ' issue ' + data.blt_issue_id + '.', 'success');
                await loadList();
            } catch (err) {
                showToast(apiErrorMsg(err), 'error');
                alert('Converting ' + displayLabel + ' to issue failed: ' + apiErrorMsg(err));
            }
        }

        async function handleExport() {
            try {
                const res = await apiRequest('/api/findings/export.csv?' + buildListQuery(), { raw: true });
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'netguardian-findings.csv';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                showToast('CSV exported.', 'success');
            } catch (err) {
                showToast(apiErrorMsg(err), 'error');
            }
        }

        async function connect() {
            const token = getToken();
            if (!token) {
                authError.textContent = 'Enter a token.';
                authError.classList.remove('hidden');
                return;
            }
            authError.classList.add('hidden');
            writeStoredToken(token);
            try {
                await loadList();
                authOverlay.classList.add('hidden');
            } catch (err) {
                setConnected(false, 'Auth failed');
                authError.textContent = apiErrorMsg(err);
                authError.classList.remove('hidden');
                authOverlay.classList.remove('hidden');
            }
        }

        if (saveTokenBtn) saveTokenBtn.addEventListener('click', connect);
        if (tokenInput) {
            tokenInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') connect(); });
        }

        if (changeTokenBtn) {
            changeTokenBtn.addEventListener('click', function () {
                authOverlay.classList.remove('hidden');
                tokenInput.focus();
            });
        }

        if (btnAvatar) {
            btnAvatar.addEventListener('click', function () {
                if (connPill.classList.contains('visible')) {
                    showToast('Connected: ' + connLabel.textContent, 'success');
                } else {
                    authOverlay.classList.remove('hidden');
                }
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', function () {
                loadList().catch(function (err) { showToast(apiErrorMsg(err), 'error'); });
            });
        }

        if (applyBtn) {
            applyBtn.addEventListener('click', function () {
                loadList().catch(function (err) { showToast(apiErrorMsg(err), 'error'); });
            });
        }

        if (severityFilter) {
            severityFilter.addEventListener('change', function () {
                loadList().catch(function (err) { showToast(apiErrorMsg(err), 'error'); });
            });
        }

        if (viewTableBtn && viewListBtn) {
            viewTableBtn.addEventListener('click', function () {
                viewTableBtn.classList.add('active');
                viewListBtn.classList.remove('active');
            });

            viewListBtn.addEventListener('click', function () {
                viewListBtn.classList.add('active');
                viewTableBtn.classList.remove('active');
            });
        }

        const saved = readStoredToken();
        if (saved) {
            tokenInput.value = saved;
        } else if (IS_LOCAL) {
            tokenInput.value = DEMO_TOKEN;
        }

        if (tokenInput && tokenInput.value) {
            connect().catch(function () {});
        } else if (authOverlay) {
            authOverlay.classList.remove('hidden');
            setConnected(false, 'Offline');
        }
    });
})();