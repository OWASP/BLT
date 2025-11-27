const MATRIX_URL = "../data/metadata_matrix.json";

// DOM Elements
const elements = {
    tableHead: document.getElementById('table-head'),
    tableBody: document.getElementById('table-body'),
    status: document.getElementById('status'),
    stats: document.getElementById('stats'),
    rowCount: document.getElementById('row-count'),
    search: document.getElementById('search'),
    
    // Buttons
    toggleTheme: document.getElementById('toggle-theme'),
    toggleFilters: document.getElementById('toggle-filters'),
    toggleColumns: document.getElementById('toggle-columns'),
    exportBtn: document.getElementById('export-btn'),
    sortAsc: document.getElementById('sort-asc'),
    sortDesc: document.getElementById('sort-desc'),
    clearFilters: document.getElementById('clear-filters'),
    
    // Panels
    filtersPanel: document.getElementById('filters-panel'),
    columnsPanel: document.getElementById('columns-panel'),
    
    // Filters
    fieldFilter: document.getElementById('field-filter'),
    completenessFilter: document.getElementById('completeness-filter'),
    columnCheckboxes: document.getElementById('column-checkboxes')
};

// Application State
const state = {
    matrixData: [],
    columns: [], 
    visibleColumns: new Set(),
    sortColumn: 'repo',
    sortDirection: 'asc',
    selectedFields: new Set(['all'])
};

async function loadMatrix() {
    try {
        updateStatus('Loading metadata...');
        
        const response = await fetch(MATRIX_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const rawData = await response.json();
        if (!Array.isArray(rawData) || rawData.length === 0) {
            updateStatus('No metadata found.');
            return;
        }

        console.log('Raw data sample:', rawData[0]);
        console.log('Total rows:', rawData.length);

        // Process and normalize data
        state.matrixData = rawData.map(row => {
            const normalized = {};
            Object.entries(row).forEach(([key, value]) => {
                const cleanKey = key.trim().toLowerCase();
                normalized[cleanKey] = value;
            });
            return normalized;
        });

        // Extract ALL unique columns from all rows with proper counting
        const allColumns = new Set();
        
        state.matrixData.forEach(row => {
            Object.keys(row).forEach(key => {
                if (key && key.trim() !== '') {
                    allColumns.add(key.trim().toLowerCase());
                }
            });
        });

        // Convert to array and ensure repo is first
        state.columns = Array.from(allColumns);
        
        // Sort columns: repo first, then others alphabetically
        state.columns.sort((a, b) => {
            if (a === 'repo') return -1;
            if (b === 'repo') return 1;
            return a.localeCompare(b);
        });

        console.log('All detected columns:', state.columns);
        console.log('Total fields detected:', state.columns.length);

        // Set all columns as visible by default
        state.visibleColumns = new Set(state.columns);

        initializeUI();
        renderTable();
        updateStats();

        updateStatus(`Loaded ${state.matrixData.length} repositories with ${state.columns.length} fields`);
        
    } catch (error) {
        console.error('Failed to load data:', error);
        updateStatus('Failed to load metadata.');
    }
}

function initializeUI() {
    setupEventListeners();
    populateFieldFilter();
    populateColumnToggles();
    loadThemePreference();
}

function setupEventListeners() {
    // Theme
    elements.toggleTheme.addEventListener('click', toggleTheme);
    
    // Panel toggles
    elements.toggleFilters.addEventListener('click', () => togglePanel(elements.filtersPanel));
    elements.toggleColumns.addEventListener('click', () => togglePanel(elements.columnsPanel));
    
    // Sorting
    elements.sortAsc.addEventListener('click', () => sortTable('repo', 'asc'));
    elements.sortDesc.addEventListener('click', () => sortTable('repo', 'desc'));
    
    // Filters
    elements.search.addEventListener('input', debounce(renderTable, 300));
    elements.fieldFilter.addEventListener('change', handleFieldFilterChange);
    elements.completenessFilter.addEventListener('change', renderTable);
    elements.clearFilters.addEventListener('click', clearAllFilters);
    
    // Export
    elements.exportBtn.addEventListener('click', exportToCSV);
}

function updateStatus(message) {
    elements.status.textContent = message;
}

function updateStats(filteredData = state.matrixData) {
    const totalRepos = state.matrixData.length;
    const totalFields = state.columns.length;
    
    // Count fields that have data in at least one repository
    const fieldsWithData = state.columns.filter(col => 
        state.matrixData.some(row => hasData(row[col]))
    ).length;

    // Count repositories that have at least one non-repo field with data
    const reposWithMetadata = state.matrixData.filter(row =>
        state.columns.some(col => col !== 'repo' && hasData(row[col]))
    ).length;

    console.log(`Stats: ${totalFields} total fields, ${fieldsWithData} fields with data`);
    
    elements.stats.textContent = `${totalRepos} repositories (${reposWithMetadata} with metadata) • ${totalFields} total fields • ${fieldsWithData} fields with data`;
    elements.rowCount.textContent = `${filteredData.length} results`;
}

// Helper function to check if a value has meaningful data
function hasData(value) {
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return value.trim() !== '';
    if (typeof value === 'boolean') return true;
    if (typeof value === 'number') return true;
    return true;
}

function populateFieldFilter() {
    // Include ALL fields including repo in the filter, sorted alphabetically
    const fields = state.columns.filter(col => col !== 'repo').sort();
    
    console.log('Populating field filter with:', fields.length, 'fields');
    
    elements.fieldFilter.innerHTML = 
        `<option value="all" selected>All fields (${fields.length})</option>` +
        fields.map(field => {
            const count = state.matrixData.filter(row => hasData(row[field])).length;
            const percentage = ((count / state.matrixData.length) * 100).toFixed(1);
            return `<option value="${field}">${formatColumnName(field)} (${count}, ${percentage}%)</option>`;
        }).join('');
}

function populateColumnToggles() {
    // Show ALL fields including repo in column toggles
    const fields = state.columns.filter(col => col !== 'repo').sort();
    
    console.log('Populating column toggles with:', fields.length, 'fields');
    
    elements.columnCheckboxes.innerHTML = fields.map(field => {
        const count = state.matrixData.filter(row => hasData(row[field])).length;
        const isChecked = state.visibleColumns.has(field);
        const percentage = ((count / state.matrixData.length) * 100).toFixed(1);
        
        return `
        <div class="column-option">
            <input type="checkbox" id="col-${field}" data-field="${field}" ${isChecked ? 'checked' : ''}>
            <label for="col-${field}">
                ${formatColumnName(field)} 
                <span class="field-stats">${count} (${percentage}%)</span>
            </label>
        </div>
    `}).join('');
    
    // Add event listeners to checkboxes
    elements.columnCheckboxes.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const field = e.target.dataset.field;
            if (e.target.checked) {
                state.visibleColumns.add(field);
            } else {
                state.visibleColumns.delete(field);
            }
            renderTable();
        });
    });
}

