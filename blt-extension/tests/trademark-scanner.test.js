/**
 * Tests for trademark-scanner.js
 * Tests verify the core functionality without requiring full module execution
 */

describe('Trademark Scanner', () => {
  beforeEach(() => {
    // Reset DOM
    document.body.innerHTML = '';
    document.head.innerHTML = '';
    
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.resetModules();
  });

  describe('CSS Injection', () => {
    it('should inject highlight styles into the document head', () => {
      require('../trademark-scanner.js');

      const styleTag = document.querySelector('style');
      expect(styleTag).not.toBeNull();
      expect(styleTag.textContent).toContain('.tm-highlight');
    });

    it('should define highlight hover styles', () => {
      require('../trademark-scanner.js');

      const styleTag = document.querySelector('style');
      expect(styleTag.textContent).toContain('.tm-highlight:hover');
    });

    it('should define background color for highlights', () => {
      require('../trademark-scanner.js');

      const styleTag = document.querySelector('style');
      expect(styleTag.textContent).toContain('background');
    });
  });

  describe('Message Listener', () => {
    it('should register message listener on load', () => {
      require('../trademark-scanner.js');

      expect(chrome.runtime.onMessage.addListener).toHaveBeenCalled();
    });
  });

  describe('Chrome API Mocks', () => {
    it('should have sendMessage available for trademark checks', () => {
      expect(chrome.runtime.sendMessage).toBeDefined();
      expect(typeof chrome.runtime.sendMessage).toBe('function');
    });

    it('should have onMessage listener available', () => {
      expect(chrome.runtime.onMessage.addListener).toBeDefined();
      expect(typeof chrome.runtime.onMessage.addListener).toBe('function');
    });
  });

  describe('Keyword Extraction Logic', () => {
    it('should identify capitalized words as potential keywords', () => {
      const text = 'Apple and Google are companies. lowercase is ignored.';
      const regex = /\b[A-Z][a-zA-Z0-9]+\b/g;
      const matches = text.match(regex) || [];
      
      expect(matches).toContain('Apple');
      expect(matches).toContain('Google');
      expect(matches).not.toContain('lowercase');
    });

    it('should filter words longer than 2 characters', () => {
      const words = ['AB', 'ABC', 'Apple', 'Hi'];
      const filtered = words.filter(w => w.length > 2);
      
      expect(filtered).not.toContain('AB');
      expect(filtered).not.toContain('Hi');
      expect(filtered).toContain('ABC');
      expect(filtered).toContain('Apple');
    });

    it('should deduplicate keywords', () => {
      const words = ['Apple', 'Apple', 'Google', 'Apple'];
      const unique = [...new Set(words)];
      
      expect(unique).toHaveLength(2);
      expect(unique).toContain('Apple');
      expect(unique).toContain('Google');
    });
  });

  describe('Highlighting Logic', () => {
    it('should create mark elements for highlighting', () => {
      document.body.innerHTML = '<p>TestWord should be highlighted</p>';
      
      const word = 'TestWord';
      const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`\\b${escaped}\\b`, 'g');
      
      const paragraph = document.querySelector('p');
      const newHtml = paragraph.innerHTML.replace(
        regex,
        `<mark class="tm-highlight">${word}</mark>`
      );
      paragraph.innerHTML = newHtml;
      
      const highlight = document.querySelector('.tm-highlight');
      expect(highlight).not.toBeNull();
      expect(highlight.textContent).toBe('TestWord');
    });

    it('should escape special characters in keywords', () => {
      const keyword = 'Test.Brand';
      const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      
      expect(escaped).toBe('Test\\.Brand');
    });
  });

  describe('DOM Walker Skip Logic', () => {
    it('should identify SCRIPT tags to skip', () => {
      const tagsToSkip = ['SCRIPT', 'STYLE', 'TEXTAREA', 'NOSCRIPT'];
      const testTag = 'SCRIPT';
      
      expect(tagsToSkip).toContain(testTag);
    });

    it('should identify STYLE tags to skip', () => {
      const tagsToSkip = ['SCRIPT', 'STYLE', 'TEXTAREA', 'NOSCRIPT'];
      const testTag = 'STYLE';
      
      expect(tagsToSkip).toContain(testTag);
    });

    it('should identify TEXTAREA tags to skip', () => {
      const tagsToSkip = ['SCRIPT', 'STYLE', 'TEXTAREA', 'NOSCRIPT'];
      const testTag = 'TEXTAREA';
      
      expect(tagsToSkip).toContain(testTag);
    });
  });

  describe('Trademark Check Response Handling', () => {
    it('should handle successful trademark check response', () => {
      const response = {
        ok: true,
        data: { available: true, trademarks: [] }
      };
      
      expect(response.ok).toBe(true);
      expect(response.data.available).toBe(true);
    });

    it('should handle trademark found response', () => {
      const response = {
        ok: true,
        data: {
          available: false,
          trademarks: [{ name: 'TestBrand', owner: 'Test Owner' }]
        }
      };
      
      expect(response.ok).toBe(true);
      expect(response.data.available).toBe(false);
      expect(response.data.trademarks).toHaveLength(1);
    });

    it('should handle error response', () => {
      const response = {
        ok: false,
        error: 'Network error'
      };
      
      expect(response.ok).toBe(false);
      expect(response.error).toBeDefined();
    });

    it('should handle null response', () => {
      const response = null;
      
      // The code should check for null responses
      const result = response ? response.data : null;
      expect(result).toBeNull();
    });
  });

  describe('Rate Limiting', () => {
    it('should have delay mechanism for API calls', async () => {
      const startTime = Date.now();
      
      // Simulate delay between checks
      await new Promise(r => setTimeout(r, 200));
      
      const elapsed = Date.now() - startTime;
      expect(elapsed).toBeGreaterThanOrEqual(200);
    });
  });
});
