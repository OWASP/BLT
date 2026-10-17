# API Documentation

This document describes the API interface between the BLT NetGuardian Client and the Cloudflare Worker backend.

## Base URL

The API base URL is configurable in the client. Example:
```
https://api.netguardian.example.com
```

## Authentication

Currently, the API does not require authentication. Future versions may implement:
- API keys
- OAuth 2.0
- JWT tokens

## Content Type

All requests and responses use `application/json`.

## Error Handling

The API uses standard HTTP status codes:

- `200 OK` - Request succeeded
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `409 Conflict` - Duplicate resource
- `500 Internal Server Error` - Server error

Error Response Format:
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

## Task Endpoints

### Queue Task

Queue a new security scanning task.

**Endpoint**: `POST /api/tasks/queue`

**Request Body**:
```json
{
  "id": "uuid-v4",
  "type": "web2Crawler|web3Monitor|staticAnalyzer|contractScanner|volunteerAgent",
  "target": "https://example.com",
  "parameters": {
    "depth": 3,
    "timeout": 30000
  },
  "status": "pending",
  "createdAt": "2024-01-01T00:00:00.000Z"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid-v4",
  "type": "web2Crawler",
  "target": "https://example.com",
  "parameters": {
    "depth": 3,
    "timeout": 30000
  },
  "status": "queued",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "completedAt": null,
  "result": null,
  "error": null
}
```

### List Tasks

Retrieve a list of tasks with optional filtering.

**Endpoint**: `GET /api/tasks?status={status}`

**Query Parameters**:
- `status` (optional): Filter by task status (pending, queued, processing, completed, failed)

**Response**: `200 OK`
```json
[
  {
    "id": "uuid-v4",
    "type": "web2Crawler",
    "target": "https://example.com",
    "parameters": {},
    "status": "completed",
    "createdAt": "2024-01-01T00:00:00.000Z",
    "completedAt": "2024-01-01T00:05:00.000Z",
    "result": "success",
    "error": null
  }
]
```

### Get Task

Retrieve details of a specific task.

**Endpoint**: `GET /api/tasks/:id`

**Response**: `200 OK`
```json
{
  "id": "uuid-v4",
  "type": "web2Crawler",
  "target": "https://example.com",
  "parameters": {},
  "status": "completed",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "completedAt": "2024-01-01T00:05:00.000Z",
  "result": "success",
  "error": null
}
```

## Target Endpoints

### Register Target

Register a new scan target.

**Endpoint**: `POST /api/targets/register`

**Request Body**:
```json
{
  "id": "uuid-v4",
  "url": "https://example.com",
  "type": "website|smartContract|api|repository",
  "metadata": {
    "priority": "high",
    "industry": "technology"
  },
  "registeredAt": "2024-01-01T00:00:00.000Z",
  "isActive": true
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid-v4",
  "url": "https://example.com",
  "type": "website",
  "metadata": {
    "priority": "high",
    "industry": "technology"
  },
  "registeredAt": "2024-01-01T00:00:00.000Z",
  "isActive": true
}
```

### List Targets

Retrieve a list of registered targets.

**Endpoint**: `GET /api/targets?isActive={boolean}`

**Query Parameters**:
- `isActive` (optional): Filter by active status (true, false)

**Response**: `200 OK`
```json
[
  {
    "id": "uuid-v4",
    "url": "https://example.com",
    "type": "website",
    "metadata": {},
    "registeredAt": "2024-01-01T00:00:00.000Z",
    "isActive": true
  }
]
```

### Get Target

Retrieve details of a specific target.

**Endpoint**: `GET /api/targets/:id`

**Response**: `200 OK`
```json
{
  "id": "uuid-v4",
  "url": "https://example.com",
  "type": "website",
  "metadata": {},
  "registeredAt": "2024-01-01T00:00:00.000Z",
  "isActive": true
}
```

### Deactivate Target

Deactivate a registered target.

**Endpoint**: `DELETE /api/targets/:id`

**Response**: `204 No Content`

## Result Endpoints

### Ingest Result

Submit agent scan results.

**Endpoint**: `POST /api/results/ingest`

