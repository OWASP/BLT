// GitHub PR Update Branch Floating Button
// Adds a floating button on GitHub PR pages that scrolls to the "Update branch" button

// CSS styles for the floating button
const floatingButtonStyle = document.createElement("style");
floatingButtonStyle.textContent = `
.blt-update-branch-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
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
 * Creates the floating button element
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
    if (floatingButton || document.querySelector('.blt-update-branch-btn')) {
        return;
    }
    
    // Create and add the floating button (always visible on PR pages)
    floatingButton = createFloatingButton();
    document.body.appendChild(floatingButton);
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
        if (!floatingButton) {
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
