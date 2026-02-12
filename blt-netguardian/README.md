# BLT-NetGuardian

🛡️ Autonomous Internet Security Scanner powered by Cloudflare Workers

## Deploy to Cloudflare

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/OWASP-BLT/BLT-NetGuardian)

Click the button above to deploy BLT-NetGuardian to your Cloudflare account in one click!

## Overview

BLT-NetGuardian is an **autonomous security scanning system** that continuously discovers and scans the internet for security vulnerabilities. Unlike traditional scanners that require manual target submission, BLT-NetGuardian actively discovers domains, repositories, smart contracts, and APIs using multiple discovery methods, automatically scans them for vulnerabilities, and contacts stakeholders when issues are found.

## Features

### 🤖 Autonomous Discovery

- **Certificate Transparency Monitoring**: Discovers new domains from CT logs
- **GitHub Repository Scanning**: Tracks trending and newly updated repositories
- **Blockchain Monitoring**: Detects new smart contract deployments
- **Subdomain Enumeration**: Discovers subdomains of known targets
- **API Directory Scanning**: Monitors public API directories
- **User Suggestions**: Allows community to guide the scanner

### 📧 Automatic Contact & Notification

- **security.txt Integration**: RFC 9116 compliant contact discovery
- **WHOIS Lookup**: Finds domain registrant contacts
- **GitHub Security Advisory**: Direct security team notification
- **Responsible Disclosure**: 90-day disclosure timeline
- **Contact Logging**: Tracks all notification attempts

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

**Live Autonomous Scanner Dashboard:**
- Real-time scanning status with current target
- Live discovery feed showing newly found targets
- Simple suggestion input to guide the scanner
- Statistics: domains discovered, repos found, contacts made
- Recent discoveries with vulnerability status

**No Manual Forms Required** - The system continuously scans on its own!

## Architecture

BLT-NetGuardian uses a split architecture:
- **Frontend**: Static HTML/CSS/JS hosted on **GitHub Pages**
- **Backend**: Python API worker running on **Cloudflare Workers**

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Pages                            │
│                   (Frontend - Static)                       │
│                                                             │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐  │
│  │  index.html  │  │ dashboard   │  │ vulnerabilities  │  │
│  │  (Main UI)   │  │   .html     │  │    .html         │  │
│  └──────────────┘  └─────────────┘  └──────────────────┘  │
│                                                             │
│         │                                                   │
└─────────┼───────────────────────────────────────────────────┘
          │ HTTPS/REST API
          ▼
┌─────────────────────────────────────────────────────────────┐
│              Cloudflare Worker (Backend)                    │
│                    Python API Only                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               API Endpoints                          │  │
│  │  • /api/tasks/queue                                  │  │
│  │  • /api/targets/register                            │  │
│  │  • /api/results/ingest                              │  │
│  │  • /api/jobs/status                                 │  │
│  │  • /api/vulnerabilities                             │  │
│  └──────────────────────────────────────────────────────┘  │
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

## How It Works

### 1. Autonomous Discovery
The system continuously discovers new targets using:
- **CT Log Monitoring**: Watches Certificate Transparency logs for new SSL certificates
- **GitHub API**: Monitors trending repositories and recent updates
- **Blockchain Scanners**: Tracks new smart contract deployments on Ethereum, Polygon, BSC
- **DNS Enumeration**: Discovers subdomains and related domains
- **Public Directories**: Scans API directories and service listings

### 2. Automatic Scanning
When a target is discovered:
1. Target is automatically registered in the system
2. Appropriate scanners are selected based on target type
3. Scan tasks are queued with priority based on discovery source
4. Multiple scanners run in parallel for comprehensive coverage
5. Results are aggregated and stored

### 3. Vulnerability Detection
Each scanner detects specific vulnerability types:
- **Web2**: XSS, CSRF, SQLi, security misconfigurations
- **Web3**: Reentrancy, access control, integer issues
- **Static**: Code vulnerabilities, dependency issues, secrets
- **Contract**: Smart contract specific vulnerabilities

### 4. Automatic Contact
When vulnerabilities are found:
1. System looks for contact information (security.txt, WHOIS, GitHub)
2. Prepares professional vulnerability disclosure report
3. Attempts contact through multiple channels
4. Logs all contact attempts for transparency
5. Follows 90-day responsible disclosure timeline

### 5. User Guidance
Community members can:
- Suggest specific targets for immediate scanning
- Mark suggestions as priority for faster processing
- View real-time discovery and scanning status
- Monitor contact attempts and responses

## API Endpoints

### Autonomous Discovery

#### Suggest a Target
```
POST /api/discovery/suggest
Content-Type: application/json

{
  "suggestion": "example.com",
  "priority": true
}
```

#### Get Discovery Status
```
GET /api/discovery/status
```

#### Get Recent Discoveries
```
GET /api/discovery/recent?limit=20
```

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

### Quick Start - One-Click Deploy

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/OWASP-BLT/BLT-NetGuardian)

**Quick Deploy**: Click the button above to instantly deploy the backend to your Cloudflare account!

BLT-NetGuardian is split into two parts:

1. **Frontend (GitHub Pages)** - Already live at `https://owasp-blt.github.io/BLT-NetGuardian/`
2. **Backend (Cloudflare Workers)** - Deploy with one click or manually (instructions below)

### Deploy the Backend (Cloudflare Workers)

#### Option 1: One-Click Deploy (Recommended)

Simply click the "Deploy to Cloudflare Workers" button above. This will:
- Fork the repository to your GitHub account (if needed)
- Guide you through connecting your Cloudflare account
- Automatically create required KV namespaces
- Deploy the worker to your Cloudflare account

#### Option 2: Manual Deployment

##### Prerequisites

- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- Cloudflare account

##### Steps

1. Install Wrangler:
```bash
npm install -g wrangler
```

2. Login to Cloudflare:
```bash
wrangler login
```

3. Create KV namespaces:
```bash
wrangler kv:namespace create "JOB_STATE"
wrangler kv:namespace create "TASK_QUEUE"
wrangler kv:namespace create "VULN_DB"
wrangler kv:namespace create "TARGET_REGISTRY"
```

4. Update `wrangler.toml` with your KV namespace IDs

5. Deploy:
```bash
wrangler publish
```

6. Update `assets/js/config.js` with your Worker URL:
```javascript
API_BASE_URL: 'https://blt-netguardian.your-subdomain.workers.dev'
```

7. Commit and push the config change to deploy to GitHub Pages

### Local Development

#### Frontend
```bash
# Serve static files
python -m http.server 8000
# Visit http://localhost:8000
```

#### Backend
```bash
wrangler dev
# API available at http://localhost:8787
```

Update `assets/js/config.js` to use local backend:
```javascript
API_BASE_URL: 'http://localhost:8787'
```

For detailed deployment instructions, see [DEPLOY.md](DEPLOY.md)

## Security Tools Reference

BLT-NetGuardian can integrate with a wide variety of security scanning tools. For a comprehensive list of vulnerability scanning tools and resources, see [SECURITY_TOOLS.md](SECURITY_TOOLS.md).

The document includes tools for:
- Static Application Security Testing (SAST)
- Dynamic Application Security Testing (DAST)
- Dependency and Supply Chain Security
- Container and Infrastructure Security
- Smart Contract Security
- Secret Detection
- And many more categories

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