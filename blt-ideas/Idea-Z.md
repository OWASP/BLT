# Idea Z — BLT-MCP: Model Context Protocol Server for Complete BLT Interface

## One line

A Model Context Protocol (MCP) server that provides comprehensive, AI-agent-friendly access to all aspects of BLT including issues, repos, contributions, rewards, and workflows.

---

## Problem & personas

- **AI Agent Developer Alice** wants to build AI assistants that can query BLT data, submit vulnerability reports, and track contributor progress without parsing HTML or reverse-engineering APIs.
- **Automation Engineer Alex** needs programmatic access to BLT's full feature set (issues, repos, rewards, workflows) in a standardized format that AI tools understand.
- **Third-Party Integration Teams** want to connect external tools (IDEs, dashboards, notification systems) to BLT using a modern, LLM-friendly protocol.

Today, integrating with BLT programmatically requires:
1. Manual API discovery and REST endpoint documentation
2. Custom parsers for different data formats
3. No standardized way for AI agents to discover available actions
4. Fragmented access: some features via GraphQL, others via REST, some only through UI

**BLT-MCP** solves this by implementing the **Model Context Protocol** — an open standard that allows AI assistants (Claude Desktop, custom agents, automation tools) to seamlessly interact with BLT as if it were a native capability. MCP provides **resource reading** (issues, repos, contributions), **tool invocation** (create issues, award BACON, update workflows), and **prompt templates** (common BLT tasks) in a standardized, discoverable format.

---

## Core idea

A **comprehensive MCP server** that exposes BLT's entire feature set through a unified, AI-agent-friendly interface:

### 1. Resources (read-only data access)

MCP resources provide structured, contextual data that AI agents can query:

- `blt://issues/{id}` — Issue details, comments, linked PRs, status
- `blt://repos/{owner}/{name}` — Repository metadata, stats, verification status
- `blt://contributors/{id}` — Profile, reputation, badges, BACON balance, contribution history
- `blt://workflows/{id}` — Workflow state, steps, blockers, progress
- `blt://leaderboards/{category}` — Rankings (top contributors, repos, organizations)
- `blt://rewards/{id}` — Reward details, eligibility, claim status
- `blt://campaigns/{id}` — Active campaigns, goals, participation
- `blt://adventures/{id}` — Education tracks, labs, progress

### 2. Tools (actions agents can invoke)

MCP tools allow AI agents to perform actions:

- `submit_issue` — Create new vulnerability report with metadata (severity, type, description)
- `update_issue_status` — Change issue state (open, in-progress, verified, closed)
- `award_bacon` — Grant BACON rewards to contributors (with justification)
- `create_workflow` — Initialize a new workflow (e.g., disclosure, remediation)
- `add_comment` — Post comment to issue or PR
- `register_contribution` — Log contributor activity (PR merged, review completed)
- `enroll_in_campaign` — Join security campaign
- `claim_reward` — Claim eligible reward
- `get_recommendations` — AI-powered suggestions (next issues, learning tracks, similar patterns)

### 3. Prompts (reusable task templates)

MCP prompts provide pre-built workflows for common BLT tasks:

- `triage_vulnerability` — Guide agent through assessing and categorizing a new report
- `plan_remediation` — Generate remediation plan for verified issue
- `review_contribution` — Structured review of contributor PR or issue fix
- `assign_rewards` — Calculate and award appropriate BACON/badges based on contribution
- `find_similar_issues` — Search for related vulnerabilities or patterns
- `generate_disclosure_summary` — Create responsible disclosure summary for maintainer

---

## Technical architecture

### MCP Server Implementation

```text
BLT-MCP Server (Python, hosted alongside BLT Django backend)
  ├── Resources Layer
  │   ├── Issue Provider (queries Django ORM, returns structured issue data)
  │   ├── Repo Provider (aggregates repo stats, verification status)
  │   ├── Contributor Provider (profile, reputation, history)
  │   └── Workflow Provider (workflow state machine queries)
  │
  ├── Tools Layer
  │   ├── Issue Management (create, update, comment)
  │   ├── Rewards System (award BACON, badges)
  │   ├── Workflow Actions (state transitions)
  │   └── AI Recommendations (integration with existing BLT AI features)
  │
  ├── Prompts Layer
  │   ├── Template Library (pre-built workflows)
  │   └── Context Injection (pull relevant BLT data into prompts)
  │
  └── Authentication & Authorization
      ├── OAuth 2.0 / API Key support
      ├── Permission scoping (read-only, contributor, maintainer, admin)
      └── Rate limiting and audit logging
```

### Protocol Details

MCP uses **JSON-RPC 2.0** over stdio (local) or HTTP/SSE (remote). The server implements:

1. **Capabilities negotiation** — Client discovers what resources/tools are available
2. **Resource URIs** — Standardized `blt://` scheme for addressing BLT entities
3. **Tool schemas** — JSON Schema definitions for each tool's inputs/outputs
4. **Prompt templates** — Pre-built workflows with parameter injection
5. **Streaming support** — Real-time updates for long-running operations (e.g., workflow progress)

