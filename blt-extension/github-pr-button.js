// GitHub PR Update Branch Floating Button
// Adds floating buttons on GitHub PR pages for navigation

// CSS styles for the floating buttons
const floatingButtonStyle = document.createElement("style");
floatingButtonStyle.textContent = `
.blt-floating-btn-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.blt-floating-btn {
  background: #238636;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.2s ease, transform 0.2s ease;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
}

.blt-floating-btn:hover {
  background: #2ea043;
  transform: translateY(-2px);
}

.blt-floating-btn:active {
  transform: translateY(0);
}

.blt-floating-btn svg {
  width: 16px;
  height: 16px;
  fill: currentColor;
}

.blt-floating-btn.blt-secondary-btn {
  background: #0969da;
}

.blt-floating-btn.blt-secondary-btn:hover {
  background: #0860ca;
}

/* Keep backwards compatibility with old class name */
.blt-update-branch-btn {
  background: #238636;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.2s ease, transform 0.2s ease;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
}

.blt-update-branch-btn:hover {
  background: #2ea043;
  transform: translateY(-2px);
}

.blt-update-branch-btn:active {
  transform: translateY(0);
}

.blt-update-branch-btn svg {
  width: 16px;
  height: 16px;
  fill: currentColor;
}
`;
document.head.appendChild(floatingButtonStyle);

// SVG icon for the button (down arrow icon)
const downArrowIcon = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
  <path fill-rule="evenodd" d="M8 12.78l-4.22-4.22a.75.75 0 011.06-1.06L8 10.69l3.16-3.19a.75.75 0 111.06 1.06L8 12.78zM8 3.75a.75.75 0 01.75.75v4.69a.75.75 0 01-1.5 0V4.5A.75.75 0 018 3.75z"/>
</svg>
`;

// SVG icon for scroll to top (up arrow icon)
const upArrowIcon = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
  <path fill-rule="evenodd" d="M8 3.22l4.22 4.22a.75.75 0 01-1.06 1.06L8 5.31 4.84 8.5a.75.75 0 01-1.06-1.06L8 3.22zM8 12.25a.75.75 0 01-.75-.75V6.81a.75.75 0 011.5 0v4.69a.75.75 0 01-.75.75z"/>
</svg>
`;

// SVG icon for files page (file icon)
const filesIcon = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
  <path fill-rule="evenodd" d="M3.75 1.5a.25.25 0 00-.25.25v11.5c0 .138.112.25.25.25h8.5a.25.25 0 00.25-.25V6H9.75A1.75 1.75 0 018 4.25V1.5H3.75zm5.75.56v2.19c0 .138.112.25.25.25h2.19L9.5 2.06zM2 1.75C2 .784 2.784 0 3.75 0h5.086c.464 0 .909.184 1.237.513l3.414 3.414c.329.328.513.773.513 1.237v8.086A1.75 1.75 0 0112.25 15h-8.5A1.75 1.75 0 012 13.25V1.75z"/>