function getFilteredData() {
    const searchTerm = elements.search.value.toLowerCase().trim();
    const completeness = elements.completenessFilter.value;
    
    return state.matrixData.filter(row => {
        // Search filter - always search in repo field
        const repoMatch = !searchTerm || 
            (row.repo && row.repo.toLowerCase().includes(searchTerm));
        if (!repoMatch) return false;
        
        // Field filter - check if row has any of the selected fields with data
        const fieldMatch = state.selectedFields.has('all') || 
            Array.from(state.selectedFields).some(field => 
                hasData(row[field])
            );
        if (!fieldMatch) return false;
        
        // Completeness filter - check if row has any metadata in non-repo fields
        if (completeness === 'with-metadata') {
            return state.columns.some(col => 
                col !== 'repo' && hasData(row[col])
            );
        }
        if (completeness === 'without-metadata') {
            return !state.columns.some(col => 
                col !== 'repo' && hasData(row[col])
            );
        }
        
        return true;
    });
}

function handleFieldFilterChange() {
    const selectedOptions = Array.from(elements.fieldFilter.selectedOptions);
    state.selectedFields = new Set(selectedOptions.map(opt => opt.value));
    console.log('Selected fields:', Array.from(state.selectedFields));
    renderTable();
}

function sortTable(column, direction) {
    state.sortColumn = column;
    state.sortDirection = direction;
    renderTable();
}

function clearAllFilters() {
    elements.search.value = '';
    elements.fieldFilter.value = 'all';
    elements.completenessFilter.value = 'all';
    state.selectedFields = new Set(['all']);
    
    // Reset all columns to visible
    state.visibleColumns = new Set(state.columns);
    
    // Update checkboxes
    populateColumnToggles();
    renderTable();
}


function renderTable() {
    const filteredData = getFilteredData();
    const sortedData = sortData(filteredData);
    
    renderTableHeader();
    renderTableBody(sortedData);
    updateStats(sortedData);
}

function renderTableHeader() {
    // Always show repo first, then other visible columns in alphabetical order
    const visibleCols = getVisibleColumns();
    
    console.log('Rendering table header with columns:', visibleCols);
    
    elements.tableHead.innerHTML = `
        <tr>
            ${visibleCols.map(col => `
                <th data-column="${col}" 
                    class="${col === state.sortColumn ? `sort-${state.sortDirection}` : ''}"
                    onclick="sortTable('${col}', '${col === state.sortColumn && state.sortDirection === 'asc' ? 'desc' : 'asc'}')">
                    ${formatColumnName(col)}
                </th>
            `).join('')}
        </tr>
    `;
}