---

## Data model (MCP interface layer)

**No new database tables.** BLT-MCP is a **presentation layer** that exposes existing Django models through MCP protocol.

### Resource schemas (examples)

```typescript
// blt://issues/{id}
interface IssueResource {
  uri: string;  // "blt://issues/12345"
  mimeType: "application/json";
  text: string; // JSON serialization
  content: {
    id: number;
    title: string;
    description: string;
    severity: "critical" | "high" | "medium" | "low";
    status: "open" | "in-progress" | "verified" | "closed";
    reporter: ContributorRef;
    assignee?: ContributorRef;
    repo: RepoRef;
    created_at: string;
    updated_at: string;
    comments: Comment[];
    linked_prs: PR[];
    tags: string[];
  };
}

// blt://contributors/{id}
interface ContributorResource {
  uri: string;
  mimeType: "application/json";
  content: {
    id: number;
    username: string;
    reputation_score: number;
    bacon_balance: number;
    badges: Badge[];
    contributions: {
      issues_reported: number;
      prs_merged: number;
      reviews_completed: number;
    };
    active_campaigns: CampaignRef[];
    learning_progress: AdventureProgress[];
  };
}
```

### Tool schemas (examples)

```typescript
// submit_issue tool
interface SubmitIssueTool {
  name: "submit_issue";
  description: "Submit a new vulnerability report to BLT";
  inputSchema: {
    type: "object";
    properties: {
      repo: { type: "string"; description: "owner/repo" };
      title: { type: "string" };
      description: { type: "string" };
      severity: { enum: ["critical", "high", "medium", "low"] };
      vulnerability_type: { type: "string"; example: "XSS" };
      proof_of_concept: { type: "string"; optional: true };
    };
    required: ["repo", "title", "description", "severity"];
  };
}

// award_bacon tool
interface AwardBaconTool {
  name: "award_bacon";
  description: "Award BACON rewards to a contributor";
  inputSchema: {
    type: "object";
    properties: {
      contributor_id: { type: "number" };
      amount: { type: "number"; minimum: 1 };
      reason: { type: "string" };
      issue_id: { type: "number"; optional: true };
    };
    required: ["contributor_id", "amount", "reason"];
  };
}
```

---

## API surface

MCP servers don't expose traditional REST endpoints. Instead, they implement JSON-RPC methods:

### Initialization & Capabilities

- `initialize` — Negotiate protocol version, capabilities
- `initialized` — Confirm handshake complete

### Resources

- `resources/list` — List available resources (optionally filtered)
- `resources/read` — Read specific resource by URI
- `resources/templates` — Discover resource URI patterns

### Tools

- `tools/list` — List all available tools with schemas
- `tools/call` — Invoke a tool with arguments

### Prompts

- `prompts/list` — List available prompt templates
- `prompts/get` — Fetch prompt template with injected context

### Sampling (optional)

- `sampling/createMessage` — Request LLM completion (if BLT-MCP acts as orchestrator)

Auth: OAuth 2.0 bearer tokens or API keys passed via MCP session metadata.

---

## UX flows

### AI agent creating a vulnerability report

```
User: "Submit an XSS issue for acme/webapp: stored XSS in profile bio field"

Agent (via MCP):
1. Call resources/read("blt://repos/acme/webapp") → verify repo exists
2. Call tools/call("submit_issue", {
     repo: "acme/webapp",
     title: "Stored XSS in profile bio field",
     description: "...",
     severity: "high",
     vulnerability_type: "XSS"
   })
3. Receive issue_id: 98765
4. Respond: "Created issue #98765: https://blt.owasp.org/issue/98765"
```

### Claude Desktop querying contributor stats

```
User: "Show me the top 5 contributors this month"

Claude (via BLT-MCP):
1. Call resources/read("blt://leaderboards/monthly") → get rankings
2. For each top contributor:
   Call resources/read("blt://contributors/{id}") → get details
3. Format and display: names, BACON earned, contributions, badges
```

### Automation tool tracking workflow progress

```
Automation (via MCP):
1. Subscribe to resource updates: resources/subscribe("blt://workflows/456")
2. Receive real-time updates as workflow progresses
3. On "verified" state: Call tools/call("award_bacon", {...})
4. On "closed" state: Unsubscribe from updates
```

---

## Integration examples

### Claude Desktop integration

Users install BLT-MCP server locally:

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "blt": {
      "command": "blt-mcp",
      "args": ["--api-key", "your-key"],
      "env": {
        "BLT_BASE_URL": "https://blt.owasp.org"
      }
    }
  }
}
```

Now Claude can naturally interact with BLT:
- "What are the open critical issues in OWASP/BLT?"
- "Award 50 BACON to contributor #123 for fixing CVE-2025-1234"
- "Show me my contribution history"

### Custom AI agent

```python
from mcp.client import MCPClient

client = MCPClient("http://blt.owasp.org/mcp")
await client.initialize()

# Query resources
issue = await client.read_resource("blt://issues/12345")

