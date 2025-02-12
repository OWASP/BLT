document.getElementById('screenshotBtn').addEventListener('click', () => {
    // Send message to background script to trigger screenshot
    chrome.runtime.sendMessage({ action: 'takeScreenshot' });
    window.close(); // Close the popup
});

document.getElementById('jobTrackingBtn').addEventListener('click', () => {
    chrome.tabs.create({ url: chrome.runtime.getURL('jobtracking.html') });
    window.close();
}); 