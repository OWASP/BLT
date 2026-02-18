# BLT-MCP Architecture

This document describes the architecture and design of the BLT-MCP server implementation.

## Overview

BLT-MCP is a Model Context Protocol (MCP) server that bridges AI agents with the BLT (Bug Logging Tool) ecosystem. It implements the MCP standard specification to provide structured, programmatic access to BLT functionality.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent / MCP Client                    │
│                  (Claude Desktop, Cline, etc.)               │
└────────────────────┬────────────────────────────────────────┘
                     │ JSON-RPC 2.0 over stdio
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    BLT-MCP Server                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           MCP Protocol Layer                         │   │
│  │  - Request/Response Handling                         │   │
│  │  - JSON-RPC 2.0 Transport (stdio)                    │   │
│  │  - Schema Validation                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Resources Layer                            │   │
│  │  - blt://issues                                      │   │
│  │  - blt://repos                                       │   │
│  │  - blt://contributors                                │   │
│  │  - blt://workflows                                   │   │
│  │  - blt://leaderboards                                │   │
│  │  - blt://rewards                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Tools Layer                                │   │
│  │  - submit_issue                                      │   │
│  │  - award_bacon                                       │   │
│  │  - update_issue_status                               │   │
│  │  - add_comment                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Prompts Layer                              │   │
│  │  - triage_vulnerability                              │   │
│  │  - plan_remediation                                  │   │
│  │  - review_contribution                               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Authentication & API Client                │   │
│  │  - OAuth/API Key Management                          │   │
│  │  - HTTP Request Handling                             │   │
│  │  - Error Handling                                    │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    BLT REST API                              │
│                https://blt.owasp.org/api                     │
└──────────────────────────────────────────────────────────────┘
```

## Component Details

### MCP Protocol Layer

The protocol layer handles all MCP-specific communication:

- **Transport**: Stdio-based transport for process-to-process communication
- **Protocol**: JSON-RPC 2.0 for request/response handling
- **Schemas**: Type-safe schema validation using MCP SDK types

### Resources Layer

Resources provide read-only access to BLT data through URI patterns:

**URI Pattern**: `blt://{resource_type}[/{resource_id}]`

**Supported Resources**:
- `issues` - Bug reports and vulnerabilities
- `repos` - Tracked repositories
- `contributors` - User profiles and contributions
- `workflows` - Security workflow definitions
- `leaderboards` - Ranking and statistics
- `rewards` - Bacon points and gamification data

**Implementation**:
- List handler: Returns all available resource URIs
- Read handler: Fetches resource data from BLT API
- Content type: application/json
- Parameterized URIs for specific resource access

### Tools Layer

Tools enable AI agents to perform actions:

**Tool Execution Flow**:
1. AI agent calls tool with parameters
2. Server validates input schema
3. Server makes authenticated API request
4. Response returned to agent

**Tool Specifications**:

#### submit_issue
- Purpose: Create new bug reports or vulnerability reports
- Required: title, description
- Optional: repo_id, severity, type
- Maps to: POST /api/issues

#### award_bacon
- Purpose: Reward contributors with bacon points
- Required: contributor_id, points, reason
- Maps to: POST /api/rewards

#### update_issue_status
- Purpose: Change issue workflow status
- Required: issue_id, status
- Optional: comment
- Maps to: PATCH /api/issues/{id}

#### add_comment
- Purpose: Add comments to issues
- Required: issue_id, comment
- Maps to: POST /api/issues/{id}/comments

### Prompts Layer

Prompts provide AI agents with structured guidance for common tasks:

**Prompt Execution Flow**:
1. AI agent requests prompt with arguments
2. Server generates context-specific prompt
3. Prompt returned with structured instructions
4. AI uses prompt to guide user interaction

**Prompt Specifications**:

#### triage_vulnerability
- Purpose: Guide security vulnerability analysis
- Input: vulnerability_description, affected_component
- Output: Structured triage workflow
- Includes: Severity assessment, impact analysis, recommendations

#### plan_remediation
- Purpose: Create remediation plans
- Input: issue_id, context
- Output: Step-by-step remediation plan
- Includes: Root cause, steps, testing, prevention

#### review_contribution
- Purpose: Evaluate contributions
- Input: contribution_id, contribution_type
- Output: Quality assessment and recommendations
- Includes: Strengths, improvements, bacon point recommendations

### Authentication & API Client

**Authentication**:
- OAuth 2.0 bearer token support
- API key authentication
- Environment-based configuration
- Secure credential storage

**API Client**:
- Base URL configuration: `BLT_API_BASE`
- Automatic header management
- Error handling and retries
- Type-safe response handling

