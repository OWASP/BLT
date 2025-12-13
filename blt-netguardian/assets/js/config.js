/**
 * Configuration for BLT-NetGuardian
 * Update API_BASE_URL with your deployed Cloudflare Worker URL
 */

const CONFIG = {
    // IMPORTANT: Change this to your deployed Cloudflare Worker URL
    // After deploying with 'wrangler publish', update this with your actual URL
    API_BASE_URL: 'https://blt-netguardian.your-subdomain.workers.dev',  // TODO: Update this!
    
    // For local development with wrangler dev
    // API_BASE_URL: 'http://localhost:8787',
    
    // API endpoints
    ENDPOINTS: {
        QUEUE_TASKS: '/api/tasks/queue',
        REGISTER_TARGET: '/api/targets/register',
        INGEST_RESULTS: '/api/results/ingest',
        JOB_STATUS: '/api/jobs/status',
        LIST_TASKS: '/api/tasks/list',
        VULNERABILITIES: '/api/vulnerabilities'
    },
    
    // Request timeout (ms)
    REQUEST_TIMEOUT: 30000
};

// Helper function to build full API URL
function buildApiUrl(endpoint) {
    return CONFIG.API_BASE_URL + endpoint;
}

// Helper function to make API requests with error handling
async function apiRequest(endpoint, options = {}) {
    const url = buildApiUrl(endpoint);
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);
        
        const response = await fetch(url, {
            ...finalOptions,
            signal: controller.signal
        });
        
        clearTimeout(timeout);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({
                error: 'Request failed',
                message: `HTTP ${response.status}: ${response.statusText}`
            }));
            throw new Error(errorData.message || errorData.error || 'Request failed');
        }
        
        return await response.json();
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('Request timeout - please try again');
        }
        throw error;
    }
}
