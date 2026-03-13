# BLT-MCP

An MCP (Model Context Protocol) server that provides AI agents and developers with structured access to the BLT (Bug Logging Tool) ecosystem. This server enables seamless integration with IDEs and chat interfaces to log bugs, triage issues, query data, and manage security workflows.

## Overview

BLT-MCP implements the MCP standard, giving AI agents structured access to BLT through three powerful layers:

### 🔗 Resources (blt:// URIs)
Access BLT data through standardized URIs:
- `blt://issues` - All issues in the system
- `blt://issues/{id}` - Specific issue details
- `blt://repos` - Tracked repositories
- `blt://repos/{id}` - Specific repository details
- `blt://contributors` - All contributors
- `blt://contributors/{id}` - Specific contributor details
- `blt://workflows` - All workflows
- `blt://workflows/{id}` - Specific workflow details
- `blt://leaderboards` - Leaderboard rankings and statistics
- `blt://rewards` - Rewards and bacon points

### 🛠️ Tools
Perform actions on BLT:
- **submit_issue** - Report new bugs and vulnerabilities
- **award_bacon** - Award bacon points to contributors (gamification)
- **update_issue_status** - Change issue status (open, in_progress, resolved, closed, wont_fix)
- **add_comment** - Add comments to issues

### 💡 Prompts
AI-guided workflows for common security tasks:
- **triage_vulnerability** - Guide AI through vulnerability triage and severity assessment
- **plan_remediation** - Create comprehensive remediation plans for security issues
- **review_contribution** - Evaluate contributions with quality assessment and bacon point recommendations

## Features

- ✅ **JSON-RPC 2.0** - Standard protocol for reliable communication
- ✅ **OAuth/API Key Authentication** - Secure access to BLT endpoints
- ✅ **Unified Interface** - Single agent-friendly interface to all BLT functionality
- ✅ **Autonomous Workflows** - Enable AI agents to work independently
- ✅ **Gamification Support** - Built-in support for BLT's bacon point system
- ✅ **Security-First** - Designed for vulnerability management and security workflows

## Installation

### Prerequisites
- Node.js 18 or higher
- npm or yarn

### Install Dependencies

```bash
npm install
```

### Build

```bash
npm run build
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Configure the following variables:

```env
BLT_API_BASE=https://blt.owasp.org/api
BLT_API_KEY=your_api_key_here
```

### MCP Client Configuration

To use this server with an MCP client (like Claude Desktop or Cline), add it to your MCP settings:

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

## Usage

### Running the Server

The server runs using stdio transport for MCP communication:

```bash
node dist/index.js
```

### Using with AI Agents

Once configured in your MCP client, you can interact with BLT through natural language:

#### Example: Submitting an Issue
```
"Submit a new critical vulnerability in the authentication system of repo 123"
```

The AI agent will use the `submit_issue` tool to create the issue.

#### Example: Accessing Resources
```
"Show me the leaderboard"
```

The AI agent will read from `blt://leaderboards` to display the rankings.

#### Example: Using Prompts
```
"Help me triage this XSS vulnerability in the login form"
```

The AI agent will use the `triage_vulnerability` prompt to guide the analysis.

## API Reference

### Resources

#### List All Issues
```
URI: blt://issues
Returns: JSON array of all issues
```

#### Get Specific Issue
```
URI: blt://issues/{id}
Returns: JSON object with issue details
```

#### Leaderboards
```
URI: blt://leaderboards
Returns: JSON object with leaderboard data
```

### Tools

#### submit_issue
Submit a new issue to BLT.

**Parameters:**
- `title` (string, required) - Issue title
- `description` (string, required) - Detailed description
- `repo_id` (string, optional) - Repository ID
- `severity` (string, optional) - One of: low, medium, high, critical
- `type` (string, optional) - One of: bug, vulnerability, feature, other

**Example:**
```json
{
  "title": "XSS vulnerability in login form",
  "description": "The login form is vulnerable to reflected XSS...",
  "repo_id": "123",
  "severity": "high",
  "type": "vulnerability"
}
```

#### award_bacon
Award bacon points to a contributor.

**Parameters:**
- `contributor_id` (string, required) - Contributor ID
- `points` (number, required) - Points to award
- `reason` (string, required) - Reason for the award

#### update_issue_status
Update the status of an issue.

**Parameters:**
- `issue_id` (string, required) - Issue ID
- `status` (string, required) - One of: open, in_progress, resolved, closed, wont_fix
- `comment` (string, optional) - Explanation for status change

#### add_comment
Add a comment to an issue.

**Parameters:**
- `issue_id` (string, required) - Issue ID
- `comment` (string, required) - Comment text

### Prompts

#### triage_vulnerability
Guides AI through vulnerability triage.

**Arguments:**
- `vulnerability_description` (required) - Description of the vulnerability
- `affected_component` (optional) - Affected component or system

#### plan_remediation
Creates remediation plans for security issues.

**Arguments:**
- `issue_id` (required) - Issue ID to create plan for
- `context` (optional) - Additional context

#### review_contribution
Evaluates security contributions.

**Arguments:**
- `contribution_id` (required) - Contribution ID
- `contribution_type` (optional) - Type of contribution

## JSON-RPC Example

Since BLT-MCP uses JSON-RPC 2.0 over stdio, below is an example request and response format.

### Example: Calling submit_issue Tool

Request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "submit_issue",
    "arguments": {
      "title": "Test issue from JSON-RPC",
      "description": "This is a test issue created via raw JSON-RPC request.",
      "severity": "low"
    }
  }
}
```

Example Response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": true,
    "message": "Issue submitted successfully"
  }
}
```

## Troubleshooting

### Node Version
Ensure you are running Node.js v18 or higher:

```bash
node -v
```

### Missing Environment Variables
Make sure `.env` is properly configured:

```
BLT_API_BASE=https://blt.owasp.org/api
BLT_API_KEY=your_api_key_here
```

### Build Issues
If `dist/index.js` is missing, run:

```bash
npm run build
```

## Development

### Watch Mode

For development, use watch mode to automatically rebuild on changes:

```bash
npm run watch
```

### Project Structure

```
blt-mcp/
├── src/
│   └── index.ts          # Main server implementation
├── dist/                 # Compiled JavaScript (generated)
├── package.json          # Project dependencies
├── tsconfig.json         # TypeScript configuration
├── .env.example          # Example environment configuration
└── mcp-config.json       # Example MCP client configuration
```

## Security Considerations

- **API Keys**: Never commit API keys to version control. Use environment variables.
- **Access Control**: Ensure proper authentication is configured for production use.
- **Rate Limiting**: Be mindful of API rate limits when making requests.
- **Input Validation**: The server validates all inputs before sending to the BLT API.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions, please visit:
- GitHub: https://github.com/OWASP-BLT/BLT-MCP
- OWASP BLT: https://owasp.org/www-project-bug-logging-tool/

## Acknowledgments

- Built on the [Model Context Protocol](https://modelcontextprotocol.io/)
- Part of the [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/)
- Powered by the security community
