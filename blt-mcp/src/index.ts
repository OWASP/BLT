#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// BLT API configuration
const BLT_API_BASE = process.env.BLT_API_BASE || "https://blt.owasp.org/api";
const BLT_API_KEY = process.env.BLT_API_KEY || "";

// Types for API requests and responses
interface ApiRequestBody {
  [key: string]: unknown;
}

interface ApiResponse {
  [key: string]: unknown;
}

// Helper function to make authenticated API requests
async function makeApiRequest(
  endpoint: string,
  method: string = "GET",
  body?: ApiRequestBody
): Promise<ApiResponse> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (BLT_API_KEY) {
    headers["Authorization"] = `Bearer ${BLT_API_KEY}`;
  }

  const options: RequestInit = {
    method,
    headers,
  };

  if (body && method !== "GET") {
    options.body = JSON.stringify(body);
  }

  const url = `${BLT_API_BASE}${endpoint}`;
  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Create the MCP server
const server = new Server(
  {
    name: "blt-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      resources: {},
      tools: {},
      prompts: {},
    },
  }
);

// ============================================================================
// RESOURCES - blt:// URIs for accessing BLT data
// ============================================================================

server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: "blt://issues",
        name: "BLT Issues",
        description: "List all issues in the BLT system",
        mimeType: "application/json",
      },
      {
        uri: "blt://issues/{id}",
        name: "BLT Issue by ID",
        description: "Get details for a specific issue by ID",
        mimeType: "application/json",
      },
      {
        uri: "blt://repos",
        name: "BLT Repositories",
        description: "List all repositories tracked in BLT",
        mimeType: "application/json",
      },
      {
        uri: "blt://repos/{id}",
        name: "BLT Repository by ID",
        description: "Get details for a specific repository by ID",
        mimeType: "application/json",
      },
      {
        uri: "blt://contributors",
        name: "BLT Contributors",
        description: "List all contributors in the BLT system",
        mimeType: "application/json",
      },
      {
        uri: "blt://contributors/{id}",
        name: "BLT Contributor by ID",
        description: "Get details for a specific contributor by ID",
        mimeType: "application/json",
      },
      {
        uri: "blt://workflows",
        name: "BLT Workflows",
        description: "List all workflows in the BLT system",
        mimeType: "application/json",
      },
      {
        uri: "blt://workflows/{id}",
        name: "BLT Workflow by ID",
        description: "Get details for a specific workflow by ID",
        mimeType: "application/json",
      },
      {
        uri: "blt://leaderboards",
        name: "BLT Leaderboards",
        description: "View leaderboard rankings and statistics",
        mimeType: "application/json",
      },
      {
        uri: "blt://rewards",
        name: "BLT Rewards",
        description: "List all rewards and bacon points",
        mimeType: "application/json",
      },
    ],
  };
});

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const uri = request.params.uri;
  const match = uri.match(/^blt:\/\/([^\/]+)(?:\/(.+))?$/);

  if (!match) {
    throw new Error(`Invalid BLT URI: ${uri}`);
  }

  const [, resourceType, resourceId] = match;

  try {
    let data: ApiResponse;

    switch (resourceType) {
      case "issues":
        if (resourceId) {
          data = await makeApiRequest(`/issues/${resourceId}`);
        } else {
          data = await makeApiRequest("/issues");
        }
        break;

      case "repos":
        if (resourceId) {
          data = await makeApiRequest(`/repos/${resourceId}`);
        } else {
          data = await makeApiRequest("/repos");
        }
        break;

      case "contributors":
        if (resourceId) {
          data = await makeApiRequest(`/contributors/${resourceId}`);
        } else {
          data = await makeApiRequest("/contributors");
        }
        break;

      case "workflows":
        if (resourceId) {
          data = await makeApiRequest(`/workflows/${resourceId}`);
        } else {
          data = await makeApiRequest("/workflows");
        }
        break;

      case "leaderboards":
        data = await makeApiRequest("/leaderboards");
        break;

      case "rewards":
        data = await makeApiRequest("/rewards");
        break;

      default:
        throw new Error(`Unknown resource type: ${resourceType}`);
    }

    return {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify(data, null, 2),
        },
      ],
    };
  } catch (error) {
    throw new Error(
      `Failed to read resource ${uri}: ${error instanceof Error ? error.message : String(error)}`
    );
  }
});