</svg>
`;

let floatingButtonContainer = null;
let floatingButton = null;

/**
 * Finds the "Update branch" button on GitHub PR pages
 * The button can appear in different forms:
 * 1. "Update branch" button text
 * 2. "Update with merge" or "Update with rebase" in dropdown
 * @returns {Element|null} The update branch button element or null if not found
 */
function findUpdateBranchButton() {
    // Look for the update branch button in the PR merge box section
    // GitHub uses different variations of this button
    const selectors = [
        // Primary update branch button
        'button[data-disable-with="Updating branch\u2026"]',
        // Form-based update buttons
        'form[action*="update_branch"] button',
        '.branch-action-btn',
        // Text-based search for buttons containing "Update branch"
        '.merge-status-list button',
        '.merging-body button'
    ];

    for (const selector of selectors) {
        try {
            const elements = document.querySelectorAll(selector);
            for (const el of elements) {
                // Skip our own floating button
                if (el.classList.contains('blt-update-branch-btn')) {
                    continue;
                }
                if (el && el.textContent && el.textContent.toLowerCase().includes('update')) {
                    return el;
                }
            }
        } catch (e) {
            // Some selectors may not be valid, continue to next
        }
    }

    // Fallback: search all buttons for "Update branch" text
    const allButtons = document.querySelectorAll('button, .btn');
    for (const btn of allButtons) {
        // Skip our own floating button
        if (btn.classList.contains('blt-update-branch-btn')) {
            continue;
        }
        const text = btn.textContent?.trim().toLowerCase() || '';
        if (text.includes('update branch') || text.includes('update with')) {
            return btn;
        }
    }

    // Also check for the merge box area which contains the update branch section
    const mergeBox = document.querySelector('.merge-message, .merging-body, [data-target="merge-message"]');
    if (mergeBox) {
        const buttons = mergeBox.querySelectorAll('button');
        for (const updateBtn of buttons) {
            const btnText = updateBtn.textContent?.trim().toLowerCase() || '';
            // More specific matching: require "update" followed by "branch" or "with"
            if (btnText.includes('update branch') || btnText.includes('update with')) {
                return updateBtn;
            }
        }
    }

    return null;
}

/**
 * Creates a floating button element
 * @param {string} icon - SVG icon HTML
 * @param {string} text - Button text
 * @param {string} title - Button title/tooltip
 * @param {Function} clickHandler - Click event handler
 * @param {boolean} isSecondary - Whether to use secondary styling
 * @returns {HTMLButtonElement} The floating button element
 */
function createButton(icon, text, title, clickHandler, isSecondary = false) {
    const button = document.createElement('button');
    button.className = `blt-floating-btn${isSecondary ? ' blt-secondary-btn' : ''}`;
    button.innerHTML = `${icon}<span>${text}</span>`;
    button.title = title;
    button.setAttribute('aria-label', title);
    
    button.addEventListener('click', clickHandler);
    
    return button;
}

/**
 * Creates the floating button container with all buttons
 * @returns {HTMLDivElement} The floating button container element
 */
function createFloatingButtonContainer() {
    const container = document.createElement('div');
    container.className = 'blt-floating-btn-container';
    
    // Create scroll to top button
    const scrollTopBtn = createButton(
        upArrowIcon,
        'Scroll to Top',
        'Scroll to top of page',
        scrollToTop,
        true
    );
    
    // Create view files button
    const viewFilesBtn = createButton(
        filesIcon,
        'View Files',
        'View changed files',
        navigateToFiles,
        true
    );
    
    // Create scroll to update branch button (primary)
    const updateBranchBtn = createButton(
        downArrowIcon,
        'Go to Update Branch',
        'Scroll to Update Branch button',
        scrollToUpdateBranch,
        false
    );
    // Add backwards-compatible class name
    updateBranchBtn.classList.add('blt-update-branch-btn');
    
    container.appendChild(scrollTopBtn);
    container.appendChild(viewFilesBtn);
    container.appendChild(updateBranchBtn);
    
    return container;
}

/**
 * Creates the floating button element (backwards compatibility)
 * @returns {HTMLButtonElement} The floating button element
 */
function createFloatingButton() {
    const button = document.createElement('button');
    button.className = 'blt-update-branch-btn';
    button.innerHTML = `${downArrowIcon}<span>Go to Update Branch</span>`;
    button.title = 'Scroll to Update Branch button';
    button.setAttribute('aria-label', 'Scroll to Update Branch button');
    
    button.addEventListener('click', scrollToUpdateBranch);
    
    return button;
}

/**
 * Scrolls to the top of the page
 */
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

/**
 * Navigates to the files changed tab of the PR
 */
function navigateToFiles() {
    // Get the current PR URL and navigate to /files
    const currentPath = window.location.pathname;
    const prMatch = currentPath.match(/(.+\/pull\/\d+)/);
    if (prMatch) {
        const prBasePath = prMatch[1];
        window.location.href = `${prBasePath}/files`;
    }
}

/**
 * Scrolls to the update branch button and highlights it.
 * If the update branch button is not found, scrolls to the bottom of the page.
 */
function scrollToUpdateBranch() {
    const updateBtn = findUpdateBranchButton();
    
    if (updateBtn) {
        // Scroll the button into view with smooth animation
        updateBtn.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
        
        // Add a brief highlight effect
        const originalOutline = updateBtn.style.outline;
        const originalBoxShadow = updateBtn.style.boxShadow;
        
        updateBtn.style.outline = '3px solid #58a6ff';
        updateBtn.style.boxShadow = '0 0 10px rgba(88, 166, 255, 0.5)';
        
        setTimeout(() => {
            updateBtn.style.outline = originalOutline;
            updateBtn.style.boxShadow = originalBoxShadow;
        }, 2000);
    } else {
        // If update branch button is not found, scroll to the bottom of the page
        window.scrollTo({
            top: document.documentElement.scrollHeight,
            behavior: 'smooth'
        });
    }
}

/**
 * Initializes the floating button on GitHub PR pages
 */
function initFloatingButton() {
    // Only run on GitHub PR pages
    if (!window.location.pathname.includes('/pull/')) {
        return;
    }
    
    // Don't create duplicate buttons
    if (floatingButtonContainer || document.querySelector('.blt-floating-btn-container')) {
        return;
    }
    
    // Create and add the floating button container (always visible on PR pages)
    floatingButtonContainer = createFloatingButtonContainer();
    document.body.appendChild(floatingButtonContainer);
    
    // Set floatingButton reference for backwards compatibility
    floatingButton = floatingButtonContainer.querySelector('.blt-update-branch-btn');
}

// Debounce timer for MutationObserver callbacks
let debounceTimer = null;

/**
 * Debounced handler for MutationObserver to ensure button is initialized
 */
function handleMutations() {
    if (debounceTimer) {
        clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
        // Initialize button if not already done
        if (!floatingButtonContainer) {
            initFloatingButton();
        }
    }, 100);
}

// Use MutationObserver to detect when the update branch button appears
// GitHub uses dynamic content loading
const observer = new MutationObserver(handleMutations);

// Start observing the document body for changes
observer.observe(document.body, { childList: true, subtree: true });

// Also initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFloatingButton);
} else {
    initFloatingButton();
}