## Data Flow

### Read Resource Example

```
1. AI Agent → MCP Client: "Show me issue 123"
2. MCP Client → BLT-MCP: resources/read { uri: "blt://issues/123" }
3. BLT-MCP → BLT API: GET /api/issues/123
4. BLT API → BLT-MCP: { id: 123, title: "...", ... }
5. BLT-MCP → MCP Client: { contents: [{ text: "..." }] }
6. MCP Client → AI Agent: Display formatted issue data
```

### Execute Tool Example

```
1. AI Agent → MCP Client: "Submit a new XSS vulnerability"
2. MCP Client → BLT-MCP: tools/call { name: "submit_issue", arguments: {...} }
3. BLT-MCP validates input schema
4. BLT-MCP → BLT API: POST /api/issues with body
5. BLT API → BLT-MCP: { id: 456, created_at: "...", ... }
6. BLT-MCP → MCP Client: { content: [{ text: "Issue created: 456" }] }
7. MCP Client → AI Agent: Confirm issue submission
```

### Use Prompt Example

```
1. AI Agent → MCP Client: "Help me triage this vulnerability"
2. MCP Client → BLT-MCP: prompts/get { name: "triage_vulnerability", arguments: {...} }
3. BLT-MCP generates structured prompt
4. BLT-MCP → MCP Client: { messages: [{ role: "user", content: {...} }] }
5. MCP Client injects prompt into conversation
6. AI Agent uses prompt to guide analysis
```

## Security Considerations

### Authentication
- API keys stored in environment variables only
- No hardcoded credentials
- Bearer token authentication for API requests
- Secure transmission over HTTPS to BLT API

### Input Validation
- JSON Schema validation for all tool inputs
- Type-safe TypeScript implementation
- Parameter validation before API calls
- Error messages don't leak sensitive data

### API Security
- Rate limiting awareness
- Error handling prevents information disclosure
- Proper HTTP status code handling
- TLS/SSL for external communication

### Access Control
- Authentication required for write operations
- Read operations may have public access
- Per-resource access control via BLT API
- Role-based permissions handled by BLT backend

## Configuration

### Environment Variables

```bash
BLT_API_BASE=https://blt.owasp.org/api  # BLT API endpoint
BLT_API_KEY=your_key_here               # Authentication token
```

### MCP Client Configuration

```json
{
  "mcpServers": {
    "blt": {
      "command": "node",
      "args": ["/path/to/dist/index.js"],
      "env": {
        "BLT_API_BASE": "https://blt.owasp.org/api",
        "BLT_API_KEY": "your_key_here"
      }
    }
  }
}
```

## Error Handling

### API Errors
- HTTP error codes mapped to user-friendly messages
- Network errors caught and reported
- Timeout handling
- Retry logic for transient failures

### Validation Errors
- Schema validation failures reported clearly
- Missing required parameters detected early
- Type mismatches caught by TypeScript
- Invalid URIs handled gracefully

### Runtime Errors
- Uncaught exceptions logged to stderr
- Process doesn't crash on errors
- Errors returned in MCP format
- Stack traces available for debugging

## Performance Considerations

### Caching
- No client-side caching (relies on BLT API caching)
- Stateless request handling
- Fast startup time
- Low memory footprint

### Scalability
- Stateless design enables horizontal scaling
- Per-request isolation
- No shared state between requests
- Thread-safe by design

### Resource Usage
- Minimal memory usage per request
- No connection pooling needed (stdio transport)
- Fast JSON parsing
- Efficient string operations

## Testing Strategy

### Unit Testing
- Test individual request handlers
- Mock BLT API responses
- Validate schema compliance
- Test error conditions

### Integration Testing
- Test with actual MCP clients
- Verify end-to-end flows
- Test authentication flows
- Validate API integration

### Manual Testing
- Use MCP Inspector for interactive testing
- Test with Claude Desktop
- Verify with Cline/Continue
- Real-world usage scenarios

## Deployment

### Installation
```bash
npm install
npm run build
```

### Running
```bash
node dist/index.js
# Server listens on stdio
```

### Monitoring
- Logs to stderr (stdout reserved for MCP)
- Error tracking
- API response times
- Request/response logging

## Future Enhancements

### Potential Features
- WebSocket support for real-time updates
- Advanced caching strategies
- Batch operations
- Search and filtering capabilities
- Webhook support
- GraphQL endpoint support
- Advanced analytics
- Rate limiting

### Performance Improvements
- Request batching
- Connection pooling
- Response caching
- Lazy loading
- Pagination optimization

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