**Request Body**:
```json
{
  "id": "uuid-v4",
  "taskId": "task-uuid",
  "agentId": "agent-uuid",
  "agentType": "web2Crawler",
  "findings": {
    "pagesScanned": 145,
    "vulnerabilitiesFound": 3
  },
  "vulnerabilities": [
    {
      "id": "vuln-uuid",
      "title": "SQL Injection",
      "description": "SQL injection vulnerability detected",
      "severity": "critical|high|medium|low|info",
      "cve": "CVE-2024-12345",
      "cwe": "CWE-89",
      "details": {
        "location": "/login",
        "parameter": "username"
      }
    }
  ],
  "submittedAt": "2024-01-01T00:00:00.000Z",
  "status": "pending"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid-v4",
  "taskId": "task-uuid",
  "agentId": "agent-uuid",
  "agentType": "web2Crawler",
  "findings": {
    "pagesScanned": 145,
    "vulnerabilitiesFound": 3
  },
  "vulnerabilities": [
    {
      "id": "vuln-uuid",
      "title": "SQL Injection",
      "description": "SQL injection vulnerability detected",
      "severity": "critical",
      "cve": "CVE-2024-12345",
      "cwe": "CWE-89",
      "details": {
        "location": "/login",
        "parameter": "username"
      }
    }
  ],
  "submittedAt": "2024-01-01T00:00:00.000Z",
  "status": "processing"
}
```

### List Results

Retrieve a list of agent results.

**Endpoint**: `GET /api/results?taskId={taskId}`

**Query Parameters**:
- `taskId` (optional): Filter by task ID

**Response**: `200 OK`
```json
[
  {
    "id": "uuid-v4",
    "taskId": "task-uuid",
    "agentId": "agent-uuid",
    "agentType": "web2Crawler",
    "findings": {},
    "vulnerabilities": [],
    "submittedAt": "2024-01-01T00:00:00.000Z",
    "status": "stored"
  }
]
```

### Get Result

Retrieve details of a specific result.

**Endpoint**: `GET /api/results/:id`

**Response**: `200 OK`
```json
{
  "id": "uuid-v4",
  "taskId": "task-uuid",
  "agentId": "agent-uuid",
  "agentType": "web2Crawler",
  "findings": {},
  "vulnerabilities": [],
  "submittedAt": "2024-01-01T00:00:00.000Z",
  "status": "stored"
}
```

## Data Models

### Task Types

- `web2Crawler` - Traditional web application crawling
- `web3Monitor` - Blockchain/Web3 monitoring
- `staticAnalyzer` - Static code analysis
- `contractScanner` - Smart contract security scanning
- `volunteerAgent` - Community-contributed agents

### Task Status

- `pending` - Task created but not yet queued
- `queued` - Task queued for processing
- `processing` - Task currently being processed
- `completed` - Task completed successfully
- `failed` - Task failed with error

### Target Types

- `website` - Web application
- `smartContract` - Blockchain smart contract
- `api` - REST/GraphQL API
- `repository` - Code repository

### Vulnerability Severity

- `critical` - Critical security issue
- `high` - High severity issue
- `medium` - Medium severity issue
- `low` - Low severity issue
- `info` - Informational finding

### Result Status

- `pending` - Result submitted, awaiting processing
- `processing` - Result being processed
- `triaged` - Result triaged by LLM engine
- `stored` - Result stored in vulnerability database

## Rate Limiting

Future versions may implement rate limiting:
- Per-client limits
- Per-endpoint limits
- Backoff strategies

## Pagination

Future versions may implement pagination for list endpoints:
```
GET /api/tasks?page=1&limit=50
```

Response will include pagination metadata:
```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "totalPages": 3
  }
}
```

## Webhook Support

Future versions may support webhooks for:
- Task completion notifications
- Vulnerability discovery alerts
- System status updates

## Client SDK

The Flutter client provides a complete SDK for interacting with the API:

```dart
// Initialize
final apiService = ApiService(baseUrl: 'https://api.example.com');
final taskManager = TaskManager(apiService: apiService);

// Queue task
final task = await taskManager.queueTask(
  type: 'web2Crawler',
  target: 'https://example.com',
  parameters: {},
);

// Get task
final task = await taskManager.getTask(taskId);

// List tasks
final tasks = await taskManager.getTasks(status: TaskStatus.completed);
```

See [API Examples](example/api_examples.md) for more usage examples.