# Invoke tools
result = await client.call_tool("update_issue_status", {
    "issue_id": 12345,
    "new_status": "verified",
    "comment": "Confirmed and verified by security team"
})

# Use prompts
remediation = await client.get_prompt("plan_remediation", {
    "issue_id": 12345
})
```

### Third-party dashboard

Dashboard tool connects to BLT-MCP to display real-time security metrics:

```javascript
const mcp = new MCPClient({ url: 'https://blt.owasp.org/mcp', apiKey: '...' });

// Fetch leaderboard data
const topRepos = await mcp.readResource('blt://leaderboards/repos');
const topContributors = await mcp.readResource('blt://leaderboards/contributors');

// Subscribe to live updates
mcp.subscribe('blt://leaderboards/repos', (updated) => {
  dashboard.refresh(updated);
});
```

---

## Development program scope (350h)

**Must-have (MVP):**

- MCP server implementation (Python, integrated with Django backend).
- Core resources: issues, repos, contributors, workflows (read-only).
- Core tools: submit_issue, update_issue_status, add_comment, award_bacon (write operations).
- Authentication layer: OAuth 2.0 + API key support with permission scoping.
- Resource URI scheme: `blt://` with proper routing and validation.
- Tool schema definitions: JSON Schema for all tool inputs/outputs.
- Basic prompt templates: triage_vulnerability, review_contribution (2-3 templates).
- Documentation: integration guide for Claude Desktop, custom agents, API reference.
- Tests: resource providers, tool invocations, auth/authz (~75%+ coverage).

**Nice-to-have (stretch):**

- Real-time subscriptions: SSE-based updates for workflows, leaderboards.
- Advanced prompts: plan_remediation, find_similar_issues (5+ templates).
- Sampling API: allow BLT-MCP to act as LLM orchestrator for complex workflows.
- CLI tool: `blt-mcp-cli` for testing and debugging (e.g., `blt-mcp-cli read blt://issues/123`).
- Python SDK: high-level client library for common MCP operations.

---

## Evaluation metrics (for development program)

- **Adoption:** ≥10 users integrate BLT-MCP with Claude Desktop or custom agents during pilot.
- **Coverage:** ≥80% of core BLT features accessible via MCP (issues, repos, contributors, rewards, workflows).
- **Usefulness:** Developer rating ≥4/5 on "MCP integration was easier than using REST APIs directly."
- **Reliability:** ≥99% uptime for MCP endpoints; <200ms p95 latency for resource reads.

---

## Pros / cons

**Pros**

- Positions BLT as AI-agent-first platform; natural integration with Claude, Cursor, and other MCP-enabled tools.
- Standardized protocol: no custom API documentation burden; AI agents discover capabilities automatically.
- Future-proof: MCP is backed by Anthropic and gaining ecosystem adoption; early implementation gives BLT first-mover advantage.
- Unifies fragmented access: one protocol for all BLT features (issues, repos, rewards, workflows).
- Enables novel use cases: AI agents that triage issues, award rewards, track workflows autonomously.

**Cons**

- MCP is relatively new protocol (2024); ecosystem still maturing (mitigated by strong Anthropic backing).
- Requires developers to learn MCP concepts (resources, tools, prompts) vs. familiar REST (mitigated by excellent docs).
- Potential for AI agent abuse (e.g., spam issue creation) — requires robust rate limiting and permission controls.
- Maintenance burden: must keep MCP server in sync with Django model changes (mitigated by clear abstraction layer).

---

## Why it fits development program

- Clear, standalone scope: MCP server + resource providers + tool implementations + auth + docs.
- 350h is sufficient for MVP: core resources/tools, OAuth integration, prompt templates, and pilot testing.
- Aligns with Discussion #5495: makes BLT more accessible to developers and AI agents; lowers integration barrier.
- Strategic positioning: early MCP adoption positions BLT as leading-edge, AI-friendly security platform.

---

## Integration points

- **BLT backend:** MCP server runs as Django app (or separate microservice) with access to Django ORM.
- **Authentication:** Reuses existing BLT OAuth 2.0 + session auth; adds API key support for agents.
- **Claude Desktop:** Users install local BLT-MCP client that proxies to BLT production.
- **Custom agents:** Developers use MCP client libraries (Python, JS) to build BLT-aware agents.
- **Webhooks:** Optional bidirectional integration (BLT events → MCP notifications, MCP actions → BLT webhooks).

---

## Related ideas

- **Synergy with Idea N (RAG AI Bot):** BLT-MCP can expose bot capabilities as MCP tools (e.g., `ask_security_question`).
- **Synergy with Idea H (BLT Growth):** MCP can surface AI-guided recommendations as prompts (`get_next_issue_recommendation`).
- **Synergy with Idea F (Reputation Graph):** Trust scores accessible via `blt://contributors/{id}/reputation`.
- **Synergy with Idea B (Gamification):** Rewards/badges/leaderboards as MCP resources; award actions as tools.

---

_Last Updated: February 2026_
