(function () {
    "use strict";

    const tokenInput = document.getElementById('api-token');
    const connPill = document.getElementById('conn-pill');
    const messageBox = document.getElementById('message');
    const findingsBody = document.getElementById('findings-body');
    const findingsCount = document.getElementById('findings-count');
    const detailPanel = document.getElementById('detail-panel');
    const convertBtn = document.getElementById('convert-issue');
    const exportBtn = document.getElementById('export-csv');
    const refreshBtn = document.getElementById('refresh-btn');
    const severityFilter = document.getElementById('filter-severity');
    const statusFilter = document.getElementById('filter-status');

    const SEVERITIES = new Set(['critical', 'high', 'medium', 'low', 'info']);
    const STATUSES = new Set(['open', 'triaged', 'resolved', 'queued', 'running', 'completed', 'contacted', 'failed']);
    const IS_LOCAL = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
    const DEMO_TOKEN = 'triage-token';
    let selectedId = null;

    function readStoredToken() {
        try {
            return localStorage.getItem('ng_api_token');
        } catch (err) {
            return null;
        }
    }

    function writeStoredToken(token) {
        try {
            localStorage.setItem('ng_api_token', token);
        } catch (err) {
            /* ignore — private mode / blocked storage */
        }
    }

    const saved = readStoredToken();
    if (saved) {
        tokenInput.value = saved;
    } else if (IS_LOCAL) {
        tokenInput.value = DEMO_TOKEN;
    }

    function showMessage(text, kind) {
        messageBox.textContent = text;
        messageBox.className = 'message ' + (kind || 'info');
        messageBox.style.display = text ? 'block' : 'none';
    }

    function setConnected(connected, label) {
        if (connected) {
            connPill.innerHTML =
                '<span class="h-2 w-2 rounded-full bg-green-500"></span>' +
                escapeHtml(label || 'Connected');
        } else {
            connPill.innerHTML =
                '<span class="h-2 w-2 rounded-full bg-gray-400"></span>' +
                escapeHtml(label || 'Not connected');
        }
    }

    function authHeaders() {
        const token = tokenInput.value.trim();
        if (!token) {
            throw new Error('Enter an org API token first.');
        }
        return { Authorization: 'Bearer ' + token };
    }

    async function apiRequest(path, options) {
        const opts = options || {};
        const res = await fetch(path, {
            method: opts.method || 'GET',
            headers: authHeaders(),
        });
        if (opts.raw) {
            if (!res.ok) {
                throw new Error('Request failed (' + res.status + ')');
            }
            return res;
        }
        let data = {};
        try {
            data = await res.json();
        } catch (err) {
            data = {};
        }
        if (!res.ok) {
            throw new Error(data.message || data.error || ('Request failed (' + res.status + ')'));
        }
        return data;
    }

    function apiErrorMessage(err) {
        if (err && err.message === 'Failed to fetch') {
            return 'Cannot reach the API. Start the dev server: python3 local_dev/serve.py then open http://localhost:8787/triage.html';
        }
        return err.message || String(err);
    }

    function escapeHtml(text) {
        return String(text === null || text === undefined ? '' : text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function severityBadge(severity) {
        const value = String(severity || 'info').toLowerCase();
        const cls = SEVERITIES.has(value) ? value : 'info';
        return '<span class="severity ' + cls + '">' + escapeHtml(value) + '</span>';
    }

    function statusBadge(status) {
        const value = String(status || '').toLowerCase();
        const cls = STATUSES.has(value) ? value : 'queued';
        return '<span class="status ' + cls + '">' + escapeHtml(value || 'open') + '</span>';
    }

    function buildListQuery() {
        const params = new URLSearchParams({ limit: '100' });
        if (severityFilter.value) {
            params.set('severity', severityFilter.value);
        }
        if (statusFilter.value) {
            params.set('status', statusFilter.value);
        }
        return params.toString();
    }

    function renderFindings(findings) {
        findingsBody.innerHTML = '';
        if (!findings.length) {
            findingsBody.innerHTML = '<tr><td colspan="4" class="loading">No findings match the current filters.</td></tr>';
            return;
        }
        for (const finding of findings) {
            const row = document.createElement('tr');
            row.className = 'cursor-pointer';
            if (finding.id === selectedId) {
                row.style.background = '#fff1f1';
            }
            row.innerHTML =
                '<td>' + severityBadge(finding.severity) + '</td>' +
                '<td class="font-medium text-dark-base">' + escapeHtml(finding.title) +
                (finding.blt_issue_id ? ' <i class="fa-solid fa-link ml-1 text-xs text-gray-400" title="Linked issue"></i>' : '') +
                '</td>' +
                '<td class="font-mono text-xs text-gray-600">' + escapeHtml(finding.rule_id) + '</td>' +
                '<td>' + statusBadge(finding.status) + '</td>';
            row.addEventListener('click', function () {
                selectedId = finding.id;
                loadDetail(finding.id);
                renderFindings(findings);
            });
            findingsBody.appendChild(row);
        }
    }

    async function loadList() {
        showMessage('Loading findings…', 'info');
        findingsBody.innerHTML = '<tr><td colspan="4" class="loading"><div class="spinner"></div>Loading findings…</td></tr>';
        const data = await apiRequest('/api/findings?' + buildListQuery());
        renderFindings(data.findings || []);
        findingsCount.textContent = (data.total || 0) + ' total';
        setConnected(true, 'org ' + data.org_id);
        showMessage('Loaded ' + (data.findings ? data.findings.length : 0) + ' of ' + (data.total || 0) + ' findings.', 'success');
        const authSection = document.getElementById('auth-section');
        if (authSection) {
            authSection.classList.add('hidden');
        }
        const showAuthBtn = document.getElementById('show-auth');
        if (showAuthBtn) {
            showAuthBtn.classList.remove('hidden');
        }
        const devHint = document.getElementById('dev-hint');
        if (devHint) {
            devHint.classList.add('hidden');
        }
        const findingsSection = document.getElementById('findings-section');
        if (findingsSection) {
            findingsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    function detailRow(label, value, mono) {
        return '<div class="flex justify-between gap-4 border-b border-neutral-border py-2">' +
            '<dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">' + escapeHtml(label) + '</dt>' +
            '<dd class="text-right ' + (mono ? 'font-mono text-xs' : 'text-sm') + ' text-dark-base">' + escapeHtml(value) + '</dd>' +
            '</div>';
    }

    async function loadDetail(id) {
        convertBtn.disabled = false;
        detailPanel.innerHTML = '<div class="loading"><div class="spinner"></div>Loading detail…</div>';
        try {
            const data = await apiRequest('/api/findings/' + encodeURIComponent(id));
            const finding = data.finding || {};
            const snippet = JSON.stringify(data.payload_snippet || {}, null, 2);
            const recent = (data.access && data.access.recent) ? data.access.recent : [];

            detailPanel.innerHTML =
                '<div class="mb-3 flex items-center gap-2">' + severityBadge(finding.severity) + statusBadge(finding.status) + '</div>' +
                '<h4 class="text-base font-bold text-dark-base">' + escapeHtml(finding.title) + '</h4>' +
                '<dl class="mt-3">' +
                detailRow('Finding ID', finding.id, true) +
                detailRow('Rule', finding.rule_id, true) +
                detailRow('Target', finding.target || '—') +
                detailRow('CVE', finding.cve_id || '—') +
                detailRow('BLT Issue', finding.blt_issue_id || 'not linked', true) +
                detailRow('Audit views', recent.length + ' recent') +
                '</dl>' +
                '<p class="mt-4 text-xs font-semibold uppercase tracking-wide text-gray-500">Redacted payload</p>' +
                '<pre class="mt-2 max-h-72 overflow-auto rounded-lg border border-neutral-border bg-gray-50 p-3 text-xs text-gray-800">' + escapeHtml(snippet) + '</pre>';
        } catch (err) {
            detailPanel.innerHTML = '<p class="text-sm text-red-700">' + escapeHtml(err.message) + '</p>';
        }
    }

    async function connect() {
        try {
            const token = tokenInput.value.trim();
            if (!token) {
                showMessage('Enter an org API token first.', 'error');
                return;
            }
            writeStoredToken(token);
            await loadList();
        } catch (err) {
            setConnected(false, 'Auth failed');
            showMessage(apiErrorMessage(err), 'error');
            const devHint = document.getElementById('dev-hint');
            if (devHint && IS_LOCAL) {
                devHint.classList.remove('hidden');
            }
        }
    }

    document.getElementById('save-token').addEventListener('click', connect);
    tokenInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            connect();
        }
    });

    refreshBtn.addEventListener('click', function () {
        loadList().catch(function (err) { showMessage(apiErrorMessage(err), 'error'); });
    });

    severityFilter.addEventListener('change', function () {
        loadList().catch(function (err) { showMessage(apiErrorMessage(err), 'error'); });
    });
    statusFilter.addEventListener('change', function () {
        loadList().catch(function (err) { showMessage(apiErrorMessage(err), 'error'); });
    });

    convertBtn.addEventListener('click', async function () {
        if (!selectedId) {
            return;
        }
        convertBtn.disabled = true;
        try {
            const data = await apiRequest(
                '/api/findings/' + encodeURIComponent(selectedId) + '/convert-to-issue',
                { method: 'POST' }
            );
            const verb = data.status === 'existing' ? 'already linked to' : 'converted to';
            await loadDetail(selectedId);
            await loadList();
            showMessage('Finding ' + verb + ' issue ' + data.blt_issue_id + '.', 'success');
        } catch (err) {
            showMessage(apiErrorMessage(err), 'error');
        } finally {
            convertBtn.disabled = false;
        }
    });

    exportBtn.addEventListener('click', async function () {
        try {
            if (!tokenInput.value.trim()) {
                showMessage('Connect with an org token first.', 'error');
                return;
            }
            const res = await apiRequest('/api/findings/export.csv?' + buildListQuery(), { raw: true });
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'netguardian-findings.csv';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            showMessage('CSV exported.', 'success');
        } catch (err) {
            showMessage(apiErrorMessage(err), 'error');
        }
    });

    document.getElementById('show-auth')?.addEventListener('click', function () {
        const authSection = document.getElementById('auth-section');
        if (authSection) {
            authSection.classList.remove('hidden');
        }
    });

    if (saved || IS_LOCAL) {
        connect().catch(function (err) {
            setConnected(false, 'Auth failed');
            showMessage(apiErrorMessage(err), 'error');
        });
    }
})();
