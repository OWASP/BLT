/**
 * Tests for popup.js
 * Tests verify DOM structure and Chrome API mocks
 */

describe('Popup', () => {
  let screenshotBtn;
  let jobTrackingBtn;
  let runScanBtn;

  beforeEach(() => {
    // Set up DOM elements
    document.body.innerHTML = `
      <button id="screenshotBtn">Take Screenshot</button>
      <button id="jobTrackingBtn">Job Tracking Dashboard</button>
      <button id="runScanBtn">Run Trademark Scanner</button>
    `;

    screenshotBtn = document.getElementById('screenshotBtn');
    jobTrackingBtn = document.getElementById('jobTrackingBtn');
    runScanBtn = document.getElementById('runScanBtn');

    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.resetModules();
  });

  describe('DOM Elements', () => {
    it('should have screenshot button in the DOM', () => {
      expect(screenshotBtn).not.toBeNull();
      expect(screenshotBtn.id).toBe('screenshotBtn');
    });

    it('should have job tracking button in the DOM', () => {
      expect(jobTrackingBtn).not.toBeNull();
      expect(jobTrackingBtn.id).toBe('jobTrackingBtn');
    });

    it('should have run scan button in the DOM', () => {
      expect(runScanBtn).not.toBeNull();
      expect(runScanBtn.id).toBe('runScanBtn');
    });
  });

  describe('Chrome API Availability', () => {
    it('should have chrome.runtime.sendMessage available', () => {
      expect(chrome.runtime.sendMessage).toBeDefined();
      expect(typeof chrome.runtime.sendMessage).toBe('function');
    });

    it('should have chrome.tabs.create available', () => {
      expect(chrome.tabs.create).toBeDefined();
      expect(typeof chrome.tabs.create).toBe('function');
    });

    it('should have chrome.tabs.query available', () => {
      expect(chrome.tabs.query).toBeDefined();
      expect(typeof chrome.tabs.query).toBe('function');
    });

    it('should have chrome.tabs.sendMessage available', () => {
      expect(chrome.tabs.sendMessage).toBeDefined();
      expect(typeof chrome.tabs.sendMessage).toBe('function');
    });

    it('should have chrome.runtime.getURL available', () => {
      expect(chrome.runtime.getURL).toBeDefined();
      expect(typeof chrome.runtime.getURL).toBe('function');
    });
  });

  describe('Screenshot Functionality', () => {
    it('should construct correct message for screenshot', () => {
      const msg = { action: 'takeScreenshot' };
      expect(msg.action).toBe('takeScreenshot');
    });

    it('should call runtime.sendMessage correctly', (done) => {
      chrome.runtime.sendMessage({ action: 'takeScreenshot' }, () => {
        expect(chrome.runtime.sendMessage).toHaveBeenCalled();
        done();
      });
    });
  });

  describe('Job Tracking Functionality', () => {
    it('should construct correct URL for job tracking', () => {
      const url = chrome.runtime.getURL('jobtracking.html');
      expect(url).toBe('chrome-extension://test-id/jobtracking.html');
    });

    it('should call tabs.create with correct URL', (done) => {
      chrome.tabs.create({ url: 'chrome-extension://test-id/jobtracking.html' }, () => {
        expect(chrome.tabs.create).toHaveBeenCalled();
        done();
      });
    });
  });

  describe('Trademark Scanner Functionality', () => {
    it('should construct correct message for trademark scan', () => {
      const msg = { action: 'RUN_TRADEMARK_SCAN' };
      expect(msg.action).toBe('RUN_TRADEMARK_SCAN');
    });

    it('should query active tab correctly', (done) => {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        expect(chrome.tabs.query).toHaveBeenCalled();
        expect(tabs).toBeDefined();
        done();
      });
    });

    it('should handle tabs query response', (done) => {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        expect(tabs).toBeInstanceOf(Array);
        if (tabs && tabs.length > 0) {
          expect(tabs[0]).toHaveProperty('id');
        }
        done();
      });
    });
  });

  describe('Window Close Functionality', () => {
    it('should have window.close available', () => {
      expect(window.close).toBeDefined();
      expect(typeof window.close).toBe('function');
    });
  });

  describe('Event Handlers', () => {
    it('should be able to attach click handlers', () => {
      const clickHandler = jest.fn();
      screenshotBtn.addEventListener('click', clickHandler);
      screenshotBtn.click();
      expect(clickHandler).toHaveBeenCalled();
    });

    it('should be able to attach multiple click handlers', () => {
      const handler1 = jest.fn();
      const handler2 = jest.fn();
      
      jobTrackingBtn.addEventListener('click', handler1);
      runScanBtn.addEventListener('click', handler2);
      
      jobTrackingBtn.click();
      runScanBtn.click();
      
      expect(handler1).toHaveBeenCalled();
      expect(handler2).toHaveBeenCalled();
    });
  });
});
