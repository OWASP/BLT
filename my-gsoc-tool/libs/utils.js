import { IS_EDITABLE } from "./constants.js";

// Format date helper
export function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// Update last updated timestamp
export function updateLastUpdated() {
    const lastUpdated = document.getElementById('last-updated');
    lastUpdated.textContent = new Date().toLocaleString();
}

export function renderEditableButtonSection() {
    if (IS_EDITABLE) {
        const editSection = document.getElementById('editabe-button-section');
        editSection.innerHTML = `
            <button id="save-button" href="config.json" target="_blank" class="btn-primary fixed top-[90%] cursor-pointer right-60 z-50 flex items-center gap-2">
                <i class="fas fa-edit"></i> Save changes
            </button>
        `;
    }
}

export const showAlert = (response, message) => {
    if (response.success) {
        alert(`SUCCESS: ${message}`);
        return;
    } else {
        alert(`Something went wrong, Please try again !`);
        return;
    }
}