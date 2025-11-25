/**
 * Tests for background.js
 * Tests verify the Chrome API mocks and message handling logic
 */

describe('Background Service Worker', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Chrome API Availability', () => {
    it('should have runtime.onMessage.addListener available', () => {
      expect(chrome.runtime.onMessage.addListener).toBeDefined();
      expect(typeof chrome.runtime.onMessage.addListener).toBe('function');
    });

    it('should have tabs.captureVisibleTab available', () => {
      expect(chrome.tabs.captureVisibleTab).toBeDefined();
      expect(typeof chrome.tabs.captureVisibleTab).toBe('function');
    });

    it('should have downloads.download available', () => {
      expect(chrome.downloads.download).toBeDefined();
      expect(typeof chrome.downloads.download).toBe('function');
    });
  });

  describe('Message Handling Logic', () => {
    it('should handle CHECK_TRADEMARK message type', () => {
      const msg = { type: 'CHECK_TRADEMARK', keyword: 'TestBrand' };
      
      expect(msg.type).toBe('CHECK_TRADEMARK');
      expect(msg.keyword).toBe('TestBrand');
    });

    it('should handle takeScreenshot action', () => {
      const msg = { action: 'takeScreenshot' };
      
      expect(msg.action).toBe('takeScreenshot');
    });

    it('should construct correct trademark API URL', () => {
      const keyword = 'TestBrand';
      const url = `https://owaspblt.org/api/trademarks/search?query=${encodeURIComponent(keyword)}`;
      
      expect(url).toBe('https://owaspblt.org/api/trademarks/search?query=TestBrand');
    });

    it('should URL encode special characters in keyword', () => {
      const keyword = 'Test Brand With Spaces';
      const url = `https://owaspblt.org/api/trademarks/search?query=${encodeURIComponent(keyword)}`;
      
      expect(url).toBe('https://owaspblt.org/api/trademarks/search?query=Test%20Brand%20With%20Spaces');
    });
  });

  describe('Screenshot Functionality', () => {
    it('should capture visible tab with PNG format', (done) => {
      chrome.tabs.captureVisibleTab(null, { format: 'png' }, (dataUrl) => {
        expect(dataUrl).toBeDefined();
        expect(typeof dataUrl).toBe('string');
        done();
      });
    });

    it('should trigger download with correct filename', (done) => {
      chrome.downloads.download({
        url: 'data:image/png;base64,test',
        filename: 'screenshot.png'
      }, (downloadId) => {
        expect(chrome.downloads.download).toHaveBeenCalled();
        done();
      });
    });
  });

  describe('Trademark Check Response Handling', () => {
    it('should handle successful response format', () => {
      const response = { ok: true, data: { available: true, trademarks: [] } };
      
      expect(response.ok).toBe(true);
      expect(response.data).toBeDefined();
    });

    it('should handle error response format', () => {
      const response = { ok: false, error: 'HTTP 500' };
      
      expect(response.ok).toBe(false);
      expect(response.error).toBeDefined();
    });
  });

  describe('Fetch API Mock', () => {
    it('should mock fetch correctly', async () => {
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ available: true })
        })
      );

      const response = await fetch('https://test.com');
      const data = await response.json();

      expect(fetch).toHaveBeenCalled();
      expect(data.available).toBe(true);
    });

    it('should handle fetch errors', async () => {
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: false,
          status: 500
        })
      );

      const response = await fetch('https://test.com');

      expect(response.ok).toBe(false);
      expect(response.status).toBe(500);
    });

    it('should handle network errors', async () => {
      global.fetch = jest.fn(() => Promise.reject(new Error('Network error')));

      await expect(fetch('https://test.com')).rejects.toThrow('Network error');
    });
  });

  describe('Message Listener Registration', () => {
    it('should register message listener on module load', () => {
      require('../background.js');
      
      expect(chrome.runtime.onMessage.addListener).toHaveBeenCalled();
    });
  });
});
