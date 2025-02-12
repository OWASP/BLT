document.addEventListener('DOMContentLoaded', () => {
    // Initialize storage
    chrome.storage.local.get('jobApplications', function(result) {
        if (!result.jobApplications) {
            chrome.storage.local.set({ 'jobApplications': [] });
        }
        displayApplications();
    });

    // Get modal elements
    const modal = document.getElementById('addModal');
    const addNewBtn = document.getElementById('addNewBtn');
    const closeBtn = document.querySelector('.close');
    const themeToggle = document.getElementById('themeToggle');

    // Initialize theme
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // Set initial theme
    document.documentElement.setAttribute('data-theme', 
        localStorage.getItem('theme') || 'light'
    );

    // Initialize modal controls
    if (addNewBtn) {
        addNewBtn.onclick = function() {
            modal.style.display = "block";
            document.getElementById('appliedDate').valueAsDate = new Date();
            // Reset form state
            const form = document.getElementById('addApplicationForm');
            form.dataset.updating = 'false';
            form.dataset.updateIndex = '';
            document.querySelector('.modal-header h2').textContent = 'Add New Application';
        }
    }

    if (closeBtn) {
        closeBtn.onclick = function() {
            modal.style.display = "none";
        }
    }

    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    // Handle form submission
    document.getElementById('addApplicationForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Check if we're updating or adding new
        const isUpdating = this.dataset.updating === 'true';
        const updateIndex = parseInt(this.dataset.updateIndex);
        
        const newApplication = {
            company: document.getElementById('company').value,
            position: document.getElementById('position').value,
            jobUrl: document.getElementById('jobUrl').value,
            platform: document.getElementById('platform').value,
            status: document.getElementById('status').value,
            appliedDate: document.getElementById('appliedDate').value
        };

        chrome.storage.local.get('jobApplications', function(result) {
            const applications = result.jobApplications || [];
            
            if (isUpdating) {
                applications[updateIndex] = newApplication;
            } else {
                applications.push(newApplication);
            }
            
            chrome.storage.local.set({ 'jobApplications': applications }, function() {
                displayApplications();
                modal.style.display = "none";
                document.getElementById('addApplicationForm').reset();
                // Reset form state
                document.getElementById('addApplicationForm').dataset.updating = 'false';
                document.getElementById('addApplicationForm').dataset.updateIndex = '';
            });
        });
    });

    // Add pagination state
    let currentPage = 1;
    let pageSize = 10;
    let selectedRows = new Set();

    // Set default page size in dropdown
    document.getElementById('pageSize').value = pageSize;

    // Update display applications function
    function displayApplications() {
        chrome.storage.local.get('jobApplications', function(result) {
            const applications = result.jobApplications || [];
            const tbody = document.getElementById('applicationsBody');
            tbody.innerHTML = '';

            // Calculate pagination
            const totalPages = Math.ceil(applications.length / pageSize);
            const start = (currentPage - 1) * pageSize;
            const end = start + pageSize;
            const pageApplications = applications.slice(start, end);

            // Update page info
            document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;

            // Update select all checkbox state
            const selectAllCheckbox = document.getElementById('selectAll');
            const pageIndices = Array.from({length: end - start}, (_, i) => start + i);
            const allPageSelected = pageIndices.every(index => selectedRows.has(index));
            selectAllCheckbox.checked = allPageSelected;
            selectAllCheckbox.indeterminate = !allPageSelected && pageIndices.some(index => selectedRows.has(index));

            // Update bulk action buttons
            updateBulkActionButtons();

            pageApplications.forEach((app, index) => {
                const globalIndex = start + index;
                const row = document.createElement('tr');
                row.className = selectedRows.has(globalIndex) ? 'selected-row' : '';
                
                // Create all cells properly
                const cells = [
                    // Row number
                    { content: globalIndex + 1, className: 'row-number' },
                    // Checkbox
                    {
                        content: document.createElement('input'),
                        setup: (cell, element) => {
                            element.type = 'checkbox';
                            element.className = 'row-checkbox';
                            element.checked = selectedRows.has(globalIndex);
                            element.addEventListener('change', () => toggleRowSelection(globalIndex));
                            cell.appendChild(element);
                        }
                    },
                    // Company
                    { content: app.company },
                    // Position
                    { content: app.position },
                    // Applied Date
                    { content: new Date(app.appliedDate).toLocaleDateString() },
                    // Platform
                    { content: app.platform },
                    // Job URL
                    { content: app.jobUrl ? `<a href="${app.jobUrl}" target="_blank">View</a>` : '-', isHTML: true },
                    // Status
                    { content: `<span class="status-badge status-${app.status.toLowerCase()}">${app.status}</span>`, isHTML: true },
                    // Actions
                    {
                        content: '',
                        setup: (cell) => {
                            const updateBtn = document.createElement('button');
                            updateBtn.textContent = 'Update';
                            updateBtn.className = 'btn btn-small';
                            updateBtn.addEventListener('click', () => updateStatus(globalIndex));

                            const deleteBtn = document.createElement('button');
                            deleteBtn.textContent = 'Delete';
                            deleteBtn.className = 'btn btn-small btn-danger';
                            deleteBtn.addEventListener('click', () => deleteApplication(globalIndex));

                            cell.appendChild(updateBtn);
                            cell.appendChild(deleteBtn);
                        }
                    }
                ];

                // Create and append all cells
                cells.forEach(cellData => {
                    const cell = document.createElement('td');
                    if (cellData.className) {
                        cell.className = cellData.className;
                    }
                    if (cellData.setup) {
                        cellData.setup(cell, cellData.content);
                    } else if (cellData.isHTML) {
                        cell.innerHTML = cellData.content;
                    } else {
                        cell.textContent = cellData.content;
                    }
                    row.appendChild(cell);
                });

                tbody.appendChild(row);
            });
        });
    }

    // Export to CSV
    document.getElementById('exportBtn').addEventListener('click', function() {
        chrome.storage.local.get('jobApplications', function(result) {
            const applications = result.jobApplications || [];
            const selectedApplications = selectedRows.size > 0 
                ? applications.filter((_, index) => selectedRows.has(index))
                : applications;
            
            const csvContent = "data:text/csv;charset=utf-8," 
                + "Company,Position,Applied Date,Platform,Job URL,Status\n"
                + selectedApplications.map(app => {
                    return `${app.company},${app.position},${app.appliedDate},${app.platform},${app.jobUrl || ''},${app.status}`;
                }).join("\n");

            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", "job_applications.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    });

    // Add delete functionality
    function deleteApplication(index) {
        if (confirm('Are you sure you want to delete this application?')) {
            chrome.storage.local.get('jobApplications', function(result) {
                const applications = result.jobApplications || [];
                applications.splice(index, 1);
                chrome.storage.local.set({ 'jobApplications': applications }, function() {
                    displayApplications();
                });
            });
        }
    }

    // Add update functionality
    function updateStatus(index) {
        chrome.storage.local.get('jobApplications', function(result) {
            const applications = result.jobApplications || [];
            const app = applications[index];
            
            // Pre-fill the form with existing data
            document.getElementById('company').value = app.company;
            document.getElementById('position').value = app.position;
            document.getElementById('jobUrl').value = app.jobUrl || '';
            document.getElementById('platform').value = app.platform;
            document.getElementById('status').value = app.status;
            document.getElementById('appliedDate').value = app.appliedDate;
            
            // Set form state to updating
            const form = document.getElementById('addApplicationForm');
            form.dataset.updating = 'true';
            form.dataset.updateIndex = index;
            
            // Show modal
            modal.style.display = "block";
            document.querySelector('.modal-header h2').textContent = 'Update Application';
        });
    }

    // Add multi-select functionality
    function toggleRowSelection(index) {
        if (selectedRows.has(index)) {
            selectedRows.delete(index);
        } else {
            selectedRows.add(index);
        }
        updateBulkActionButtons();
        displayApplications();
    }

    // Add pagination event listeners
    document.getElementById('pageSize').addEventListener('change', function(e) {
        pageSize = parseInt(e.target.value);
        currentPage = 1;
        displayApplications();
    });

    document.getElementById('prevPage').addEventListener('click', function() {
        if (currentPage > 1) {
            currentPage--;
            displayApplications();
        }
    });

    document.getElementById('nextPage').addEventListener('click', function() {
        chrome.storage.local.get('jobApplications', function(result) {
            const totalPages = Math.ceil((result.jobApplications || []).length / pageSize);
            if (currentPage < totalPages) {
                currentPage++;
                displayApplications();
            }
        });
    });

    // Handle select all checkbox
    document.getElementById('selectAll').addEventListener('change', function(e) {
        const isChecked = e.target.checked;
        chrome.storage.local.get('jobApplications', function(result) {
            const applications = result.jobApplications || [];
            const start = (currentPage - 1) * pageSize;
            const end = Math.min(start + pageSize, applications.length);
            
            for (let i = start; i < end; i++) {
                if (isChecked) {
                    selectedRows.add(i);
                } else {
                    selectedRows.delete(i);
                }
            }
            updateBulkActionButtons();
            displayApplications();
        });
    });

    // Add bulk delete button
    const bulkActionDiv = document.createElement('div');
    bulkActionDiv.innerHTML = `
        <button id="deleteSelected" class="btn btn-danger" style="display: none;">Delete Selected</button>
        <button id="exportSelected" class="btn" style="display: none;">Export Selected</button>
    `;
    document.querySelector('.header').appendChild(bulkActionDiv);

    // Handle bulk delete
    document.getElementById('deleteSelected').addEventListener('click', function() {
        if (selectedRows.size === 0) return;
        
        if (confirm(`Are you sure you want to delete ${selectedRows.size} selected applications?`)) {
            chrome.storage.local.get('jobApplications', function(result) {
                const applications = result.jobApplications || [];
                const newApplications = applications.filter((_, index) => !selectedRows.has(index));
                chrome.storage.local.set({ 'jobApplications': newApplications }, function() {
                    selectedRows.clear();
                    displayApplications();
                });
            });
        }
    });

    // Update export functionality to handle selected rows
    document.getElementById('exportSelected').addEventListener('click', function() {
        chrome.storage.local.get('jobApplications', function(result) {
            const applications = result.jobApplications || [];
            const selectedApplications = applications.filter((_, index) => selectedRows.has(index));
            
            if (selectedApplications.length === 0) {
                alert('Please select applications to export');
                return;
            }

            const csvContent = "data:text/csv;charset=utf-8," 
                + "Company,Position,Applied Date,Platform,Job URL,Status\n"
                + selectedApplications.map(app => {
                    return `${app.company},${app.position},${app.appliedDate},${app.platform},${app.jobUrl || ''},${app.status}`;
                }).join("\n");

            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", "selected_applications.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    });

    // Update display to show/hide bulk action buttons
    function updateBulkActionButtons() {
        const deleteBtn = document.getElementById('deleteSelected');
        const exportBtn = document.getElementById('exportSelected');
        if (selectedRows.size > 0) {
            deleteBtn.style.display = 'inline-block';
            exportBtn.style.display = 'inline-block';
        } else {
            deleteBtn.style.display = 'none';
            exportBtn.style.display = 'none';
        }
    }
}); 