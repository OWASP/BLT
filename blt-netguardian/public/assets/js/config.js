/**
 * Configuration for BLT-NetGuardian
 */

const CONFIG = {
    // Frontend and API are served from the same Cloudflare Worker, so use the
    // current page origin. For local development with `wrangler dev` this will
    // automatically resolve to http://localhost:8787.
    API_BASE_URL: (typeof window !== 'undefined' ? window.location.origin : ''),
    
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
