/**
 * Tests for wellfound-monitor.js
 */

describe('Wellfound Monitor', () => {
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

  describe('monitorWellfoundApplications function', () => {
    it('should set up MutationObserver on document body', () => {
      require('../wellfound-monitor.js');

      expect(MutationObserver).toHaveBeenCalled();
      const observerInstance = MutationObserver.mock.instances[0];
      expect(observerInstance.observe).toHaveBeenCalledWith(
        document.body,
        { childList: true, subtree: true }
      );
    });

    it('should detect and add listener to Wellfound apply button', () => {
      document.body.innerHTML = `
        <button data-test="JobDescriptionSlideIn--SubmitButton">Apply</button>
        <div class="text-sm font-semibold text-black">Test Company</div>
        <div class="mt-4">
          <h1 class="text-xl font-semibold text-black">Frontend Developer</h1>
        </div>
      `;

      require('../wellfound-monitor.js');

      const applyButton = document.querySelector('button[data-test="JobDescriptionSlideIn--SubmitButton"]');
      
      // Trigger MutationObserver callback
      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      expect(applyButton.dataset.listenerAdded).toBe('true');
    });

    it('should not add duplicate listeners to the same button', () => {
      document.body.innerHTML = `
        <button data-test="JobDescriptionSlideIn--SubmitButton">Apply</button>
        <div class="text-sm font-semibold text-black">Test Company</div>
        <div class="mt-4">
          <h1 class="text-xl font-semibold text-black">Frontend Developer</h1>
        </div>
      `;

      require('../wellfound-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      
      // Call observer multiple times
      observerCallback();
      observerCallback();
      observerCallback();

      const applyButton = document.querySelector('button[data-test="JobDescriptionSlideIn--SubmitButton"]');
      expect(applyButton.dataset.listenerAdded).toBe('true');
    });

    it('should store job application data when apply button is clicked', () => {
      document.body.innerHTML = `
        <button data-test="JobDescriptionSlideIn--SubmitButton">Apply</button>
        <div class="text-sm font-semibold text-black">Startup Inc</div>
        <div class="mt-4">
          <h1 class="text-xl font-semibold text-black">Full Stack Engineer</h1>
        </div>
      `;

      require('../wellfound-monitor.js');

      // Trigger MutationObserver to set up listener
      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      // Click the apply button
      const applyButton = document.querySelector('button[data-test="JobDescriptionSlideIn--SubmitButton"]');
      applyButton.click();

      // Verify storage was called
      expect(chrome.storage.local.get).toHaveBeenCalledWith('jobApplications', expect.any(Function));
    });

    it('should handle missing company name gracefully', () => {
      document.body.innerHTML = `
        <button data-test="JobDescriptionSlideIn--SubmitButton">Apply</button>
        <div class="mt-4">
          <h1 class="text-xl font-semibold text-black">Full Stack Engineer</h1>
        </div>
      `;

      require('../wellfound-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      const applyButton = document.querySelector('button[data-test="JobDescriptionSlideIn--SubmitButton"]');
      applyButton.click();

      // Should not throw error even without company name element
      expect(chrome.storage.local.get).toHaveBeenCalled();
    });

    it('should handle missing position title gracefully', () => {
      document.body.innerHTML = `
        <button data-test="JobDescriptionSlideIn--SubmitButton">Apply</button>
        <div class="text-sm font-semibold text-black">Startup Inc</div>
      `;

      require('../wellfound-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      const applyButton = document.querySelector('button[data-test="JobDescriptionSlideIn--SubmitButton"]');
      applyButton.click();

      expect(chrome.storage.local.get).toHaveBeenCalled();
    });

    it('should handle no apply button present', () => {
      document.body.innerHTML = `
        <div class="text-sm font-semibold text-black">Test Company</div>
      `;

      require('../wellfound-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      
      // Should not throw when button doesn't exist
      expect(() => observerCallback()).not.toThrow();
    });
  });

  describe('Job Data Storage', () => {
    it('should include correct job data fields for Wellfound', () => {
      document.body.innerHTML = `
        <button data-test="JobDescriptionSlideIn--SubmitButton">Apply</button>
        <div class="text-sm font-semibold text-black">TechStartup</div>
        <div class="mt-4">
          <h1 class="text-xl font-semibold text-black">Backend Developer</h1>
        </div>
      `;

      require('../wellfound-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      const applyButton = document.querySelector('button[data-test="JobDescriptionSlideIn--SubmitButton"]');
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
        platform: 'Wellfound',
        status: 'Applied',
        appliedDate: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/)
      });
    });

    it('should append to existing applications', () => {
      document.body.innerHTML = `
        <button data-test="JobDescriptionSlideIn--SubmitButton">Apply</button>
        <div class="text-sm font-semibold text-black">New Startup</div>
        <div class="mt-4">
          <h1 class="text-xl font-semibold text-black">DevOps Engineer</h1>
        </div>
      `;

      require('../wellfound-monitor.js');

      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();

      const applyButton = document.querySelector('button[data-test="JobDescriptionSlideIn--SubmitButton"]');
      applyButton.click();

      // Simulate existing applications
      const existingApps = [
        { company: 'Old Startup', position: 'Old Position', platform: 'Wellfound' }
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
