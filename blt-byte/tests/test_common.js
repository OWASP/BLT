// tests/test_common.js
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';

const commonJsCode = fs.readFileSync(path.resolve(__dirname, '../public/static/common.js'), 'utf8');

describe('BLT Common JS Utilities', () => {
  let dom;
  let window;

  beforeEach(() => {
    // Setup a fresh JSDOM for each test
    dom = new JSDOM('<!DOCTYPE html><html><head></head><body><button id="dark-toggle"></button></body></html>', {
      url: 'http://localhost',
      runScripts: 'dangerously',
      resources: 'usable'
    });
    window = dom.window;
    global.window = window;
    global.document = window.document;
    global.localStorage = window.localStorage;
    global.navigator = window.navigator;

    // Execute the common.js code in the JSDOM context
    const scriptEl = window.document.createElement('script');
    scriptEl.textContent = commonJsCode;
    window.document.head.appendChild(scriptEl);
  });

  describe('escHtml', () => {
    it('should escape HTML special characters', () => {
      const input = '<script>alert("xss")</script> & "quotes"';
      const expected = '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt; &amp; &quot;quotes&quot;';
      expect(window.BLT.escHtml(input)).toBe(expected);
    });

    it('should return empty string for null/undefined', () => {
      expect(window.BLT.escHtml(null)).toBe('');
      expect(window.BLT.escHtml(undefined)).toBe('');
    });
  });

  describe('sanitize', () => {
    it('should return original HTML if DOMPurify is missing', () => {
      const dirty = '<img src=x onerror=alert(1)>';
      expect(window.BLT.sanitize(dirty)).toBe(dirty);
    });

    it('should use DOMPurify if available', () => {
      // Mock DOMPurify
      window.DOMPurify = {
        sanitize: vi.fn().mockReturnValue('<span>safe</span>')
      };
      const result = window.BLT.sanitize('<script>bad</script>');
      expect(window.DOMPurify.sanitize).toHaveBeenCalled();
      expect(result).toBe('<span>safe</span>');
    });
  });

  describe('Theme Toggle', () => {
    it('should toggle "dark" class on documentElement', () => {
      const btn = window.document.getElementById('dark-toggle');
      window.BLT.initThemeToggle('dark-toggle');
      
      // Initial state (assuming light)
      expect(window.document.documentElement.classList.contains('dark')).toBe(false);
      
      // Toggle to dark
      btn.click();
      expect(window.document.documentElement.classList.contains('dark')).toBe(true);
      expect(window.localStorage.getItem('blt-theme')).toBe('dark');
      
      // Toggle back to light
      btn.click();
      expect(window.document.documentElement.classList.contains('dark')).toBe(false);
      expect(window.localStorage.getItem('blt-theme')).toBe('light');
    });
  });
});
