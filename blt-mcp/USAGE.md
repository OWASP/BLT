# BLT-MCP Usage Examples

This document provides practical examples of how to use the BLT-MCP server.

## Prerequisites

1. Install and build the server:
   ```bash
   npm install
   npm run build
   ```

2. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your BLT API credentials
   ```

## Configuration Examples

### Claude Desktop Configuration

Add to your Claude Desktop config file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "blt": {
      "command": "node",
      "args": ["/absolute/path/to/blt-mcp/dist/index.js"],
      "env": {
        "BLT_API_BASE": "https://blt.owasp.org/api",
        "BLT_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### Cline/Continue Configuration

For VS Code extensions like Cline or Continue, add to your MCP settings:

```json
{
  "mcpServers": {
    "blt": {
      "command": "node",
      "args": ["/absolute/path/to/blt-mcp/dist/index.js"],
      "env": {
        "BLT_API_BASE": "https://blt.owasp.org/api",
        "BLT_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Usage Scenarios

### Scenario 1: Reporting a Vulnerability

**User Query:**
```
I found a SQL injection vulnerability in the user registration endpoint of repo 456. 
Please submit this as a critical issue.
```

**What Happens:**
1. AI agent uses the `submit_issue` tool
2. Creates issue with:
   - Title: "SQL Injection in User Registration"
   - Description: Details about the vulnerability
   - Repository ID: 456
   - Severity: critical
   - Type: vulnerability

**Expected Result:**
```json
{
  "id": "789",
  "title": "SQL Injection in User Registration",
  "status": "open",
  "created_at": "2026-02-18T02:30:00Z"
}
```

### Scenario 2: Triaging Multiple Vulnerabilities

**User Query:**
```
Help me triage this XSS vulnerability: 
User input in the comment section is not properly sanitized, 
allowing arbitrary JavaScript execution. This affects the main web application.
```

**What Happens:**
1. AI agent uses the `triage_vulnerability` prompt
2. Provides structured analysis including:
   - Severity assessment
   - Potential impact
   - Affected systems
   - Mitigation recommendations
   - Priority level

**Expected Response:**
The AI provides a comprehensive security analysis with actionable recommendations.

### Scenario 3: Reviewing the Leaderboard

**User Query:**
```
Show me the current leaderboard standings
```

**What Happens:**
1. AI agent reads the `blt://leaderboards` resource
2. Displays formatted leaderboard data

**Expected Result:**
```json
{
  "top_contributors": [
    {
      "rank": 1,
      "username": "security_pro",
      "bacon_points": 1250,
      "contributions": 45
    },
    {
      "rank": 2,
      "username": "bug_hunter",
      "bacon_points": 980,
      "contributions": 32
    }
  ]
}
```

### Scenario 4: Awarding Bacon Points

**User Query:**
```
Award 50 bacon points to contributor 123 for their excellent security analysis
```

**What Happens:**
1. AI agent uses the `award_bacon` tool
2. Awards points with reason

**Expected Result:**
```json
{
  "contributor_id": "123",
  "points_awarded": 50,
  "new_total": 350,
  "reason": "Excellent security analysis"
}
```

### Scenario 5: Managing Issue Workflow

**User Query:**
```
Update issue 789 to resolved status and add a comment explaining the fix
```

**What Happens:**
1. AI agent uses `update_issue_status` tool to mark as resolved
2. AI agent uses `add_comment` tool to add explanation

**Expected Result:**
Issue is updated and comment is added successfully.

### Scenario 6: Planning Remediation

**User Query:**
```
Create a remediation plan for issue 789. The vulnerability is a buffer overflow 
in the authentication module that could lead to remote code execution.
```

**What Happens:**
1. AI agent uses the `plan_remediation` prompt
2. Generates comprehensive plan including:
   - Root cause analysis
   - Step-by-step remediation
   - Testing procedures
   - Prevention measures
   - Timeline estimate

**Expected Response:**
Detailed remediation plan with actionable steps.

### Scenario 7: Reviewing a Contribution

**User Query:**
```
Review contribution 456 - it's a bug report about a memory leak
```

**What Happens:**
1. AI agent uses the `review_contribution` prompt
2. Evaluates quality, completeness, and value
3. Recommends bacon point award

**Expected Response:**
- Quality assessment
- Strengths and improvements
- Recommended bacon points (e.g., 35 points)
- Follow-up actions

## Advanced Usage

### Batch Operations

You can request multiple operations in sequence:

```
1. Submit a new XSS vulnerability for repo 123
2. Check the leaderboard to see current rankings
3. Award 25 bacon points to the top contributor
```

The AI agent will execute each operation in order.

### Querying Specific Resources

Request detailed information about specific resources:

```
Show me details for issue 789
What repositories are currently being tracked?
Get information about contributor 456
```

### Workflow Automation

Create complex workflows combining multiple tools:

```
1. Get all open issues from repo 123
2. For critical issues, create remediation plans
3. Update low-priority issues to triaged status
4. Generate a summary report
```

## Testing the Server

### Manual Testing

You can test the server manually using stdio:

```bash
node dist/index.js
```

Then send JSON-RPC requests via stdin. Example:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "resources/list"
}
```

### Testing with MCP Inspector

Use the MCP Inspector tool to test the server:

```bash
npx @modelcontextprotocol/inspector node dist/index.js
```

This provides a web UI to test all resources, tools, and prompts.

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify `BLT_API_KEY` is set correctly
   - Check that the API key has proper permissions

2. **Connection Issues**
   - Verify `BLT_API_BASE` URL is correct
   - Check network connectivity

3. **Build Errors**
   - Run `npm install` to ensure dependencies are installed
   - Run `npm run build` to compile TypeScript

4. **Server Not Responding**
   - Check that Node.js version is 18 or higher
   - Verify the path to `dist/index.js` is correct

## Best Practices

1. **Security**
   - Never commit `.env` files with real API keys
   - Use environment-specific API keys
   - Regularly rotate API keys

2. **Performance**
   - Be mindful of API rate limits
   - Cache frequently accessed resources when possible
   - Batch operations when appropriate

3. **Error Handling**
   - Always check error responses
   - Provide context in issue descriptions
   - Include relevant details in comments

## Additional Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/)
- [BLT API Documentation](https://blt.owasp.org/api/docs)