function renderTableBody(data) {
    const visibleCols = getVisibleColumns();
    
    console.log('Rendering table body with', data.length, 'rows and', visibleCols.length, 'columns');
    
    if (data.length === 0) {
        elements.tableBody.innerHTML = `
            <tr>
                <td colspan="${visibleCols.length}" class="loading">
                    No repositories match your filters. Try adjusting your search or filters.
                </td>
            </tr>
        `;
        return;
    }
    
    elements.tableBody.innerHTML = data.map(row => `
        <tr>
            ${visibleCols.map(col => {
                const value = row[col];
                
                if (col === 'repo') {
                    return `<td class="repo-cell">${escapeHtml(value || '')}</td>`;
                } else {
                    return renderTableCell(value);
                }
            }).join('')}
        </tr>
    `).join('');
}

function getVisibleColumns() {
    return [
        'repo', 
        ...Array.from(state.visibleColumns)
            .filter(col => col !== 'repo')
            .sort()
    ];
}

function renderTableCell(value) {
    if (!hasData(value)) {
        return `<td class="empty-cell" title="No data">—</td>`;
    }
    
    const strValue = String(value).trim();
    
    // Handle checkmarks and boolean values
    if (strValue === '✔' || strValue === 'true' || strValue === 'yes' || value === true) {
        return `<td class="check-cell" title="Present"><span class="badge">✓</span></td>`;
    }
    
    // Handle false values
    if (strValue === '✘' || strValue === 'false' || strValue === 'no' || value === false) {
        return `<td class="cross-cell" title="Not present"><span class="badge cross">✘</span></td>`;
    }
    
    // Handle URLs
    if (strValue.startsWith('http://') || strValue.startsWith('https://')) {
        return `<td class="url-cell" title="${escapeHtml(strValue)}"><a href="${escapeHtml(strValue)}" target="_blank" rel="noopener">🔗 Link</a></td>`;
    }
    
    // Handle long text (truncate)
    if (strValue.length > 50) {
        return `<td class="text-cell" title="${escapeHtml(strValue)}">${escapeHtml(strValue.substring(0, 47))}...</td>`;
    }
    
    // Regular text
    return `<td class="text-cell">${escapeHtml(strValue)}</td>`;
}

function sortData(data) {
    return [...data].sort((a, b) => {
        const aVal = String(a[state.sortColumn] || '').toLowerCase();
        const bVal = String(b[state.sortColumn] || '').toLowerCase();
        
        if (state.sortDirection === 'asc') {
            return aVal.localeCompare(bVal, undefined, { numeric: true, sensitivity: 'base' });
        } else {
            return bVal.localeCompare(aVal, undefined, { numeric: true, sensitivity: 'base' });
        }
    });
}

function formatColumnName(column) {
    // Convert snake_case and kebab-case to Title Case
    return column
        .replace(/[_-]/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function togglePanel(panel) {
    panel.classList.toggle('hidden');
    
    // Close other panels
    const allPanels = [elements.filtersPanel, elements.columnsPanel];
    allPanels.forEach(p => {
        if (p !== panel && !p.classList.contains('hidden')) {
            p.classList.add('hidden');
        }
    });
}

function toggleTheme() {
    document.body.classList.toggle('dark');
    localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
}

function loadThemePreference() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark');
    }
}

function exportToCSV() {
    const filteredData = getFilteredData();
    const visibleCols = getVisibleColumns();
    
    const headers = visibleCols.map(col => formatColumnName(col)).join(',');
    
    const rows = filteredData.map(row => 
        visibleCols.map(col => {
            const value = row[col];
            if (!hasData(value)) {
                return '';
            }
            
            const strValue = String(value).trim();
            if (strValue === '✔' || strValue === 'true' || strValue === 'yes' || value === true) {
                return 'Yes';
            }
            if (strValue === '✘' || strValue === 'false' || strValue === 'no' || value === false) {
                return 'No';
            }
            
            // Escape CSV special characters and wrap in quotes
            return `"${strValue.replace(/"/g, '""')}"`;
        }).join(',')
    );
    
    const csvContent = [headers, ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `owasp-metadata-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function debugFieldCounts() {
    console.group('Field Analysis');
    console.log('Total columns detected:', state.columns.length);
    console.log('Columns:', state.columns);
    
    state.columns.forEach(col => {
        const count = state.matrixData.filter(row => hasData(row[col])).length;
        console.log(`${col}: ${count} repositories have data`);
    });
    
    console.groupEnd();
}

// Make sortTable available globally for header clicks
window.sortTable = sortTable;

loadMatrix().then(() => {
    setTimeout(debugFieldCounts, 1000);
});