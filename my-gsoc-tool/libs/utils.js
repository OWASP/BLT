import { IS_EDITABLE } from "./constants.js";

export function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

export function updateLastUpdated() {
    const lastUpdated = document.getElementById('last-updated');
    lastUpdated.textContent = new Date().toLocaleString();
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