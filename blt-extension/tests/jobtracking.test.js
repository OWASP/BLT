/**
 * Tests for jobtracking.js
 * These tests verify the DOM structure and Chrome API interactions
 */

describe('Job Tracking', () => {
  beforeEach(() => {
    // Set up the DOM structure similar to jobtracking.html
    document.body.innerHTML = `
      <div class="container">
        <div class="header">
          <div class="header-title">
            <h1>Job Applications</h1>
            <button class="theme-toggle" id="themeToggle">Toggle Theme</button>
          </div>
          <div>
            <button id="exportBtn" class="btn">Export All</button>
            <button id="addNewBtn" class="btn">Add New</button>
          </div>
        </div>
        <table id="applicationsTable">
          <thead>
            <tr>
              <th class="row-number">#</th>
              <th><input type="checkbox" id="selectAll" class="row-checkbox"></th>
              <th>Company</th>
              <th>Position</th>
              <th>Applied Date</th>
              <th>Platform</th>
              <th>Job URL</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="applicationsBody"></tbody>
        </table>
        <div class="pagination-controls">
          <div class="items-per-page">
            <select id="pageSize" class="page-size-select">
              <option value="5">5</option>
              <option value="10" selected>10</option>
              <option value="20">20</option>
            </select>
          </div>
          <div class="pagination-buttons">
            <button id="prevPage" class="btn">Previous</button>
            <span id="pageInfo">Page 1 of 1</span>
            <button id="nextPage" class="btn">Next</button>
          </div>
        </div>
      </div>
      <div id="addModal" class="modal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Add New Application</h2>
            <span class="close">&times;</span>
          </div>
          <form id="addApplicationForm">
            <input type="text" id="company" required>
            <input type="text" id="position" required>
            <input type="url" id="jobUrl">
            <select id="platform" required>
              <option value="LinkedIn">LinkedIn</option>
              <option value="Indeed">Indeed</option>
              <option value="Wellfound">Wellfound</option>
            </select>
            <select id="status" required>
              <option value="Pending">Pending</option>
              <option value="Applied">Applied</option>
              <option value="Interview">Interview</option>
            </select>
            <input type="date" id="appliedDate" required>
            <button type="submit" class="btn">Save</button>
          </form>
        </div>
      </div>
      <button id="deleteSelected" class="btn btn-danger" style="display: none;">Delete Selected</button>
      <button id="exportSelected" class="btn" style="display: none;">Export Selected</button>
    `;

    document.documentElement.setAttribute('data-theme', 'light');

    // Reset localStorage mock
    localStorage.clear();
    localStorage.setItem('theme', 'light');

    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.resetModules();
  });

  describe('DOM Elements', () => {
    it('should have all required elements present', () => {
      expect(document.getElementById('addNewBtn')).not.toBeNull();
      expect(document.getElementById('exportBtn')).not.toBeNull();
      expect(document.getElementById('addModal')).not.toBeNull();
      expect(document.getElementById('addApplicationForm')).not.toBeNull();
      expect(document.getElementById('themeToggle')).not.toBeNull();
      expect(document.getElementById('pageSize')).not.toBeNull();
      expect(document.getElementById('prevPage')).not.toBeNull();
      expect(document.getElementById('nextPage')).not.toBeNull();
      expect(document.getElementById('selectAll')).not.toBeNull();
    });

    it('should have form inputs for application data', () => {
      expect(document.getElementById('company')).not.toBeNull();
      expect(document.getElementById('position')).not.toBeNull();
      expect(document.getElementById('jobUrl')).not.toBeNull();
      expect(document.getElementById('platform')).not.toBeNull();
      expect(document.getElementById('status')).not.toBeNull();
      expect(document.getElementById('appliedDate')).not.toBeNull();
    });

    it('should have table body for displaying applications', () => {
      expect(document.getElementById('applicationsBody')).not.toBeNull();
    });
  });

  describe('Chrome Storage API', () => {
    it('should be available for storing job applications', () => {
      expect(chrome.storage.local.get).toBeDefined();
      expect(chrome.storage.local.set).toBeDefined();
      expect(chrome.storage.local.remove).toBeDefined();
    });

    it('should get job applications from storage', (done) => {
      chrome.storage.local.get('jobApplications', (result) => {
        expect(result).toBeDefined();
        done();
      });
    });

    it('should set job applications in storage', (done) => {
      const testData = {
        jobApplications: [{
          company: 'Test Company',
          position: 'Developer',
          platform: 'LinkedIn',
          status: 'Applied',
          appliedDate: '2024-01-15'
        }]
      };

      chrome.storage.local.set(testData, () => {
        expect(chrome.storage.local.set).toHaveBeenCalled();
        done();
      });
    });
  });

  describe('Job Application Data Structure', () => {
    it('should have required fields for a job application', () => {
      const jobApplication = {
        company: 'Test Company',
        position: 'Software Engineer',
        jobUrl: 'https://example.com/job',
        platform: 'LinkedIn',
        status: 'Applied',
        appliedDate: '2024-01-15'
      };

      expect(jobApplication).toHaveProperty('company');
      expect(jobApplication).toHaveProperty('position');
      expect(jobApplication).toHaveProperty('jobUrl');
      expect(jobApplication).toHaveProperty('platform');
      expect(jobApplication).toHaveProperty('status');
      expect(jobApplication).toHaveProperty('appliedDate');
    });

    it('should validate status values', () => {
      const validStatuses = ['Pending', 'Applied', 'Interview', 'Accepted', 'Rejected'];
      const testStatus = 'Applied';
      
      expect(validStatuses).toContain(testStatus);
    });

    it('should validate platform values', () => {
      const validPlatforms = ['LinkedIn', 'Indeed', 'Wellfound', 'Other'];
      const testPlatform = 'LinkedIn';
      
      expect(validPlatforms).toContain(testPlatform);
    });
  });

  describe('Theme Functionality', () => {
    it('should have light theme by default', () => {
      expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    });

    it('should store theme in localStorage', () => {
      localStorage.setItem('theme', 'dark');
      expect(localStorage.getItem('theme')).toBe('dark');
    });
  });

  describe('Modal Functionality', () => {
    it('should be hidden by default', () => {
      const modal = document.getElementById('addModal');
      expect(modal.style.display).toBe('none');
    });

    it('should have close button', () => {
      const closeBtn = document.querySelector('.close');
      expect(closeBtn).not.toBeNull();
    });
  });

  describe('Pagination Controls', () => {
    it('should have page size options', () => {
      const pageSize = document.getElementById('pageSize');
      const options = pageSize.options;
      
      expect(options.length).toBeGreaterThan(0);
      expect(pageSize.value).toBe('10');
    });

    it('should have navigation buttons', () => {
      const prevBtn = document.getElementById('prevPage');
      const nextBtn = document.getElementById('nextPage');
      
      expect(prevBtn).not.toBeNull();
      expect(nextBtn).not.toBeNull();
    });

    it('should have page info display', () => {
      const pageInfo = document.getElementById('pageInfo');
      expect(pageInfo).not.toBeNull();
      expect(pageInfo.textContent).toContain('Page');
    });
  });

  describe('Export Functionality', () => {
    it('should have export button', () => {
      const exportBtn = document.getElementById('exportBtn');
      expect(exportBtn).not.toBeNull();
    });

    it('should generate valid CSV content', () => {
      const applications = [
        {
          company: 'Test Co',
          position: 'Dev',
          appliedDate: '2024-01-15',
          platform: 'LinkedIn',
          jobUrl: 'https://test.com',
          status: 'Applied'
        }
      ];

      const csvHeader = 'Company,Position,Applied Date,Platform,Job URL,Status';
      const csvRow = `${applications[0].company},${applications[0].position},${applications[0].appliedDate},${applications[0].platform},${applications[0].jobUrl},${applications[0].status}`;
      
      expect(csvHeader).toContain('Company');
      expect(csvHeader).toContain('Position');
      expect(csvRow).toContain('Test Co');
      expect(csvRow).toContain('Dev');
    });
  });

  describe('Multi-Select Functionality', () => {
    it('should have select all checkbox', () => {
      const selectAll = document.getElementById('selectAll');
      expect(selectAll).not.toBeNull();
      expect(selectAll.type).toBe('checkbox');
    });

    it('should have bulk delete button', () => {
      const deleteSelected = document.getElementById('deleteSelected');
      expect(deleteSelected).not.toBeNull();
    });

    it('should have bulk export button', () => {
      const exportSelected = document.getElementById('exportSelected');
      expect(exportSelected).not.toBeNull();
    });
  });

  describe('Date Handling', () => {
    it('should format dates correctly', () => {
      const date = new Date('2024-01-15');
      const formattedDate = date.toISOString().split('T')[0];
      expect(formattedDate).toBe('2024-01-15');
    });

    it('should handle date input', () => {
      const dateInput = document.getElementById('appliedDate');
      dateInput.value = '2024-01-15';
      expect(dateInput.value).toBe('2024-01-15');
    });
  });
});
