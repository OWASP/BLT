// Interactive Score Calculator for BLT-Leaf "How It Works" Page

function calculateScore() {
    // Get input values
    const ciPassed = parseInt(document.getElementById('ciPassed').value);
    const ciFailed = parseInt(document.getElementById('ciFailed').value);
    const approvals = parseInt(document.getElementById('approvals').value);
    const changesRequested = parseInt(document.getElementById('changesRequested').value);
    const conversations = parseInt(document.getElementById('conversations').value);
    const responseRate = parseInt(document.getElementById('responseRate').value);

    // Update displayed values
    document.getElementById('ciPassedValue').textContent = ciPassed;
    document.getElementById('ciFailedValue').textContent = ciFailed;
    document.getElementById('approvalsValue').textContent = approvals;
    document.getElementById('changesRequestedValue').textContent = changesRequested;
    document.getElementById('conversationsValue').textContent = conversations;
    document.getElementById('responseRateValue').textContent = responseRate + '%';

    // Calculate CI Score
    const totalChecks = ciPassed + ciFailed;
    let ciScore = 0;
    let ciConfidence = 'Low';
    let ciConfidenceBadge = 'badge-low';

    if (totalChecks > 0) {
        ciScore = (ciPassed / totalChecks) * 100;
        ciConfidence = 'High';
        ciConfidenceBadge = 'badge-high';
    } else {
        // No checks run - low confidence, assume failure
        ciScore = 0;
        ciConfidence = 'Low';
        ciConfidenceBadge = 'badge-low';
    }

    // Calculate Review Score
    let reviewScore = 0;
    let reviewConfidence = 'Medium';
    let reviewConfidenceBadge = 'badge-medium';

    if (approvals > 0 && changesRequested === 0) {
        reviewScore = 100;
        reviewConfidence = 'High';
        reviewConfidenceBadge = 'badge-high';
    } else if (approvals > 0 && changesRequested > 0) {
        reviewScore = 50;
        reviewConfidence = 'Medium';
        reviewConfidenceBadge = 'badge-medium';
    } else if (approvals === 0 && changesRequested > 0) {
        reviewScore = 0;
        reviewConfidence = 'High';
        reviewConfidenceBadge = 'badge-high';
    } else {
        // No approvals, no changes requested
        reviewScore = 0;
        reviewConfidence = 'Medium';
        reviewConfidenceBadge = 'badge-medium';
    }

    // Response Score (direct mapping)
    const responseScore = responseRate;
    let responseConfidence = 'High';
    let responseConfidenceBadge = 'badge-high';

    if (responseRate < 50) {
        responseConfidence = 'Low';
        responseConfidenceBadge = 'badge-low';
    } else if (responseRate < 80) {
        responseConfidence = 'Medium';
        responseConfidenceBadge = 'badge-medium';
    }

    // Calculate Overall Score
    // Formula: (CI × 0.4) + (Review × 0.4) + (Response × 0.2) - (3 × conversations)
    let overallScore = (ciScore * 0.4) + (reviewScore * 0.4) + (responseScore * 0.2);

    // Deduct 3 points per unresolved conversation
    overallScore = Math.max(0, overallScore - (conversations * 3));

    // Determine overall status
    let overallStatus = '';
    let overallColor = '';

    if (overallScore >= 80) {
        overallStatus = '✅ Merge Ready';
        overallColor = 'text-green-600 dark:text-green-400';
    } else if (overallScore >= 60) {
        overallStatus = '⚠️ Needs Attention';
        overallColor = 'text-yellow-600 dark:text-yellow-400';
    } else {
        overallStatus = '❌ Not Ready';
        overallColor = 'text-red-600 dark:text-red-400';
    }

    // Update UI
    const overallScoreElement = document.getElementById('overallScore');
    overallScoreElement.textContent = Math.round(overallScore) + '%';
    overallScoreElement.className = overallColor + ' text-5xl font-bold mb-2';

    document.getElementById('overallStatus').textContent = overallStatus;

    document.getElementById('ciScoreDisplay').innerHTML =
        `${Math.round(ciScore)}% <span class="${ciConfidenceBadge} px-2 py-0.5 rounded text-xs ml-1">${ciConfidence}</span>`;

    document.getElementById('reviewScoreDisplay').innerHTML =
        `${Math.round(reviewScore)}% <span class="${reviewConfidenceBadge} px-2 py-0.5 rounded text-xs ml-1">${reviewConfidence}</span>`;

    document.getElementById('responseScoreDisplay').innerHTML =
        `${Math.round(responseScore)}% <span class="${responseConfidenceBadge} px-2 py-0.5 rounded text-xs ml-1">${responseConfidence}</span>`;
}

// Initialize calculator on page load
document.addEventListener('DOMContentLoaded', function () {
    // Attach event listeners to all range inputs
    const rangeInputs = document.querySelectorAll('input[type="range"]');
    rangeInputs.forEach(input => {
        input.addEventListener('input', calculateScore);
    });

    // Initial calculation
    calculateScore();
});
