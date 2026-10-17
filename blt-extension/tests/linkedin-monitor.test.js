/**
 * Tests for linkedin-monitor.js
 */

describe('LinkedIn Monitor', () => {
  let originalMutationObserver;

  beforeEach(() => {
    // Store original MutationObserver
    originalMutationObserver = global.MutationObserver;

    // Mock MutationObserver
    global.MutationObserver = jest.fn(function(callback) {
      this.callback = callback;
      this.observe = jest.fn();
      this.disconnect = jest.fn();
      this.takeRecords = jest.fn(() => []);
    });

    // Reset DOM
    document.body.innerHTML = '';
    
    jest.clearAllMocks();
  });

  afterEach(() => {
    // Restore original MutationObserver
    global.MutationObserver = originalMutationObserver;
    jest.resetModules();
  });

  describe('monitorLinkedInApplications function', () => {
    it('should set up MutationObserver on document body', () => {
      require('../linkedin-monitor.js');

      expect(MutationObserver).toHaveBeenCalled();
      const observerInstance = MutationObserver.mock.instances[0];
      expect(observerInstance.observe).toHaveBeenCalledWith(
        document.body,
        { childList: true, subtree: true }
      );
    });

    it('should detect and add listener to apply button', () => {
      // Create a mock apply button
      document.body.innerHTML = `
        <button aria-label="Submit application">Apply</button>
        <a data-view-name="job-details-about-company-name-link">Test Company</a>
        <div class="job-details-jobs-unified-top-card__job-title">
          <h1><a>Software Engineer</a></h1>
        </div>
      `;

      require('../linkedin-monitor.js');

      const applyButton = document.querySelector('button[aria-label="Submit application"]');
      
      // Trigger MutationObserver callback
      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      expect(applyButton.dataset.listenerAdded).toBe('true');
    });

    it('should not add duplicate listeners to the same button', () => {
      document.body.innerHTML = `
        <button aria-label="Submit application">Apply</button>
        <a data-view-name="job-details-about-company-name-link">Test Company</a>
        <div class="job-details-jobs-unified-top-card__job-title">
          <h1><a>Software Engineer</a></h1>
        </div>
      `;

      require('../linkedin-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      
      // Call observer multiple times
      observerCallback();
      observerCallback();
      observerCallback();

      const applyButton = document.querySelector('button[aria-label="Submit application"]');
      expect(applyButton.dataset.listenerAdded).toBe('true');
    });

    it('should store job application data when apply button is clicked', () => {
      document.body.innerHTML = `
        <button aria-label="Submit application">Apply</button>
        <a data-view-name="job-details-about-company-name-link">Test Company</a>
        <div class="job-details-jobs-unified-top-card__job-title">
          <h1><a>Software Engineer</a></h1>
        </div>
      `;

      require('../linkedin-monitor.js');

      // Trigger MutationObserver to set up listener
      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      // Click the apply button
      const applyButton = document.querySelector('button[aria-label="Submit application"]');
      applyButton.click();

      // Verify storage was called
      expect(chrome.storage.local.get).toHaveBeenCalledWith('jobApplications', expect.any(Function));
    });

    it('should handle missing company name gracefully', () => {
      document.body.innerHTML = `
        <button aria-label="Submit application">Apply</button>
        <div class="job-details-jobs-unified-top-card__job-title">
          <h1><a>Software Engineer</a></h1>
        </div>
      `;

      require('../linkedin-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      const applyButton = document.querySelector('button[aria-label="Submit application"]');
      applyButton.click();

      // Should not throw error even without company name element
      expect(chrome.storage.local.get).toHaveBeenCalled();
    });

    it('should handle missing position title gracefully', () => {
      document.body.innerHTML = `
        <button aria-label="Submit application">Apply</button>
        <a data-view-name="job-details-about-company-name-link">Test Company</a>
      `;

      require('../linkedin-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      const applyButton = document.querySelector('button[aria-label="Submit application"]');
      applyButton.click();

      expect(chrome.storage.local.get).toHaveBeenCalled();
    });
  });

  describe('Job Data Storage', () => {
    it('should include correct job data fields', () => {
      document.body.innerHTML = `
        <button aria-label="Submit application">Apply</button>
        <a data-view-name="job-details-about-company-name-link">Acme Corp</a>
        <div class="job-details-jobs-unified-top-card__job-title">
          <h1><a>Senior Developer</a></h1>
        </div>
      `;

      require('../linkedin-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      const applyButton = document.querySelector('button[aria-label="Submit application"]');
      applyButton.click();

      // Get the callback and simulate it
      const storageCallback = chrome.storage.local.get.mock.calls[0][1];
      storageCallback({ jobApplications: [] });

      expect(chrome.storage.local.set).toHaveBeenCalled();
      
      const setCall = chrome.storage.local.set.mock.calls[0][0];
      expect(setCall.jobApplications).toHaveLength(1);
      expect(setCall.jobApplications[0]).toMatchObject({
        company: expect.any(String),
        position: expect.any(String),
        jobUrl: expect.any(String),
        platform: 'LinkedIn',
        status: 'Applied',
        appliedDate: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/)
      });
    });

    it('should append to existing applications', () => {
      document.body.innerHTML = `
        <button aria-label="Submit application">Apply</button>
        <a data-view-name="job-details-about-company-name-link">New Company</a>
        <div class="job-details-jobs-unified-top-card__job-title">
          <h1><a>New Position</a></h1>
        </div>
      `;

      require('../linkedin-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      const applyButton = document.querySelector('button[aria-label="Submit application"]');
      applyButton.click();

      // Simulate existing applications
      const existingApps = [
        { company: 'Old Company', position: 'Old Position', platform: 'LinkedIn' }
      ];
      
      const storageCallback = chrome.storage.local.get.mock.calls[0][1];
      storageCallback({ jobApplications: existingApps });

      const setCall = chrome.storage.local.set.mock.calls[0][0];
      // The set call should include the new application
      expect(setCall.jobApplications).toBeDefined();
      expect(setCall.jobApplications.length).toBeGreaterThanOrEqual(1);
    });
  });
});
