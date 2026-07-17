(function () {
    "use strict";

    document.addEventListener('DOMContentLoaded', function () {
        const connPill        = document.getElementById('conn-pill');
        const connDot         = document.getElementById('conn-dot');
        const connLabel       = document.getElementById('conn-label');
        const btnAvatar       = document.getElementById('btn-avatar');
        const changeTokenBtn  = document.getElementById('change-token-btn');
        const refreshBtn      = document.getElementById('refresh-btn');
        const findingsBody    = document.getElementById('findings-body');
        const findingsCount   = document.getElementById('findings-count');
        const severityFilter  = document.getElementById('filter-severity');
        const statusFilter    = document.getElementById('filter-status');
        const sortFilter      = document.getElementById('filter-sort');
        const cveFilter       = document.getElementById('filter-cve');
        const dateStart       = document.getElementById('filter-date-start');
        const dateEnd         = document.getElementById('filter-date-end');
        const applyBtn        = document.getElementById('apply-filters');
        const triageModeBtn   = document.getElementById('triage-mode-btn');
        const viewTableBtn    = document.getElementById('view-table');
        const viewListBtn     = document.getElementById('view-list');
        const tableWrap       = document.getElementById('findings-table-wrap');
        const listView        = document.getElementById('findings-list-view');
        const layout          = document.querySelector('.layout');
        const mobileTabBtns   = document.querySelectorAll('.mobile-tab');
        const mobileMq        = window.matchMedia('(max-width: 900px)');
        const toast           = document.getElementById('toast');

        const IS_LOCAL   = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
        const STATUSES   = ['open', 'triaging', 'converted', 'snoozed', 'wontfix'];

        let selectedRawId = null;
        let detailRequestSeq = 0;
        let toastTimer = null;
        let currentFindings = [];
        let idIndexMap = {};
        let triageQueueOn = false;
        let listViewMode = false;
        let lastHealth = null;

        function isMobileView() { return mobileMq.matches; }

        function setMobilePanel(name) {
            if (!layout || !isMobileView()) return;
            layout.classList.remove('panel-findings', 'panel-filters', 'panel-detail');
            layout.classList.add('panel-' + name);
            mobileTabBtns.forEach(function (btn) {
                btn.classList.toggle('active', btn.getAttribute('data-mobile-panel') === name);
            });
        }

        function applyMobileLayout() {
            if (isMobileView()) {
                setListViewMode(true);
                if (layout && !layout.classList.contains('panel-detail') &&
                    !layout.classList.contains('panel-filters')) {
                    layout.classList.add('panel-findings');
                }
            } else if (layout) {
                layout.classList.remove('panel-findings', 'panel-filters', 'panel-detail');
            }
        }

        function onFindingClick(rawId) {
            if (!rawId) return;
            selectedRawId = rawId;
            document.querySelectorAll('.finding-row, .finding-list-card').forEach(function (el) {
                el.classList.toggle('selected', el.getAttribute('data-raw-id') === rawId);
            });
            if (isMobileView()) setMobilePanel('detail');
            loadFindingDetail(rawId);
        }

        if (findingsBody) {
            findingsBody.addEventListener('click', function (e) {
                const row = e.target.closest('tr[data-raw-id]');
                if (!row) return;
                onFindingClick(row.getAttribute('data-raw-id'));
            });
        }

        if (listView) {
            listView.addEventListener('click', function (e) {
                const card = e.target.closest('.finding-list-card[data-raw-id]');
                if (!card) return;
                onFindingClick(card.getAttribute('data-raw-id'));
            });
        }

        document.querySelectorAll('.date-wrap').forEach(function (wrap) {
            const input = wrap.querySelector('input[type="date"]');
            if (!input) return;
            wrap.addEventListener('click', function (e) {
                if (e.target === input) return;
                openDatePicker(input);
            });
            input.addEventListener('click', function () { openDatePicker(input); });
        });

        function openDatePicker(input) {
            if (!input) return;
            if (typeof input.showPicker === 'function') {
                try { input.showPicker(); return; } catch (_) {}
            }
            input.focus();
        }

        function resetDetailPanel() {
            const panel = document.getElementById('detail-panel-content');
            if (!panel) return;
            panel.innerHTML =
                '<div class="detail-placeholder">' +
                '<i class="fa-solid fa-shield-halved"></i>' +
                '<span>Select a finding to view details</span></div>';
        }

        function showDetailLoading() {
            const panel = document.getElementById('detail-panel-content');
            if (!panel) return;
            panel.innerHTML =
                '<div class="detail-placeholder"><div class="spinner"></div>' +
                '<span>Loading finding details…</span></div>';
        }

        function showDetailError(message, rawId) {
            const panel = document.getElementById('detail-panel-content');
            if (!panel) return;
            panel.innerHTML =
                '<div class="detail-placeholder detail-error">' +
                '<i class="fa-solid fa-triangle-exclamation"></i>' +
                '<span>' + esc(message) + '</span>' +
                '<button type="button" class="export-btn detail-retry-btn">Retry</button></div>';
            const retryBtn = panel.querySelector('.detail-retry-btn');
            if (retryBtn) {
                retryBtn.addEventListener('click', function () {
                    if (rawId) loadFindingDetail(rawId);
                });
            }
        }

        function formatSnippet(snippet) {
            if (!snippet || typeof snippet !== 'object') return '—';
            try { return JSON.stringify(snippet, null, 2); } catch (_) { return '—'; }
        }

        function formatAccessTime(ts) {
            if (ts == null || ts === '') return '—';
            const n = Number(ts);
            if (!isNaN(n) && n > 1e9) {
                const d = new Date(n < 1e12 ? n * 1000 : n);
                if (!isNaN(d.getTime())) return d.toLocaleString();
            }
            return String(ts);
        }

        function renderAccessLogs(access) {
            const logs = (access && access.recent) || [];
            if (!logs.length) return '<li>No access events yet</li>';
            return logs.map(function (log) {
                return '<li>' + esc(log.action || 'access') + ' · ' +
                    esc(log.actor || '—') + ' · ' +
                    esc(formatAccessTime(log.created_at)) + '</li>';
            }).join('');
        }

        function cveUrl(cveId) {
            if (!cveId || cveId === '—') return '';
            const id = String(cveId).trim().toUpperCase();
            if (!/^CVE-\d{4}-/.test(id)) return '';
            return 'https://nvd.nist.gov/vuln/detail/' + encodeURIComponent(id);
        }

        function likelihoodBullets(finding, riskNum) {
            const bullets = [];
            const target = finding.target || '';
            if (/^https?:\/\//i.test(target)) bullets.push('Internet-exposed target: ' + target);
            else if (target) bullets.push('Affected target: ' + target);
            if (finding.cve_id) bullets.push('Mapped ' + finding.cve_id + ' (score ' + riskNum + ')');
            else bullets.push('No CVE mapped — severity-derived score ' + riskNum);
            if (finding.fingerprint) bullets.push('Fingerprint: ' + finding.fingerprint);
            return bullets;
        }

        function impactBullets(finding) {
            const bullets = [];
            const sev = String(finding.severity || 'info').toLowerCase();
            bullets.push('Severity class: ' + sev.toUpperCase());
            if (finding.rule_id) bullets.push('Rule: ' + finding.rule_id);
            if (finding.title) bullets.push('Title: ' + finding.title);
            if (sev === 'critical' || sev === 'high') bullets.push('Elevated business impact — prioritize review');
            else bullets.push('Standard review queue');
            return bullets;
        }

        function renderDetailFromApi(data) {
            const panel = document.getElementById('detail-panel-content');
            if (!panel || !data) return;

            const finding = data.finding || {};
            const id = displayId(finding.id);
            const rule = finding.rule_id || '—';
            const severity = String(finding.severity || 'info');
            const target = finding.target || '—';
            const cve = finding.cve_id || '';
            const status = finding.status || 'open';
            const safeCve = cve && cve !== '—' ? cve : '';
            const sevKey = severity.toLowerCase();
            const riskNum = riskScore(finding);
            const riskWord = riskNum >= 9 ? 'Critical' : riskNum >= 7 ? 'High' : riskNum >= 4 ? 'Medium' : 'Low';
            const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
            const snippetText = formatSnippet(data.payload_snippet);
            const bltIssue = finding.blt_issue_id;
            const cveHref = cveUrl(safeCve);
            const env = data.envelope || {};
            const evidence = data.evidence || {};
            let evidenceBadge = '';
            if (evidence.encrypted_at_rest) {
                evidenceBadge = evidence.decrypted
                    ? '<span class="evidence-badge enc-ok" title="AES-256-GCM ciphertext at rest, decrypted server-side for this authorized view">\uD83D\uDD13 Encrypted at rest · decrypted server-side</span>'
                    : '<span class="evidence-badge enc-fail" title="Encrypted at rest; server could not decrypt (key unavailable)">\uD83D\uDD12 Encrypted at rest · key unavailable</span>';
            }

            const statusOptions = STATUSES.map(function (s) {
                const sel = s === status ? ' selected' : '';
                return '<option value="' + esc(s) + '"' + sel + '>' + esc(s) + '</option>';
            }).join('');

            panel.innerHTML = `
              <div class="finding-card">
                <div class="finding-card-title">${esc(id)} · ${esc(rule)}</div>
                <div class="detail-tabs">
                  <span class="detail-tab active" data-tab="evidence">Evidence</span>
                  <span class="detail-tab" data-tab="risk">Risk</span>
                  <span class="detail-tab" data-tab="status">Status</span>
                </div>
                <div class="detail-tab-panels">
                  <div class="detail-tab-panel active" data-panel="evidence">
                    <div class="evidence-section">
                      <div class="evidence-label">Redacted Evidence Snippet</div>
                      <div class="evidence-label-small">Payload (server-redacted)${evidenceBadge}</div>
                      <div class="evidence-box evidence-box-live">
                        <pre class="evidence-json">${esc(snippetText)}</pre>
                        <div class="confidential-stamp">confidential</div>
                      </div>
                    </div>
                    <div class="access-section">
                      <div class="field-label">Recent Access</div>
                      <ul class="risk-list access-log-list">${renderAccessLogs(data.access)}</ul>
                    </div>
                  </div>
                  <div class="detail-tab-panel" data-panel="risk">
                    <div class="risk-row">
                      <div class="risk-block">
                        <div class="field-label">Likelihood</div>
                        <div class="risk-value risk-num-${riskClass(riskNum).replace('risk-','')}">${esc(String(riskNum))} ${esc(riskWord)}</div>
                        <ul class="risk-list">${likelihoodBullets(finding, riskNum).map(function (b) { return '<li>' + esc(b) + '</li>'; }).join('')}</ul>
                      </div>
                      <div class="risk-block">
                        <div class="field-label">Impact</div>
                        <div class="risk-value risk-num-${sevKey}">${esc(severity.toUpperCase())}</div>
                        <ul class="risk-list">${impactBullets(finding).map(function (b) { return '<li>' + esc(b) + '</li>'; }).join('')}</ul>
                      </div>
                    </div>
                    <div class="reason-box">
                      <div class="field-label">Reason</div>
                      <div class="summary-text">${esc(rule)} on ${esc(target)}. Severity ${esc(severity)}, status ${esc(statusLabel)}.${bltIssue ? ' Linked to BLT issue ' + esc(bltIssue) + '.' : ''}</div>
                    </div>
                  </div>
                  <div class="detail-tab-panel" data-panel="status">
                    <div class="field-label">Triage Status</div>
                    <div class="status-save-row">
                      <select id="detail-status-select" class="field-select">${statusOptions}</select>
                      <button id="detail-status-save" type="button" class="apply-btn" style="margin:0;padding:6px 10px;">Save</button>
                    </div>
                    <dl class="meta-grid">
                      <dt>Created</dt><dd>${esc(formatAccessTime(finding.created_at))}</dd>
                      <dt>Updated</dt><dd>${esc(formatAccessTime(finding.updated_at))}</dd>
                      <dt>Envelope</dt><dd>${esc(env.sender_id || '—')} / ${esc(env.kid || '—')}</dd>
                      <dt>Received</dt><dd>${esc(formatAccessTime(env.received_at))}</dd>
                    </dl>
                    ${bltIssue ? '<div class="blt-issue-link">BLT Issue #' + esc(bltIssue) + ' (via BLT-API)</div>' : '<div class="field-label" style="margin-top:8px">Not yet converted to BLT issue</div>'}
                  </div>
                </div>
                <div class="detail-actions">
                  <button id="detail-convert-btn" type="button" class="convert-btn"${bltIssue ? ' disabled' : ''}>
                    <span>📋</span><span class="cve-badge">CVE</span>
                    <span>${bltIssue ? 'Issue ' + esc(bltIssue) : 'Convert to Issue (BLT-API)'}</span>
                  </button>
                  <div class="field-label">CVE Link</div>
                  ${cveHref
                    ? '<div class="cve-link-row"><a href="' + esc(cveHref) + '" target="_blank" rel="noopener">' + esc(cveHref) + '</a></div>'
                    : '<input type="text" class="cve-input" value="" placeholder="No CVE mapped" readonly />'}
                  <button id="detail-export-btn" type="button" class="export-btn">📄 Export CSV</button>
                </div>
              </div>`;

            const convertBtn = document.getElementById('detail-convert-btn');
            const exportBtn = document.getElementById('detail-export-btn');
            const statusSave = document.getElementById('detail-status-save');

            if (convertBtn && !bltIssue) {
                convertBtn.addEventListener('click', function () {
                    if (selectedRawId) handleConvert(selectedRawId, id);
                });
            }
            if (exportBtn) exportBtn.addEventListener('click', handleExport);
            if (statusSave) {
                statusSave.addEventListener('click', function () {
                    const sel = document.getElementById('detail-status-select');
                    if (selectedRawId && sel) handleStatusUpdate(selectedRawId, sel.value);
                });
            }

            panel.querySelectorAll('.detail-tab').forEach(function (tab) {
                tab.addEventListener('click', function () {
                    const name = tab.getAttribute('data-tab');
                    panel.querySelectorAll('.detail-tab').forEach(function (t) {
                        t.classList.toggle('active', t.getAttribute('data-tab') === name);
                    });
                    panel.querySelectorAll('.detail-tab-panel').forEach(function (p) {
                        p.classList.toggle('active', p.getAttribute('data-panel') === name);
                    });
                });
            });
        }

        async function loadFindingDetail(rawId) {
            if (!rawId) return;
            const seq = ++detailRequestSeq;
            showDetailLoading();
            try {
                const data = await apiRequest('/api/findings/' + encodeURIComponent(rawId));
                if (seq !== detailRequestSeq) return;
                renderDetailFromApi(data);
            } catch (err) {
                if (seq !== detailRequestSeq) return;
                const msg = apiErrorMsg(err);
                showDetailError(msg, rawId);
                showToast(msg, 'error');
            }
        }

        async function handleStatusUpdate(rawId, newStatus) {
            if (!rawId || !newStatus) return;
            try {
                await apiRequest('/api/findings/' + encodeURIComponent(rawId), {
                    method: 'PATCH',
                    body: { status: newStatus },
                });
                showToast('Status updated to ' + newStatus + '.', 'success');
                await loadList();
                loadFindingDetail(rawId);
            } catch (err) {
                showToast(apiErrorMsg(err), 'error');
            }
        }

        function esc(v) {
            return String(v == null ? '' : v)
                .replace(/&/g, '&amp;').replace(/</g, '&lt;')
                .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function authHeaders(json) {
            const h = {};
            if (json) h['Content-Type'] = 'application/json';
            const token = getStoredToken();
            if (token) h['Authorization'] = 'Bearer ' + token;
            return h;
        }

        function getStoredToken() {
            try { return localStorage.getItem('ng_api_token') || ''; } catch (_) { return ''; }
        }

        function setStoredToken(token) {
            try {
                if (token) localStorage.setItem('ng_api_token', token);
                else localStorage.removeItem('ng_api_token');
            } catch (_) {}
        }

        function openDemoMode() {
            return !!(lastHealth && lastHealth.auth && lastHealth.auth.read_required === false);
        }

        function showAuthOverlay(show, message) {
            const overlay = document.getElementById('auth-overlay');
            const err = document.getElementById('auth-error');
            if (!overlay) return;
            overlay.classList.toggle('hidden', !show);
            overlay.setAttribute('aria-hidden', show ? 'false' : 'true');
            if (err) {
                if (message) {
                    err.hidden = false;
                    err.textContent = message;
                } else {
                    err.hidden = true;
                    err.textContent = '';
                }
            }
        }

        function showToast(text, kind) {
            if (!toast) return;
            clearTimeout(toastTimer);
            toast.textContent = text;
            toast.className = 'toast show ' + (kind || '');
            toastTimer = setTimeout(function () { toast.className = 'toast ' + (kind || ''); }, 3500);
        }

        function setConnected(ok, label) {
            connDot.className = 'conn-dot' + (ok ? ' live' : '');
            connLabel.textContent = label || (ok ? 'Connected' : 'Offline');
            connPill.classList.toggle('visible', ok);
        }

        async function apiRequest(path, opts) {
            opts = opts || {};
            const hasBody = opts.body != null;
            const res = await fetch(path, {
                method: opts.method || 'GET',
                headers: authHeaders(hasBody),
                body: hasBody ? JSON.stringify(opts.body) : undefined,
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

        const SEV_MAP = { critical: 'sev-critical', high: 'sev-high', medium: 'sev-medium', low: 'sev-low', info: 'sev-info' };
        const SEV_SCORE = { critical: 9, high: 7, medium: 5, low: 3, info: 1 };

        function sevBadge(v) {
            const key = String(v || 'info').toLowerCase();
            return '<span class="sev ' + (SEV_MAP[key] || 'sev-info') + '">' + esc(key) + '</span>';
        }

        function riskScore(f) {
            if (f && f.cve_score != null && !isNaN(f.cve_score)) {
                return Math.max(1, Math.min(10, Math.round(Number(f.cve_score))));
            }
            return SEV_SCORE[String((f && f.severity) || 'info').toLowerCase()] || 1;
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
            return '<span class="status-pill status-' + esc(key) + '">' +
                esc(key.charAt(0).toUpperCase() + key.slice(1)) + '</span>';
        }

        function displayId(id) {
            if (!id) return '—';
            if (/^NG-\d{3}$/i.test(id)) return id.toUpperCase();
            if (idIndexMap[id] != null) {
                return 'NG-' + String(idIndexMap[id]).padStart(3, '0');
            }
            return id;
        }

        function dateToUnixStart(dateStr) {
            if (!dateStr) return null;
            const d = new Date(dateStr + 'T00:00:00');
            if (isNaN(d.getTime())) return null;
            return Math.floor(d.getTime() / 1000);
        }

        function dateToUnixEnd(dateStr) {
            if (!dateStr) return null;
            const d = new Date(dateStr + 'T23:59:59');
            if (isNaN(d.getTime())) return null;
            return Math.floor(d.getTime() / 1000);
        }

        function buildListQuery() {
            const p = new URLSearchParams({ limit: '100' });
            if (severityFilter && severityFilter.value) p.set('severity', severityFilter.value);
            if (statusFilter && statusFilter.value) p.set('status', statusFilter.value);
            if (cveFilter && cveFilter.value.trim()) p.set('cve_id', cveFilter.value.trim());
            if (sortFilter && sortFilter.value) {
                const parts = sortFilter.value.split(':');
                p.set('sort', parts[0] || 'updated_at');
                p.set('order', parts[1] || 'desc');
            }
            const from = dateStart ? dateToUnixStart(dateStart.value) : null;
            const to = dateEnd ? dateToUnixEnd(dateEnd.value) : null;
            if (from != null) p.set('created_from', String(from));
            if (to != null) p.set('created_to', String(to));
            if (triageQueueOn) p.set('triage_queue', '1');
            return p.toString();
        }

        function setListViewMode(listMode) {
            listViewMode = listMode;
            if (tableWrap) tableWrap.classList.toggle('hidden', listMode);
            if (listView) listView.classList.toggle('hidden', !listMode);
            if (viewTableBtn) viewTableBtn.classList.toggle('active', !listMode);
            if (viewListBtn) viewListBtn.classList.toggle('active', listMode);
        }

        function targetParts(target) {
            if (!target) return { host: '—', path: '' };
            try {
                if (/^https?:\/\//i.test(target)) {
                    const u = new URL(target);
                    const path = (u.pathname || '/') + (u.search || '');
                    return {
                        host: u.hostname,
                        path: path === '/' ? '' : path,
                    };
                }
            } catch (_) {}
            return { host: '—', path: String(target) };
        }

        function renderListCards(findings) {
            if (!listView) return;
            if (!findings.length) {
                listView.innerHTML = '<div class="empty-state">No findings match the current filters.</div>';
                return;
            }
            listView.innerHTML = findings.map(function (f) {
                const sel = f.id === selectedRawId ? ' selected' : '';
                const tp = targetParts(f.target);
                const pathLine = tp.path
                    ? '<div class="flc-path">' + esc(tp.path) + '</div>'
                    : '';
                return '<div class="finding-list-card' + sel + '" data-raw-id="' + esc(f.id) + '">' +
                    '<div class="flc-top"><span class="flc-id">' + esc(displayId(f.id)) + '</span>' +
                    '<div class="flc-badges">' + sevBadge(f.severity) + statusPill(f.status) + '</div></div>' +
                    '<div class="flc-rule">' + esc(f.rule_id || '—') + '</div>' +
                    '<div class="flc-host">' + esc(tp.host) + '</div>' +
                    pathLine + '</div>';
            }).join('');
        }

        function renderFindings(findings) {
            currentFindings = findings;
            idIndexMap = {};
            findings.forEach(function (f, i) { idIndexMap[f.id] = i + 1; });

            const stillVisible = findings.some(function (f) { return f.id === selectedRawId; });
            if (!stillVisible) {
                selectedRawId = null;
                resetDetailPanel();
            }

            if (!findingsBody) return;
            findingsBody.innerHTML = '';
            if (!findings.length) {
                findingsBody.innerHTML =
                    '<tr><td colspan="7"><div class="empty-state">No findings match the current filters.</div></td></tr>';
                renderListCards([]);
                return;
            }

            for (const f of findings) {
                const tr = document.createElement('tr');
                tr.className = 'finding-row';
                if (f.id === selectedRawId) tr.classList.add('selected');
                tr.setAttribute('data-raw-id', f.id);
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
            renderListCards(findings);
        }

        async function checkIntegrations() {
            try {
                const res = await fetch('/api/health');
                const data = await res.json();
                lastHealth = data;
                const blt = data.integrations && data.integrations.blt_api;
                if (blt && blt.configured) {
                    return blt.reachable ? 'BLT-API live' : 'BLT-API down';
                }
                return null;
            } catch (_) {
                return null;
            }
        }

        async function loadList() {
            if (!findingsBody) return;
            findingsBody.innerHTML =
                '<tr><td colspan="7"><div class="empty-state"><div class="spinner"></div>Loading findings…</div></td></tr>';
            try {
                const data = await apiRequest('/api/findings?' + buildListQuery());
                renderFindings(data.findings || []);
                const total = data.total || 0;
                findingsCount.textContent = total + ' total' + (triageQueueOn ? ' · triage queue' : '');
                const bltLabel = await checkIntegrations();
                const label = data.org_id || 'connected';
                const connText = isMobileView()
                    ? label
                    : (bltLabel ? label + ' · ' + bltLabel : label);
                setConnected(true, connText);
                if (!isMobileView() && bltLabel === 'BLT-API down') {
                    showToast('BLT-API unreachable — start: python3 local_dev/blt_api_stub.py', 'error');
                }
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
                showToast('Finding ' + verb + ' BLT issue ' + data.blt_issue_id + '.', 'success');
                await loadList();
                loadFindingDetail(rawId);
            } catch (err) {
                showToast(apiErrorMsg(err), 'error');
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

        if (changeTokenBtn) {
            changeTokenBtn.addEventListener('click', function () {
                if (openDemoMode()) {
                    showToast('Open triage — reads do not require a token in this demo.', 'success');
                    return;
                }
                showAuthOverlay(true);
                const input = document.getElementById('auth-token-input');
                if (input) {
                    input.value = getStoredToken();
                    input.focus();
                }
            });
        }
        if (btnAvatar) {
            btnAvatar.addEventListener('click', function () {
                if (connPill.classList.contains('visible')) {
                    let msg = 'Connected: ' + connLabel.textContent;
                    if (lastHealth && lastHealth.integrations) {
                        const blt = lastHealth.integrations.blt_api;
                        if (blt) msg += ' | BLT-API configured=' + blt.configured;
                    }
                    showToast(msg, 'success');
                } else {
                    showToast('Not connected — check API health.', 'error');
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
        if (statusFilter) {
            statusFilter.addEventListener('change', function () {
                loadList().catch(function (err) { showToast(apiErrorMsg(err), 'error'); });
            });
        }
        if (triageModeBtn) {
            triageModeBtn.addEventListener('click', function () {
                triageQueueOn = !triageQueueOn;
                triageModeBtn.classList.toggle('active', triageQueueOn);
                loadList().catch(function (err) { showToast(apiErrorMsg(err), 'error'); });
            });
        }
        if (viewTableBtn && viewListBtn) {
            viewTableBtn.addEventListener('click', function () { setListViewMode(false); });
            viewListBtn.addEventListener('click', function () { setListViewMode(true); });
        }

        mobileTabBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                setMobilePanel(btn.getAttribute('data-mobile-panel'));
            });
        });
        if (typeof mobileMq.addEventListener === 'function') {
            mobileMq.addEventListener('change', applyMobileLayout);
        } else if (typeof mobileMq.addListener === 'function') {
            mobileMq.addListener(applyMobileLayout);
        }
        applyMobileLayout();

        (async function boot() {
            try {
                lastHealth = await apiRequest('/api/health');
                const blt = lastHealth && lastHealth.integrations && lastHealth.integrations.blt_api;
                const label = blt && blt.configured ? 'BLT-API configured' : 'API live';
                setConnected(true, label);
            } catch (_) {
                lastHealth = null;
                setConnected(false, 'Offline');
            }

            const authSubmit = document.getElementById('auth-submit');
            const authInput = document.getElementById('auth-token-input');
            if (authSubmit && authInput) {
                authSubmit.addEventListener('click', async function () {
                    const token = (authInput.value || '').trim();
                    if (!token) {
                        showAuthOverlay(true, 'Token required.');
                        return;
                    }
                    setStoredToken(token);
                    try {
                        await loadList();
                        showAuthOverlay(false);
                        showToast('Connected with org token.', 'success');
                    } catch (err) {
                        setStoredToken('');
                        showAuthOverlay(true, apiErrorMsg(err));
                    }
                });
            }

            if (openDemoMode()) {
                // Open-read demo: do not force a token for GET, but keep any stored
                // token so PATCH/convert still authenticate.
                showAuthOverlay(false);
                if (IS_LOCAL && !getStoredToken()) {
                    setStoredToken('triage-token');
                }
                showToast('Open triage — reads do not require a token in this demo.', 'success');
                loadList().catch(function (err) { showToast(apiErrorMsg(err), 'error'); });
                return;
            }

            if (!getStoredToken()) {
                showAuthOverlay(true);
                return;
            }
            loadList().catch(function (err) {
                showAuthOverlay(true, apiErrorMsg(err));
            });
        })();
    });
})();
