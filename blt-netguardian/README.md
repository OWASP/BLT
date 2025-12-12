# BLT-NetGuardian

🛡️ Comprehensive Security Pipeline & Vulnerability Scanner powered by Cloudflare Workers

## Overview

BLT-NetGuardian is a Cloudflare Python Worker that implements a complete security scanning pipeline. It coordinates multiple security scanning agents including Web2 crawlers, Web3 monitors, static code analyzers, smart contract scanners, and volunteer security testers to provide comprehensive vulnerability detection and analysis.

## Features

### 🚀 Core Capabilities

- **Task Queueing**: Efficient task queue management with automatic deduplication
- **Target Registration**: Register and manage scan targets (websites, APIs, smart contracts, repositories)
- **Result Ingestion**: Collect and aggregate scan results from multiple agents
- **Job State Management**: Track scan progress and status in real-time
- **Vulnerability Database**: Store and query discovered vulnerabilities
- **LLM Triage Engine**: Prepare vulnerability data for AI-powered classification and prioritization

### 🔍 Security Scanners

1. **Web2 Crawler** - Web application vulnerability scanner
   - XSS, CSRF, SQLi detection
   - Security header analysis
   - Form and endpoint discovery
   - Authentication testing

2. **Web3 Monitor** - Blockchain and smart contract monitoring
   - Transaction pattern analysis
   - Malicious address detection
   - Gas usage optimization
   - Real-time blockchain monitoring

3. **Static Analyzer** - Source code security analysis
   - SAST tool integration
   - Dependency vulnerability scanning
   - Hardcoded secret detection
   - Multi-language support (Python, JavaScript, Java, Go, Rust)

4. **Contract Scanner** - Smart contract auditing
   - Reentrancy vulnerability detection
   - Access control analysis
   - Integer overflow/underflow checks
   - Gas optimization recommendations
   - Solidity and Vyper support

5. **Volunteer Agent Manager** - Community security testing
   - Distributed testing coordination
   - Agent registration and management
   - Result validation and aggregation
   - Contributor rewards

### 🌐 Web Interface

Live web interface for submitting scan targets and monitoring job status:
- Target submission form with multiple scan types
- Real-time job progress tracking
- Vulnerability dashboard
- Scanner status monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare Worker                        │
│                                                             │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐  │
│  │   API Layer  │  │  Web UI     │  │  Job Coordinator │  │
│  └──────┬───────┘  └──────┬──────┘  └────────┬─────────┘  │
│         │                  │                   │             │
│         └──────────────────┴───────────────────┘             │
│                            │                                 │
│         ┌──────────────────┴──────────────────┐             │
│         │     Scanner Coordinator             │             │
│         └──────────┬──────────────────────────┘             │
│                    │                                         │
│  ┌─────────────────┼─────────────────────────────────────┐  │
│  │                 │                                     │  │
│  ▼                 ▼                 ▼                   ▼  │
│ Web2          Web3             Static            Contract   │
│ Crawler       Monitor          Analyzer          Scanner    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
           ┌────────────────────────┐
           │   Cloudflare KV Store  │
           │  ├─ Job States         │
           │  ├─ Task Queue         │
           │  ├─ Vulnerability DB   │
           │  └─ Target Registry    │
           └────────────────────────┘
```

## API Endpoints

### Task Management

#### Queue Tasks
```
POST /api/tasks/queue
Content-Type: application/json

{
  "target_id": "abc123",
  "task_types": ["crawler", "static_analysis"],
  "priority": "high"
}
```

#### List Tasks
```
GET /api/tasks/list?job_id=job123
```

### Target Registration

#### Register Target
```
POST /api/targets/register
Content-Type: application/json

{
  "target_type": "web2",
  "target": "https://example.com",
  "scan_types": ["crawler", "vulnerability_scan"],
  "notes": "Focus on authentication flows"
}
```

### Results & Vulnerabilities

#### Ingest Results
```
POST /api/results/ingest
Content-Type: application/json

{
  "task_id": "task123",
  "agent_type": "web2_crawler",
  "results": {
    "findings": [...],
    "vulnerabilities": [...]
  }
}
```

#### Get Vulnerabilities
```
GET /api/vulnerabilities?limit=50&severity=critical
```

### Job Status

#### Check Job Status
```
GET /api/jobs/status?job_id=job123
```

## Installation & Deployment

### Prerequisites

- [Node.js](https://nodejs.org/) v16+
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- Cloudflare account

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/OWASP-BLT/BLT-NetGuardian.git
cd BLT-NetGuardian
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Wrangler:
```bash
wrangler login
```

4. Create KV namespaces:
```bash
wrangler kv:namespace create "JOB_STATE"
wrangler kv:namespace create "TASK_QUEUE"
wrangler kv:namespace create "VULN_DB"
wrangler kv:namespace create "TARGET_REGISTRY"
```

5. Update `wrangler.toml` with your KV namespace IDs

6. Run locally:
```bash
wrangler dev
```

### Production Deployment

```bash
wrangler publish
```

## Configuration

Edit `wrangler.toml` to configure:

- KV namespace bindings
- Environment variables
- Worker routes
- Build settings

## Usage Examples

### Submit a Web Application Scan

```javascript
const response = await fetch('https://your-worker.workers.dev/api/targets/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    target_type: 'web2',
    target: 'https://example.com',
    scan_types: ['crawler', 'vulnerability_scan']
  })
});

const { target_id } = await response.json();

// Queue scanning tasks
await fetch('https://your-worker.workers.dev/api/tasks/queue', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    target_id,
    task_types: ['crawler', 'vulnerability_scan'],
    priority: 'high'
  })
});
```

### Check Scan Progress

```javascript
const response = await fetch(`https://your-worker.workers.dev/api/jobs/status?job_id=${jobId}`);
const status = await response.json();

console.log(`Progress: ${status.progress}% (${status.completed}/${status.total} tasks)`);
```

### View Vulnerabilities

```javascript
const response = await fetch('https://your-worker.workers.dev/api/vulnerabilities?severity=critical');
const { vulnerabilities } = await response.json();

vulnerabilities.forEach(vuln => {
  console.log(`${vuln.severity.toUpperCase()}: ${vuln.title}`);
});
```

## Security Considerations

- All API endpoints support CORS for web interface access
- Task deduplication prevents redundant scanning
- Vulnerability data is stored with 30-day expiration
- Results include LLM triage preparation for AI-powered analysis
- Volunteer agent submissions should be validated before acceptance

## Data Models

### Task
```typescript
{
  task_id: string
  job_id: string
  target_id: string
  task_type: "crawler" | "static_analysis" | "contract_audit" | ...
  priority: "low" | "medium" | "high"
  status: "queued" | "running" | "completed" | "failed"
  created_at: string
  completed_at?: string
  result_id?: string
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
  references?: string[]
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OWASP BLT Project
- Cloudflare Workers Platform
- Security research community

## Support

For issues and questions, please open an issue on GitHub.

---

Built with ❤️ by the OWASP BLT community