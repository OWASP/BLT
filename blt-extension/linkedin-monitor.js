// Function to monitor the "Review" button
function monitorLinkedInApplications() {
    // console.log("Monitoring LinkedIn job applications...");
    const applyButton = document.querySelector('button[aria-label="Submit application"]');
    
    if (applyButton && !applyButton.dataset.listenerAdded) {
        // console.log("✅ Apply button found! Adding event listener...");

        applyButton.dataset.listenerAdded = "true"; // Prevent duplicate event listeners

        applyButton.addEventListener("click", () => {
            // alert("Apply button clicked! ✅");
            const jobData = {
                company: document.querySelector('a[data-view-name="job-details-about-company-name-link"]')?.textContent.trim() || "Unknown Company",
                position: document.querySelector('.job-details-jobs-unified-top-card__job-title h1 a')?.textContent.trim() || "Unknown Position",
                jobUrl: window.location.href,
                platform: 'LinkedIn',
                status: 'Applied',
                appliedDate: new Date().toISOString().split('T')[0]
            };
            // can you pleasse print the jobData to the console
            // console.log(jobData);
            
            // Store the application
            chrome.storage.local.get('jobApplications', function(result) {
                const applications = result.jobApplications || [];
                applications.push(jobData);
                chrome.storage.local.set({ 'jobApplications': applications });
            });
        });
    }
}
// 👀 Use MutationObserver to detect new elements being added dynamically
const observer = new MutationObserver(() => {
    monitorLinkedInApplications();
});

observer.observe(document.body, { childList: true, subtree: true });
