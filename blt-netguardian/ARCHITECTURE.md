# BLT-NetGuardian Architecture

## Overview

BLT-NetGuardian implements a modern, scalable security scanning pipeline using a split architecture that separates the frontend from the backend.

## Architecture Components

### Frontend (GitHub Pages)

**Technology Stack**: Static HTML, CSS, JavaScript

**Location**: `https://owasp-blt.github.io/BLT-NetGuardian/`

**Files**:
- `index.html` - Main scan submission interface
- `dashboard.html` - Job monitoring dashboard
- `vulnerabilities.html` - Vulnerability database viewer
- `assets/css/style.css` - Responsive styling
- `assets/js/config.js` - API configuration
- `assets/js/main.js` - Main page logic
- `assets/js/dashboard.js` - Dashboard logic
- `assets/js/vulnerabilities.js` - Vulnerabilities page logic

**Features**:
- Beautiful gradient UI with modern design
- Responsive layout for mobile and desktop
- Real-time job status monitoring
- Vulnerability filtering and viewing
- Client-side API communication

### Backend (Cloudflare Workers)

**Technology Stack**: Python on Cloudflare Workers Runtime

**Location**: Cloudflare Workers (user-deployed)

**Files**:
- `src/worker.py` - Main API worker
- `src/models/` - Data models (Task, Target, Result, Vulnerability)
- `src/scanners/` - Scanner modules
- `src/utils/` - Utility functions (deduplication, storage)

**Features**:
- RESTful API with JSON responses
- CORS-enabled for frontend access
- KV storage for job states and vulnerabilities
- Task deduplication
- Scanner coordination
- LLM triage data preparation

## Data Flow

```
┌─────────────┐
│   Browser   │
│  (GitHub    │
│   Pages)    │
└──────┬──────┘
       │
       │ HTTPS Request
       │ (JSON)
       ▼
┌─────────────────────────┐
│  Cloudflare Worker      │
│  (Python API)           │
│                         │
│  ┌─────────────────┐   │
│  │ Request Router  │   │
│  └────────┬────────┘   │
│           │             │
│  ┌────────▼────────┐   │
│  │ API Handlers    │   │
│  │ - Queue Tasks   │   │
│  │ - Register      │   │
│  │ - Ingest        │   │
│  │ - Status        │   │
│  └────────┬────────┘   │
│           │             │
│  ┌────────▼────────┐   │
│  │ Scanner         │   │
│  │ Coordinator     │   │
│  └────────┬────────┘   │
│           │             │
│  ┌────────▼────────┐   │
│  │ Scanners        │   │
│  │ - Web2          │   │
│  │ - Web3          │   │
│  │ - Static        │   │
│  │ - Contract      │   │
│  │ - Volunteer     │   │
│  └────────┬────────┘   │
│           │             │
└───────────┼─────────────┘
            │
            ▼
┌─────────────────────┐
│ Cloudflare KV Store │
│ - Job States        │
│ - Task Queue        │
│ - Vulnerabilities   │
│ - Target Registry   │
└─────────────────────┘
```

## API Endpoints

### 1. Root Endpoint
- **Method**: GET
- **Path**: `/`
- **Purpose**: API information and status

### 2. Queue Tasks
- **Method**: POST
- **Path**: `/api/tasks/queue`
- **Purpose**: Queue new security scanning tasks
- **Input**: `target_id`, `task_types[]`, `priority`
- **Output**: `job_id`, `tasks_queued`

### 3. Register Target
- **Method**: POST
- **Path**: `/api/targets/register`
- **Purpose**: Register a new scan target
- **Input**: `target_type`, `target`, `scan_types[]`, `notes`
- **Output**: `target_id`

### 4. Ingest Results
- **Method**: POST
- **Path**: `/api/results/ingest`
- **Purpose**: Accept scan results from agents
- **Input**: `task_id`, `agent_type`, `results{}`
- **Output**: `result_id`, `vulnerabilities_found`

### 5. Job Status
- **Method**: GET
- **Path**: `/api/jobs/status`
- **Purpose**: Get current job status
- **Query**: `job_id`
- **Output**: `status`, `progress`, `completed`, `total`

### 6. List Tasks
- **Method**: GET
- **Path**: `/api/tasks/list`
- **Purpose**: List all tasks for a job
- **Query**: `job_id`
- **Output**: Array of tasks

### 7. Vulnerabilities
- **Method**: GET
- **Path**: `/api/vulnerabilities`
- **Purpose**: Query vulnerability database
- **Query**: `limit`, `severity`
- **Output**: Array of vulnerabilities

## Security Scanners

### Web2 Crawler
- **Purpose**: Web application vulnerability scanning
- **Checks**: XSS, CSRF, SQLi, security headers, authentication
- **Output**: Findings and vulnerabilities

### Web3 Monitor
- **Purpose**: Blockchain and smart contract monitoring
- **Checks**: Transaction patterns, malicious addresses, gas usage
- **Output**: Blockchain-specific findings

### Static Analyzer
- **Purpose**: Source code security analysis
- **Checks**: Code patterns, dependency vulnerabilities, secrets
- **Supports**: Python, JavaScript, Java, Go, Rust

