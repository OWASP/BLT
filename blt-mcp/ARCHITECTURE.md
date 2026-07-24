# BLT-MCP Architecture

This document describes the architecture and design of the BLT-MCP server implementation.

## Overview

The OWASP BLT toolchain consists of a **Dual Interface Ecosystem** that connects users (both Human and AI) to the BLT (Bug Logging Tool) backend REST API.

1. **BLT-CLI (Rust TUI):** An interactive Text User Interface designed for *Humans*.
2. **BLT-MCP (Python Server):** A Model Context Protocol server designed for *AI Agents* (e.g., Claude, Cursor, Cline).

Both interfaces ultimately consume the same core BLT REST API (`https://api.owaspblt.org`).

### TUI Modes (Direct vs MCP Mode)
The Rust TUI (`blt-cli`) features a unique dual-mode architecture:
- **Direct Mode (Standalone):** The TUI communicates directly with the BLT REST API via standard HTTP requests. This is the default, lightweight mode for users.
- **MCP Mode (Dogfooding):** When launched with the `--mcp-path` flag, the TUI transforms into an *MCP Client*. It spawns the Python `BLT-MCP` server as a background subprocess and routes its data requests through the MCP server. This allows developers to thoroughly test and "dogfood" the Python MCP server without needing a third-party AI client.

## Architecture Diagram

```text
                               ┌─────────────────────────┐
                               │       Human User        │
                               └────────────┬────────────┘
                                            │ interacts
┌─────────────────────────┐    ┌────────────▼────────────┐
│      AI Assistant       │    │     BLT-CLI (Rust)      │
│ (Claude, Cursor, etc.)  │    │     Terminal TUI        │
└────────────┬────────────┘    └─┬─────────────────────┬─┘
             │                   │                     │
             │ JSON-RPC          │ JSON-RPC            │
             │ (stdio)           │ (stdio)             │ HTTP
             │                   │ [--mcp-path]        │ (Direct Mode)
┌────────────▼───────────────────▼───────┐             │
│            BLT-MCP (Python)            │             │
│            MCP Server                  │             │
└────────────┬───────────────────────────┘             │
             │ HTTPS                                   │
             └───────────────────────┐   ┌─────────────┘
                                     │   │
                               ┌─────▼───▼───────────────┐
                               │     BLT REST API        │
                               │ https://api.owaspblt.org│
                               └─────────────────────────┘
```

## BLT-CLI (Rust TUI) Structure

The Rust CLI is an interactive Terminal User Interface (TUI) built using `ratatui` and `crossterm`. Its architecture separates state management, UI rendering, and data fetching into distinct modules:

- **`main.rs`**: The entry point. Handles CLI arguments, environment setup, and bootstraps either *Direct Mode* or *MCP Mode* (spawning the subprocess).
- **`app.rs`**: Manages the core application state (loaded data, current view, active tabs) and handles state transitions.
- **`tui.rs`**: Manages the terminal lifecycle (raw mode, alternate screens) and runs the primary **async event loop** (via `tokio`). Key-presses spawn background `tokio` tasks for network operations and communicate results back to the main loop through an `mpsc` channel of `AppEvent`s.
- **`ui.rs`**: Contains all `ratatui` rendering logic. Responsible for drawing layouts, panels, and widgets purely based on the current `app` state.
- **`api.rs`**: The HTTP client used in *Direct Mode* to fetch data directly from the BLT REST API.
- **`mcp_client.rs`**: The JSON-RPC client used in *MCP Mode*. It manages the Python subprocess and routes resource requests to it over `stdio`.
- **`scanner.rs`**: An asynchronous background security health scanner that runs independently alongside the UI. Each subprocess scan (Trivy, Semgrep, Bandit) is bounded by a **30-second timeout**; the process is killed on expiry.
- **`models.rs`**: Core data structures defining the shapes of issues, repos, and users.

---

## BLT-MCP Server Details
The remainder of this document focuses specifically on the architecture and design of the **BLT-MCP Python Server**.

## Component Details

### MCP Protocol Layer

The protocol layer handles all MCP-specific communication:

- **Transport**: Stdio-based transport for process-to-process communication
- **Protocol**: JSON-RPC 2.0 for request/response handling
- **Schemas**: Type-safe schema validation using Pydantic and FastMCP

#### Supported Capabilities
During the `initialize` handshake, the server negotiates and advertises the following MCP capabilities:
- **`tools`**: Supported (`listChanged`: false). Allows the server to expose executable actions like `submit_issue`.
- **`resources`**: Supported (`subscribe`: false, `listChanged`: false). Allows the server to expose read-only data URIs like `blt://issues`.
- **`prompts`**: Supported (`listChanged`: false). Allows the server to provide structured interaction templates like `triage_vulnerability`.
- **`experimental`**: Supported, serving as an extensible base for future experimental MCP features.

### Resources Layer

Resources provide read-only access to BLT data through URI patterns:

**URI Pattern**: `blt://{resource_type}[/{resource_id}]`

**Supported Resources**:
- `issues` - Bug reports and vulnerabilities
- `repos` - Tracked repositories
- `contributors` - User profiles and contributions
- `workflows` - Security workflow definitions
- `leaderboards` - Ranking and statistics
- `rewards` - Contributor points and gamification data

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
- Optional: repo_id, severity, type, confirmed
- Maps to: POST /bugs
- Note: The BLT API does not natively support a `title` field; the server prepends the title to the `description` payload.



#### add_comment
- Purpose: Add comments to issues
- Required: issue_id, comment_text
- Optional: confirmed
- Maps to: POST /bugs/{id}/comments

#### summarize_issue_context
- Purpose: Generate a structured summary of an issue's context (title, status, description, comments)
- Required: issue_id
- Maps to: GET /bugs/{id} and GET /bugs/{id}/comments

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
- Includes: Strengths, improvements, points recommendations

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
3. BLT-MCP → BLT API: GET /bugs/123
4. BLT API → BLT-MCP: { id: 123, title: "...", ... }
5. BLT-MCP → MCP Client: { contents: [{ text: "..." }] }
6. MCP Client → AI Agent: Display formatted issue data
```

### Execute Tool Example

```
1. AI Agent → MCP Client: "Submit a new XSS vulnerability"
2. MCP Client → BLT-MCP: tools/call { name: "submit_issue", arguments: {...} }
3. BLT-MCP validates input schema
4. BLT-MCP → BLT API: POST /bugs with body
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
- Type-safe Python implementation with Pydantic
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
BLT_API_BASE=https://api.owaspblt.org  # BLT API endpoint
BLT_API_KEY=your_key_here               # Authentication token
```

### MCP Client Configuration

```json
{
  "mcpServers": {
    "blt": {
      "command": "uv",
      "args": ["run", "blt-mcp"],
      "env": {
        "BLT_API_BASE": "https://api.owaspblt.org",
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
- Type mismatches caught by Pydantic and Python type hints
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
uv sync
```

### Running
```bash
uv run blt-mcp
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
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
