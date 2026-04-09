/**
 * Custom Modal Utility for BLT Jobs
 */
const Modal = (function() {
    let overlay = null;
    let focusableElements = [];
    let firstFocusableElement = null;
    let lastFocusableElement = null;
    let onConfirmCallback = null;
    let onCancelCallback = null;

    function createModal() {
        if (overlay) return;

        overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.setAttribute('aria-hidden', 'true');
        overlay.id = 'custom-confirm-modal';

        overlay.innerHTML = `
            <div class="modal-container" role="dialog" aria-modal="true" aria-labelledby="modal-title">
                <div class="modal-header">
                    <h2 id="modal-title" class="modal-title">Confirm Action</h2>
                    <button id="modal-close-btn" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition" aria-label="Close modal">
                        <i class="fas fa-times text-xl"></i>
                    </button>
                </div>
                <div id="modal-message" class="modal-body">
                    Are you sure you want to proceed?
                </div>
                <div class="modal-footer">
                    <button id="modal-cancel-btn" class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">
                        Cancel
                    </button>
                    <button id="modal-confirm-btn" class="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 shadow-sm focus:ring-2 focus:ring-red-500 focus:ring-offset-2">
                        Confirm
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Event Listeners
        overlay.querySelector('#modal-close-btn').addEventListener('click', hide);
        overlay.querySelector('#modal-cancel-btn').addEventListener('click', handleCancel);
        overlay.querySelector('#modal-confirm-btn').addEventListener('click', handleConfirm);
        
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) hide();
        });

        window.addEventListener('keydown', handleKeyDown);
    }

    function handleKeyDown(e) {
        if (!overlay || !overlay.classList.contains('active')) return;

        if (e.key === 'Escape') {
            hide();
        }

        if (e.key === 'Tab') {
            if (e.shiftKey) {
                if (document.activeElement === firstFocusableElement) {
                    lastFocusableElement.focus();
                    e.preventDefault();
                }
            } else {
                if (document.activeElement === lastFocusableElement) {
                    firstFocusableElement.focus();
                    e.preventDefault();
                }
            }
        }
    }

    function handleConfirm() {
        if (onConfirmCallback) onConfirmCallback();
        hide();
    }

    function handleCancel() {
        if (onCancelCallback) onCancelCallback();
        hide();
    }

    function show(options = {}) {
        createModal();
        
        const titleEl = overlay.querySelector('#modal-title');
        const messageEl = overlay.querySelector('#modal-message');
        const confirmBtn = overlay.querySelector('#modal-confirm-btn');
        const cancelBtn = overlay.querySelector('#modal-cancel-btn');

        titleEl.textContent = options.title || 'Confirm Action';
        messageEl.textContent = options.message || 'Are you sure you want to proceed?';
        confirmBtn.textContent = options.confirmText || 'Confirm';
        cancelBtn.textContent = options.cancelText || 'Cancel';
        
        onConfirmCallback = options.onConfirm || null;
        onCancelCallback = options.onCancel || null;

        overlay.classList.add('active');
        overlay.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';

        // Accessibility: Trap focus
        focusableElements = Array.from(overlay.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'));
        firstFocusableElement = focusableElements[0];
        lastFocusableElement = focusableElements[focusableElements.length - 1];
        
        // Focus the confirm button by default for destructive actions, or first element
        setTimeout(() => {
            if (confirmBtn) confirmBtn.focus();
            else if (firstFocusableElement) firstFocusableElement.focus();
        }, 100);
    }

    function hide() {
        if (!overlay) return;
        overlay.classList.remove('active');
        overlay.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    return {
        confirm: show,
        hide: hide
    };
})();

// Export to window
window.BLTModal = Modal;
