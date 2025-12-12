# BLT-NetGuardian API Documentation

## Base URL
```
https://your-worker.workers.dev
```

## Authentication
Currently, all endpoints are open. In production, implement authentication using:
- API keys
- JWT tokens
- Cloudflare Access

## Endpoints

### 1. Home / Web Interface

**GET /**

Returns the main web interface HTML.

**Response**: HTML page

---

### 2. Queue Tasks

**POST /api/tasks/queue**

Queue new security scanning tasks for a target.

**Request Body:**
```json
{
  "target_id": "string (required)",
  "task_types": ["string"] (required),
  "priority": "low|medium|high (optional, default: medium)"
}
```

**Task Types:**
- `crawler` - Web2 application crawling
- `static_analysis` - Static code analysis
- `contract_audit` - Smart contract audit
- `vulnerability_scan` - Vulnerability scanning
- `penetration_test` - Penetration testing
- `web3_monitor` - Web3 blockchain monitoring

**Response (200):**
```json
{
  "success": true,
  "job_id": "string",
  "tasks_queued": 3,
  "tasks_deduplicated": 1,
  "message": "Successfully queued 3 tasks for processing"
}
```

**Errors:**
- `400` - Missing required fields
- `500` - Failed to queue tasks

---

### 3. Register Target

**POST /api/targets/register**

Register a new scan target in the system.

**Request Body:**
```json
{
  "target_type": "web2|web3|api|repo|contract (required)",
  "target": "string (required)",
  "scan_types": ["string"] (optional),
  "notes": "string (optional)"
}
```

**Target Types:**
- `web2` - Website or web application
- `web3` - Blockchain address or smart contract
- `api` - API endpoint
- `repo` - Code repository
- `contract` - Smart contract

**Response (200):**
```json
{
  "success": true,
  "target_id": "string",
  "message": "Target registered successfully"
}
```

**Errors:**
- `400` - Missing required fields
- `500` - Failed to register target

---

### 4. Ingest Results

**POST /api/results/ingest**

Submit scan results from security scanning agents.

**Request Body:**
```json
{
  "task_id": "string (required)",
  "agent_type": "string (required)",
  "results": {
    "findings": [
      {
        "type": "string",
        "severity": "critical|high|medium|low|info",
        "title": "string",
        "description": "string",
        "location": "string",
        "remediation": "string"
      }
    ],
    "vulnerabilities": [
      {
        "type": "string",
        "severity": "critical|high|medium|low|info",
        "title": "string",
        "description": "string",
        "affected_component": "string",
        "cve_id": "string (optional)",
        "cvss_score": 0.0-10.0 (optional),
        "remediation": "string (optional)"
      }
    ],
    "metadata": {}
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "result_id": "string",
  "vulnerabilities_found": 2,
  "triage_ready": true,
  "message": "Results ingested successfully"
}
```

**Errors:**
- `400` - Missing required fields
- `500` - Failed to ingest results

---

### 5. Get Job Status

**GET /api/jobs/status**

Get the current status of a scanning job.

**Query Parameters:**
- `job_id` (required) - The job ID to query

**Response (200):**
```json
{
  "job_id": "string",
  "status": "queued|running|completed",
  "total": 5,
  "completed": 3,
  "progress": 60,
  "created_at": "2024-01-01T00:00:00.000Z",
  "updated_at": "2024-01-01T00:05:00.000Z"
}
```

**Errors:**
- `400` - Missing job_id parameter
- `404` - Job not found
- `500` - Failed to get job status

---

### 6. List Tasks

**GET /api/tasks/list**

List all tasks for a specific job.

**Query Parameters:**
- `job_id` (required) - The job ID

**Response (200):**
```json
{
  "job_id": "string",
  "tasks": [
    {
      "task_id": "string",
      "job_id": "string",
      "target_id": "string",
      "task_type": "string",
      "priority": "string",
      "status": "string",
      "created_at": "string",
      "completed_at": "string|null",
      "result_id": "string|null"
    }
  ]
}
```

**Errors:**
- `400` - Missing job_id parameter
- `404` - Job not found
- `500` - Failed to list tasks

---

### 7. Get Vulnerabilities

**GET /api/vulnerabilities**

Query the vulnerability database.

**Query Parameters:**
- `limit` (optional, default: 50) - Maximum number of results
- `severity` (optional) - Filter by severity (critical|high|medium|low|info)

**Response (200):**
```json
{
  "count": 10,
  "vulnerabilities": [
    {
      "vulnerability_id": "string",
      "type": "string",
      "severity": "critical|high|medium|low|info",
      "title": "string",
      "description": "string",
      "affected_component": "string",
      "task_id": "string",
      "result_id": "string",
      "discovered_at": "string",
      "cve_id": "string|null",
      "cvss_score": 0.0-10.0|null,
      "remediation": "string|null"
    }
  ]
}
```

**Errors:**
- `500` - Failed to get vulnerabilities

---

### 8. Dashboard

**GET /dashboard**

Returns the monitoring dashboard HTML.

**Response**: HTML page

---

## Error Response Format

All error responses follow this format:

```json
{
  "error": "Error category",
  "message": "Detailed error message"
}
```

## Rate Limiting

Currently not implemented. In production, consider:
- Rate limiting per IP address
- Rate limiting per API key
- Cloudflare rate limiting rules

## CORS

All API endpoints support CORS with the following headers:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization`

## Data Storage

Data is stored in Cloudflare KV with the following TTLs:
- Tasks: 24 hours
- Vulnerabilities: 30 days
- Job states: Persistent
- Targets: Persistent

## Example Workflows

### Complete Scan Workflow

1. Register target:
```bash
curl -X POST https://your-worker.workers.dev/api/targets/register \
  -H "Content-Type: application/json" \
  -d '{
    "target_type": "web2",
    "target": "https://example.com",
    "scan_types": ["crawler", "vulnerability_scan"]
  }'
```

2. Queue tasks:
```bash
curl -X POST https://your-worker.workers.dev/api/tasks/queue \
  -H "Content-Type: application/json" \
  -d '{
    "target_id": "abc123",
    "task_types": ["crawler", "vulnerability_scan"],
    "priority": "high"
  }'
```

3. Check status:
```bash
curl "https://your-worker.workers.dev/api/jobs/status?job_id=job123"
```

4. View results:
```bash
curl "https://your-worker.workers.dev/api/vulnerabilities?severity=critical"
```

### Agent Result Submission

```bash
curl -X POST https://your-worker.workers.dev/api/results/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task123",
    "agent_type": "web2_crawler",
    "results": {
      "findings": [
        {
          "type": "xss",
          "severity": "high",
          "title": "Cross-Site Scripting Vulnerability",
          "description": "Unescaped user input in search parameter",
          "location": "/search?q=",
          "remediation": "Sanitize and escape all user input"
        }
      ],
      "vulnerabilities": [],
      "metadata": {
        "scan_duration": "45s",
        "pages_crawled": 127
      }
    }
  }'
```

## Webhook Support (Future)

Future versions will support webhooks for:
- Job completion notifications
- Vulnerability alerts
- Task status updates

## WebSocket Support (Future)

Future versions may support WebSocket connections for:
- Real-time job progress updates
- Live vulnerability feeds
- Agent communication
