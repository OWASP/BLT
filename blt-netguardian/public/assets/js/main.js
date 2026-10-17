/**
 * Main JavaScript for BLT-NetGuardian frontend
 */

document.addEventListener('DOMContentLoaded', function() {
    const scanForm = document.getElementById('scanForm');
    if (scanForm) {
        scanForm.addEventListener('submit', handleScanSubmit);
    }
});

async function handleScanSubmit(e) {
    e.preventDefault();
    
    const messageDiv = document.getElementById('message');
    const submitButton = e.target.querySelector('button[type="submit"]');
    
    // Hide previous message
    messageDiv.style.display = 'none';
    
    // Disable submit button
    submitButton.disabled = true;
    submitButton.textContent = '⏳ Processing...';
    
    const formData = {
        target_type: document.getElementById('targetType').value,
        target: document.getElementById('target').value,
        scan_types: Array.from(document.getElementById('scanTypes').selectedOptions)
            .map(opt => opt.value),
        notes: document.getElementById('notes').value,
        priority: 'medium'
    };
    
    try {
        // Step 1: Register the target
        showMessage(messageDiv, 'info', '📝 Registering target...');
        
        const registerData = await apiRequest(CONFIG.ENDPOINTS.REGISTER_TARGET, {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        if (!registerData.success) {
            throw new Error(registerData.message || 'Failed to register target');
        }
        
        // Step 2: Queue the tasks
        showMessage(messageDiv, 'info', '📋 Queueing scan tasks...');
        
        const queueData = await apiRequest(CONFIG.ENDPOINTS.QUEUE_TASKS, {
            method: 'POST',
            body: JSON.stringify({
                target_id: registerData.target_id,
                task_types: formData.scan_types,
                priority: formData.priority
            })
        });
        
        if (!queueData.success) {
            throw new Error(queueData.message || 'Failed to queue tasks');
        }
        
        // Success!
        showMessage(
            messageDiv, 
            'success', 
            `✅ Success! Job ID: ${queueData.job_id}. ${queueData.tasks_queued} tasks queued for scanning.`
        );
        
        // Store job ID for later reference
        localStorage.setItem('lastJobId', queueData.job_id);
        
        // Reset form
        document.getElementById('scanForm').reset();
        
        // Optionally redirect to dashboard after a delay
        setTimeout(() => {
            if (confirm('Scan started! Would you like to view the dashboard?')) {
                window.location.href = `dashboard.html?job_id=${queueData.job_id}`;
            }
        }, 2000);
        
    } catch (error) {
        console.error('Scan submission error:', error);
        showMessage(
            messageDiv, 
            'error', 
            `❌ Error: ${error.message}. Please check that the API is configured correctly.`
        );
    } finally {
        // Re-enable submit button
        submitButton.disabled = false;
        submitButton.textContent = '🚀 Start Security Scan';
    }
}

async function checkStatus() {
    const lastJobId = localStorage.getItem('lastJobId');
    const jobId = prompt('Enter Job ID:', lastJobId || '');
    
    if (!jobId) return;
    
    try {
        const data = await apiRequest(`${CONFIG.ENDPOINTS.JOB_STATUS}?job_id=${jobId}`);
        
        const statusMessage = [
            `Job ID: ${data.job_id}`,
            `Status: ${data.status}`,
            `Progress: ${data.progress}%`,
            `Completed: ${data.completed}/${data.total} tasks`,
            `Created: ${new Date(data.created_at).toLocaleString()}`
        ].join('\n');
        
        alert(statusMessage);
        
        // Update stored job ID
        localStorage.setItem('lastJobId', jobId);
        
    } catch (error) {
        alert(`Error checking status: ${error.message}`);
    }
}

function showMessage(element, type, message) {
    element.className = `message ${type}`;
    element.textContent = message;
    element.style.display = 'block';
}

// Export functions for use in other pages
window.checkStatus = checkStatus;
window.showMessage = showMessage;
