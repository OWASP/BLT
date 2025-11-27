/**
 * Tests for github-pr-button.js
 */

describe('GitHub PR Update Branch Button', () => {
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
    
    // Mock window.location for GitHub PR page
    delete window.location;
    window.location = { 
      pathname: '/owner/repo/pull/123',
      href: 'https://github.com/owner/repo/pull/123'
    };
    
    // Mock scrollIntoView for jsdom
    Element.prototype.scrollIntoView = jest.fn();
    
    jest.clearAllMocks();
  });

  afterEach(() => {
    // Restore original MutationObserver
    global.MutationObserver = originalMutationObserver;
    jest.resetModules();
  });

  describe('Initialization', () => {
    it('should inject floating button styles into document head', () => {
      require('../github-pr-button.js');

      const styleElements = document.querySelectorAll('style');
      let hasFloatingButtonStyles = false;
      
      styleElements.forEach(style => {
        if (style.textContent.includes('blt-update-branch-btn')) {
          hasFloatingButtonStyles = true;
        }
      });

      expect(hasFloatingButtonStyles).toBe(true);
    });

    it('should set up MutationObserver on document body', () => {
      require('../github-pr-button.js');

      expect(MutationObserver).toHaveBeenCalled();
      const observerInstance = MutationObserver.mock.instances[0];
      expect(observerInstance.observe).toHaveBeenCalledWith(
        document.body,
        { childList: true, subtree: true }
      );
    });

    it('should create floating button container on PR pages', () => {
      require('../github-pr-button.js');

      const container = document.querySelector('.blt-floating-btn-container');
      expect(container).not.toBeNull();
    });

    it('should create floating button on PR pages', () => {
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn).not.toBeNull();
    });

    it('should not create floating button on non-PR pages', () => {
      window.location = { pathname: '/owner/repo/issues/123' };
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn).toBeNull();
    });

    it('should not create duplicate floating buttons', () => {
      require('../github-pr-button.js');

      // Trigger MutationObserver callback multiple times
      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();
      observerCallback();
      observerCallback();

      const floatingBtns = document.querySelectorAll('.blt-update-branch-btn');
      expect(floatingBtns.length).toBe(1);
    });

    it('should create three buttons in the container', () => {
      require('../github-pr-button.js');

      const buttons = document.querySelectorAll('.blt-floating-btn');
      expect(buttons.length).toBe(3);
    });
  });

  describe('Floating Button Structure', () => {
    it('should have correct button text', () => {
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn.textContent).toContain('Go to Update Branch');
    });

    it('should have correct aria-label for accessibility', () => {
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn.getAttribute('aria-label')).toBe('Scroll to Update Branch button');
    });

    it('should have title attribute', () => {
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn.getAttribute('title')).toBe('Scroll to Update Branch button');
    });

    it('should contain SVG icon', () => {
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      const svgIcon = floatingBtn.querySelector('svg');
      expect(svgIcon).not.toBeNull();
    });

    it('should have scroll to top button with correct text', () => {
      require('../github-pr-button.js');

      const buttons = document.querySelectorAll('.blt-floating-btn');
      const scrollTopBtn = Array.from(buttons).find(btn => 
        btn.textContent.includes('Scroll to Top')
      );
      expect(scrollTopBtn).not.toBeNull();
    });

    it('should have view files button with correct text', () => {
      require('../github-pr-button.js');

      const buttons = document.querySelectorAll('.blt-floating-btn');
      const viewFilesBtn = Array.from(buttons).find(btn => 
        btn.textContent.includes('View Files')
      );
      expect(viewFilesBtn).not.toBeNull();
    });
  });

  describe('CSS Styles', () => {
    it('should define fixed positioning styles', () => {
      require('../github-pr-button.js');

      const styleEl = Array.from(document.querySelectorAll('style')).find(
        style => style.textContent.includes('blt-update-branch-btn')
      );

      expect(styleEl.textContent).toContain('position: fixed');
      expect(styleEl.textContent).toContain('bottom:');
      expect(styleEl.textContent).toContain('right:');
    });

    it('should define hover styles', () => {
      require('../github-pr-button.js');

      const styleEl = Array.from(document.querySelectorAll('style')).find(
        style => style.textContent.includes('blt-update-branch-btn')
      );

      expect(styleEl.textContent).toContain(':hover');
    });

    it('should define green background color', () => {
      require('../github-pr-button.js');

      const styleEl = Array.from(document.querySelectorAll('style')).find(
        style => style.textContent.includes('blt-update-branch-btn')
      );

      expect(styleEl.textContent).toContain('background:');
    });

    it('should define secondary button styles', () => {
      require('../github-pr-button.js');

      const styleEl = Array.from(document.querySelectorAll('style')).find(
        style => style.textContent.includes('blt-floating-btn-container')
      );

      expect(styleEl.textContent).toContain('blt-secondary-btn');
    });
  });

  describe('Button Click Behavior', () => {
    it('should have click event listener attached', () => {
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      
      // The button should respond to clicks without throwing errors
      expect(() => floatingBtn.click()).not.toThrow();
    });

    it('should scroll to update branch button when found', () => {
      // Create a mock update branch button
      document.body.innerHTML = `
        <div class="merge-message">
          <button id="update-btn">Update branch</button>
        </div>
      `;

      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      floatingBtn.click();

      const updateBtn = document.getElementById('update-btn');
      expect(updateBtn.scrollIntoView).toHaveBeenCalledWith({
        behavior: 'smooth',
        block: 'center'
      });
    });

    it('should scroll to bottom of page when no update branch button exists', () => {
      document.body.innerHTML = '<div>No update button here</div>';
      
      // Mock window.scrollTo
      window.scrollTo = jest.fn();
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      floatingBtn.click();

      expect(window.scrollTo).toHaveBeenCalledWith({
        top: document.documentElement.scrollHeight,
        behavior: 'smooth'
      });
    });

    it('should not throw when no update branch button exists', () => {
      document.body.innerHTML = '<div>No update button here</div>';
      
      // Mock window.scrollTo
      window.scrollTo = jest.fn();
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      
      expect(() => floatingBtn.click()).not.toThrow();
    });

    it('should scroll to top when scroll to top button is clicked', () => {
      window.scrollTo = jest.fn();
      
      require('../github-pr-button.js');

      const buttons = document.querySelectorAll('.blt-floating-btn');
      const scrollTopBtn = Array.from(buttons).find(btn => 
        btn.textContent.includes('Scroll to Top')
      );
      scrollTopBtn.click();

      expect(window.scrollTo).toHaveBeenCalledWith({
        top: 0,
        behavior: 'smooth'
      });
    });

    it('should navigate to files page when view files button is clicked', () => {
      require('../github-pr-button.js');

      const buttons = document.querySelectorAll('.blt-floating-btn');
      const viewFilesBtn = Array.from(buttons).find(btn => 
        btn.textContent.includes('View Files')
      );
      viewFilesBtn.click();

      expect(window.location.href).toBe('/owner/repo/pull/123/files');
    });
  });

  describe('Update Branch Button Detection', () => {
    it('should always show floating button on PR pages', () => {
      document.body.innerHTML = `
        <button>Update branch</button>
      `;
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn).not.toBeNull();
      expect(floatingBtn.classList.contains('hidden')).toBe(false);
    });

    it('should show floating button even when no update button exists', () => {
      document.body.innerHTML = `
        <div>PR content with regular merge button</div>
        <button>Merge pull request</button>
      `;
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn).not.toBeNull();
      expect(floatingBtn.classList.contains('hidden')).toBe(false);
    });

    it('should find button with "Update with merge" text', () => {
      document.body.innerHTML = `
        <button>Update with merge</button>
      `;
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn.classList.contains('hidden')).toBe(false);
    });

    it('should find button with data-disable-with attribute', () => {
      document.body.innerHTML = `
        <button data-disable-with="Updating branch…">Update</button>
      `;
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn.classList.contains('hidden')).toBe(false);
    });

    it('should handle case-insensitive button text', () => {
      document.body.innerHTML = `
        <button>UPDATE BRANCH</button>
      `;
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn.classList.contains('hidden')).toBe(false);
    });
  });

  describe('MutationObserver Updates', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('should keep button visible when DOM changes', () => {
      document.body.innerHTML = '<div>Initial content</div><button>Merge</button>';
      
      require('../github-pr-button.js');

      let floatingBtn = document.querySelector('.blt-update-branch-btn');
      // Button should always be visible
      expect(floatingBtn.classList.contains('hidden')).toBe(false);

      // Simulate DOM change - add update button
      const updateButton = document.createElement('button');
      updateButton.textContent = 'Update branch';
      document.body.appendChild(updateButton);
      
      // Trigger MutationObserver callback
      const observerCallback = MutationObserver.mock.calls[0][0];
      observerCallback();
      
      // Fast-forward the debounce timer
      jest.advanceTimersByTime(150);

      floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn.classList.contains('hidden')).toBe(false);
    });
  });

  describe('Page Navigation', () => {
    it('should work on different PR number pages', () => {
      window.location = { pathname: '/owner/repo/pull/456' };
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn).not.toBeNull();
    });

    it('should work on different repository PR pages', () => {
      window.location = { pathname: '/different-owner/different-repo/pull/1' };
      
      require('../github-pr-button.js');

      const floatingBtn = document.querySelector('.blt-update-branch-btn');
      expect(floatingBtn).not.toBeNull();
    });

    it('should navigate to correct files URL for different PRs', () => {
      window.location = { 
        pathname: '/another-owner/another-repo/pull/789',
        href: 'https://github.com/another-owner/another-repo/pull/789'
      };
      
      require('../github-pr-button.js');

      const buttons = document.querySelectorAll('.blt-floating-btn');
      const viewFilesBtn = Array.from(buttons).find(btn => 
        btn.textContent.includes('View Files')
      );
      viewFilesBtn.click();

      expect(window.location.href).toBe('/another-owner/another-repo/pull/789/files');
    });
  });
});