// ============================================================================
// TOOLS - Actions that can be performed on BLT
// ============================================================================

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "submit_issue",
        description:
          "Submit a new issue to the BLT system. Use this to report bugs, vulnerabilities, or other issues.",
        inputSchema: {
          type: "object",
          properties: {
            title: {
              type: "string",
              description: "The title of the issue",
            },
            description: {
              type: "string",
              description: "Detailed description of the issue",
            },
            repo_id: {
              type: "string",
              description: "The repository ID where the issue was found",
            },
            severity: {
              type: "string",
              enum: ["low", "medium", "high", "critical"],
              description: "The severity level of the issue",
            },
            type: {
              type: "string",
              enum: ["bug", "vulnerability", "feature", "other"],
              description: "The type of issue",
            },
          },
          required: ["title", "description"],
        },
      },
      {
        name: "award_bacon",
        description:
          "Award bacon points to a contributor for their contribution. This is part of BLT's gamification system.",
        inputSchema: {
          type: "object",
          properties: {
            contributor_id: {
              type: "string",
              description: "The ID of the contributor to award",
            },
            points: {
              type: "number",
              description: "The number of bacon points to award",
            },
            reason: {
              type: "string",
              description: "The reason for awarding the bacon points",
            },
          },
          required: ["contributor_id", "points", "reason"],
        },
      },
      {
        name: "update_issue_status",
        description:
          "Update the status of an existing issue in the BLT system.",
        inputSchema: {
          type: "object",
          properties: {
            issue_id: {
              type: "string",
              description: "The ID of the issue to update",
            },
            status: {
              type: "string",
              enum: ["open", "in_progress", "resolved", "closed", "wont_fix"],
              description: "The new status for the issue",
            },
            comment: {
              type: "string",
              description: "Optional comment explaining the status change",
            },
          },
          required: ["issue_id", "status"],
        },
      },
      {
        name: "add_comment",
        description: "Add a comment to an existing issue in the BLT system.",
        inputSchema: {
          type: "object",
          properties: {
            issue_id: {
              type: "string",
              description: "The ID of the issue to comment on",
            },
            comment: {
              type: "string",
              description: "The comment text to add",
            },
          },
          required: ["issue_id", "comment"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (!args) {
    return {
      content: [
        {
          type: "text",
          text: "Error: Missing required arguments",
        },
      ],
      isError: true,
    };
  }

  try {
    switch (name) {
      case "submit_issue": {
        const result = await makeApiRequest("/issues", "POST", {
          title: args.title,
          description: args.description,
          repo_id: args.repo_id,
          severity: args.severity || "medium",
          type: args.type || "bug",
        });

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "award_bacon": {
        const result = await makeApiRequest("/rewards", "POST", {
          contributor_id: args.contributor_id,
          points: args.points,
          reason: args.reason,
        });

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "update_issue_status": {
        const result = await makeApiRequest(
          `/issues/${args.issue_id}`,
          "PATCH",
          {
            status: args.status,
            comment: args.comment,
          }
        );

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "add_comment": {
        const result = await makeApiRequest(
          `/issues/${args.issue_id}/comments`,
          "POST",
          {
            comment: args.comment,
          }
        );

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

// ============================================================================
// PROMPTS - AI guidance for common workflows
// ============================================================================

server.setRequestHandler(ListPromptsRequestSchema, async () => {
  return {
    prompts: [
      {
        name: "triage_vulnerability",
        description:
          "Guides the AI through triaging a vulnerability report, including severity assessment and initial recommendations.",
        arguments: [
          {
            name: "vulnerability_description",
            description: "Description of the reported vulnerability",
            required: true,
          },
          {
            name: "affected_component",
            description: "The component or system affected by the vulnerability",
            required: false,
          },
        ],
      },
      {
        name: "plan_remediation",
        description:
          "Helps plan remediation steps for a confirmed security issue.",
        arguments: [
          {
            name: "issue_id",
            description: "The ID of the issue to create a remediation plan for",
            required: true,
          },
          {
            name: "context",
            description: "Additional context about the issue",
            required: false,
          },
        ],
      },
      {
        name: "review_contribution",
        description:
          "Guides the review of a security contribution, including quality assessment and bacon point recommendations.",
        arguments: [
          {
            name: "contribution_id",
            description: "The ID of the contribution to review",
            required: true,
          },
          {
            name: "contribution_type",
            description: "The type of contribution (e.g., bug report, fix, documentation)",
            required: false,
          },
        ],
      },
    ],
  };
});

server.setRequestHandler(GetPromptRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "triage_vulnerability": {
      const vulnerabilityDesc = args?.vulnerability_description || "";
      const affectedComponent = args?.affected_component || "unspecified component";

      return {
        messages: [
          {
            role: "user",
            content: {
              type: "text",
              text: `You are a security expert helping to triage a vulnerability report. Please analyze the following vulnerability and provide:

1. Severity Assessment (Critical/High/Medium/Low)
2. Potential Impact Analysis
3. Affected Systems/Components
4. Immediate Mitigation Recommendations
5. Suggested Priority Level

Vulnerability Description:
${vulnerabilityDesc}

Affected Component: ${affectedComponent}

Please provide a structured analysis with clear, actionable recommendations.`,
            },
          },
        ],
      };
    }

    case "plan_remediation": {
      const issueId = args?.issue_id || "";
      const context = args?.context || "";

      return {
        messages: [
          {
            role: "user",
            content: {
              type: "text",
              text: `You are a security expert creating a remediation plan for issue #${issueId}. Please provide:

1. Root Cause Analysis
2. Step-by-Step Remediation Plan
3. Testing and Verification Steps
4. Prevention Measures for Future
5. Estimated Timeline and Resources

${context ? `Additional Context:\n${context}\n` : ""}
Please create a comprehensive, actionable remediation plan that can be followed by the development team.`,
            },
          },
        ],
      };
    }

    case "review_contribution": {
      const contributionId = args?.contribution_id || "";
      const contributionType = args?.contribution_type || "contribution";

      return {
        messages: [
          {
            role: "user",
            content: {
              type: "text",
              text: `You are reviewing a security contribution (ID: ${contributionId}, Type: ${contributionType}). Please evaluate:

1. Quality and Accuracy of the ${contributionType}
2. Completeness of Information
3. Technical Depth and Insight
4. Value to the Security Community
5. Recommended Bacon Points (1-100 scale)

Please provide a thorough review with:
- Strengths of the contribution
- Areas for improvement (if any)
- Recommended bacon point award with justification
- Any follow-up actions needed

Be constructive and encouraging while maintaining high standards for security contributions.`,
            },
          },
        ],
      };
    }

    default:
      throw new Error(`Unknown prompt: ${name}`);
  }
});

// ============================================================================
// Start the server
// ============================================================================

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  // Log to stderr since stdout is used for MCP communication
  console.error("BLT-MCP server running on stdio");
  console.error(`BLT API Base: ${BLT_API_BASE}`);
  console.error(`API Key configured: ${BLT_API_KEY ? "Yes" : "No"}`);
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