### Contract Scanner
- **Purpose**: Smart contract security auditing
- **Checks**: Reentrancy, access control, integer issues, gas optimization
- **Supports**: Solidity, Vyper

### Volunteer Agent Manager
- **Purpose**: Community-driven security testing
- **Features**: Agent registration, task distribution, result validation

## Data Models

### Task
```typescript
{
  task_id: string
  job_id: string
  target_id: string
  task_type: string
  priority: "low" | "medium" | "high"
  status: "queued" | "running" | "completed" | "failed"
  created_at: ISO8601
  completed_at?: ISO8601
  result_id?: string
}
```

### Target
```typescript
{
  target_id: string
  target_type: "web2" | "web3" | "api" | "repo" | "contract"
  target_url: string
  scan_types: string[]
  notes: string
  registered_at: ISO8601
}
```

### Vulnerability
```typescript
{
  vulnerability_id: string
  type: string
  severity: "critical" | "high" | "medium" | "low" | "info"
  title: string
  description: string
  affected_component: string
  cve_id?: string
  cvss_score?: number
  remediation?: string
  discovered_at: ISO8601
}
```

## Storage Strategy

### Cloudflare KV Namespaces

1. **JOB_STATE** - Job state tracking
   - Key: `job:{job_id}`
   - TTL: Persistent
   - Contains: Job metadata, progress, task IDs

2. **TASK_QUEUE** - Task queue management
   - Key: `{task_id}`
   - TTL: 24 hours
   - Contains: Task details and status

3. **VULN_DB** - Vulnerability database
   - Key: `vuln:{vuln_id}`
   - TTL: 30 days
   - Contains: Vulnerability details

4. **TARGET_REGISTRY** - Target registry
   - Key: `{target_id}`
   - TTL: Persistent
   - Contains: Target metadata

## Scalability

### Horizontal Scaling
- Cloudflare Workers automatically scale to handle requests
- No server management required
- Global edge deployment

### Task Distribution
- Scanner coordinator manages task assignment
- Tasks are queued and processed asynchronously
- Deduplication prevents redundant work

### Storage Optimization
- KV stores are eventually consistent
- TTLs manage data lifecycle
- Only critical data is persisted

## Security Considerations

### Frontend Security
- Static hosting on GitHub Pages (HTTPS enforced)
- No sensitive data stored client-side
- API keys not exposed to frontend

### Backend Security
- CORS configured (should restrict to specific domain in production)
- Input validation on all endpoints
- Error handling prevents information leakage
- KV storage access controlled

### Data Security
- Vulnerabilities stored temporarily (30-day TTL)
- No PII collected
- Task data expires after 24 hours

## LLM Triage Integration

The system prepares vulnerability data for LLM-based triage:

```python
{
  'result_id': string,
  'task_id': string,
  'agent_type': string,
  'summary': {
    'total_findings': number,
    'total_vulnerabilities': number,
    'critical_count': number,
    'high_count': number
  },
  'vulnerabilities': [...],
  'findings': [...],
  'metadata': {...}
}
```

This structured format enables:
- Automated severity assessment
- Vulnerability classification
- Priority ranking
- False positive reduction
- Actionable remediation suggestions

## Future Enhancements

### Planned Features
- WebSocket support for real-time updates
- Webhook notifications for job completion
- Advanced filtering and search
- Vulnerability deduplication across scans
- Integration with external vulnerability databases
- Automated remediation suggestions
- Report generation (PDF, HTML)
- API authentication (JWT, API keys)
- Rate limiting per user/IP
- Advanced analytics and metrics

### Integration Opportunities
- CI/CD pipeline integration
- GitHub Security Advisory integration
- CVE database integration
- Bug bounty platform integration
- SIEM system integration

## Performance Characteristics

### Frontend
- Static assets cached by CDN
- Minimal JavaScript bundle size
- Lazy loading for dashboard data
- Responsive to all device sizes

### Backend
- Sub-100ms API response times (typical)
- Global edge deployment
- KV reads: ~50ms
- KV writes: ~100ms
- Automatic scaling to demand

## Development Workflow

### Local Development
1. Frontend: `python -m http.server 8000`
2. Backend: `wrangler dev`
3. Update config.js to point to local backend

### Testing
1. Python syntax: `python -m py_compile src/**/*.py`
2. Frontend: Manual testing in browser
3. API: cURL or Postman testing

### Deployment
1. Frontend: Git push to main branch (auto-deploys)
2. Backend: `wrangler publish`
3. Update config.js with production URL

## Monitoring & Debugging

### Frontend
- Browser DevTools console
- Network tab for API requests
- localStorage for job tracking

### Backend
- `wrangler tail` for live logs
- Cloudflare dashboard for metrics
- Error rate monitoring
- Request count tracking

## Conclusion

BLT-NetGuardian's architecture provides:
- ✅ Scalability through serverless deployment
- ✅ Global availability via edge network
- ✅ Cost-effectiveness (pay-per-use)
- ✅ Easy maintenance (no servers)
- ✅ Fast performance (edge computing)
- ✅ Modern development experience
- ✅ Extensibility for new scanners
- ✅ Security by design

The split architecture allows independent development and deployment of frontend and backend components while maintaining a cohesive user experience.
