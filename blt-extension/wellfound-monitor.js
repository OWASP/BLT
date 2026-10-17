// Function to monitor the Wellfound "Apply" button
function monitorWellfoundApplications() {
    const applyButton = document.querySelector('button[data-test="JobDescriptionSlideIn--SubmitButton"]');
    
    // console.log("🔍 Checking for apply button...");
    if (applyButton && !applyButton.dataset.listenerAdded) {
        applyButton.dataset.listenerAdded = "true"; // Prevent duplicate event listeners
        // console.log("✅ Apply button found! Adding event listener...");

        applyButton.addEventListener("click", () => {
            // console.log("🔍 Apply button clicked! Adding event listener...");
            const jobData = {
                company: document.querySelector('.text-sm.font-semibold.text-black')?.textContent.trim() || "Unknown Company",
                position: document.querySelector('.mt-4 h1.text-xl.font-semibold.text-black')?.textContent.trim() || "Unknown Position",
                jobUrl: window.location.href,
                platform: 'Wellfound',
                status: 'Applied',
                appliedDate: new Date().toISOString().split('T')[0]
            };
            
            // Store the application
            chrome.storage.local.get('jobApplications', function(result) {
                const applications = result.jobApplications || [];
                applications.push(jobData);
                chrome.storage.local.set({ 'jobApplications': applications });
            });
        });
    }
}

// Use MutationObserver to detect new elements being added dynamically
const observer = new MutationObserver(() => {
    monitorWellfoundApplications();
});

observer.observe(document.body, { childList: true, subtree: true }); 