# AI Agent Guide for BLT-MCP

This guide explains how to interact with the OWASP Bug Logging Tool (BLT) ecosystem using the **`blt-mcp`** Model Context Protocol (MCP) server. Use these tools, resources, and prompts to help users find, triage, report, and remediate security vulnerabilities.

---

## 1. Available Resources (`blt://`)

You can read structured JSON data from the BLT ecosystem using the following URIs:

- **`blt://v2/bugs`** - Retrieves the list of all active bug reports and vulnerabilities.
- **`blt://v2/bugs/{id}`** - Fetches detailed info for a specific bug, including screenshots, OCR text, and user comments.
- **`blt://v2/repos`** - Lists all tracked repositories registered in the BLT platform.
- **`blt://v2/repos/{id}`** - Fetches details for a specific repository.
- **`blt://v2/stats`** - Retrieves global platform stats (total bugs, active repos, bacon points).
- **`blt://v2/leaderboard`** - Fetches the global contributor leaderboard rankings.

---

## 2. Executable Tools

You can perform actions on the BLT platform by calling the following MCP tools:

### `submit_issue`

Submit a new bug or security vulnerability to the OWASP BLT database. This is a write operation and is blocked unless `confirmed` is `true`.

- **Arguments**:
  - `url` (string, required): The target URL of the vulnerability.
  - `title` (string, required): Title of the bug.
  - `description` (string, required): Detailed description of the vulnerability.
  - `severity` (string, optional): Severity level, e.g. `Critical`, `High`, `Medium`, or `Low` (lowercased before sending).
  - `bug_type` (string, optional): Type of bug (e.g. `SQLi`, `XSS`, `IDOR`).
  - `steps_to_reproduce` (string, optional): Numbered steps to reproduce the issue.
  - `labels` (list of strings, optional): Labels to apply, e.g. `["bug", "security"]`.
  - `assignee` (string, optional): Username of the assignee.
  - `confirmed` (boolean, optional, default `false`): Must be `true` to run the write. See [Confirmation](#confirmation-for-write-tools).
- **Returns**: `Successfully submitted issue for <url> (ID: <id>)`. API errors are raised as `Error executing tool submit_issue: API Error <status>: <body>`.

### `triage_vulnerability`

Analyze a vulnerability description using Cloudflare Workers AI (Llama 3.1) to automatically determine class, severity, and mitigation steps. Read-only: it does not change anything in BLT.

- **Arguments**:
  - `prompt` (string, required): Contextual description of the issue to analyze.
- **Returns**: The model's analysis, starting with a severity suggestion followed by a recommendation. An incomplete (truncated) model response is raised as an error.
- **Requires**: `CF_ACCOUNT_ID` and `CF_API_TOKEN` in the server environment (`.env`). The model can be overridden with `CF_MODEL`. Without the credentials the call fails with a `Missing Cloudflare credentials` error.

### `summarize_issue_context`

Retrieve an issue and return a structured plain-text summary, including comments when the issue payload carries them (the BLT API has no comments endpoint). Read-only: it does not need `confirmed`.

- **Arguments**:
  - `issue_id` (string, required): ID of the issue to summarize. IDs containing `/`, `?`, `#` or `&` are rejected.
- **Returns**: Text with `Issue ID`, `Title`, `Status`, `Description` and `Comments` (one `- <author>: <text>` line per comment). If the issue payload has no comments field it says `Comments unavailable (not supported).`; with an empty list it says `No comments.`. A missing or invalid issue is returned as a string starting with `Error:` rather than raised.

### `draft_vision_issue`

Analyze a local screenshot with Cloudflare Vision AI and draft an issue report from it. It only returns draft text (exactly a `TITLE:` line followed by a `DESCRIPTION:` section); it does not submit anything. Pass the result to `submit_issue` yourself once the user has reviewed it.

- **Arguments**:
  - `image_path` (string, required): Path to the screenshot on the machine running the MCP server. It must be a `.png`, `.jpg`, `.jpeg`, `.gif` or `.webp` file of at most 10 MB, located under `BLT_APPROVED_ROOT` (defaults to the server's working directory), `~/.blt-mcp`, or the system temp directory.
  - `context` (string, optional): Hints or background about the screenshot.
- **Returns**: Plain text in the form `TITLE: <title>\nDESCRIPTION: <description>`. When no clear issue is visible it returns the fallback `TITLE: No clear issue identified`. Output that does not follow this format is raised as an error rather than returned.
- **Requires**: `CF_ACCOUNT_ID` and `CF_API_TOKEN` in the server environment. The model can be overridden with `CF_VISION_MODEL`. Invalid paths and missing credentials raise errors.

### Other tools (v2 API)

These tools are also registered. Arguments marked `?` are optional. Every tool in the first list takes `confirmed` (default `false`) and requires `confirmed=true`; see [Confirmation](#confirmation-for-write-tools).

- `auth_signup(email, password, username)`
- `create_bug(url, title, description, repo_id?, labels?, assignee?)`, `update_bug(id, title?, description?, status?)`
- `create_user(username, email, password, profile_info?)`
- `create_job(title, description, company, location?)`, `update_job(id, title?, description?, company?, location?)`, `record_job_view(id)`
- `create_hackathon(name, description, start_date?, end_date?)`, `update_hackathon(id, name?, description?)`, `register_hackathon_participant(id, user_id)`

`auth_signin(email, password)` does not take `confirmed`.

### Confirmation for write tools

Write tools take `confirmed` (boolean, default `false`). Called without `confirmed=true`, they do nothing and raise `Write operation requires confirmation. Please set 'confirmed': true to proceed.` Ask the user before retrying with `confirmed=true`. Write calls are tagged as AI-generated with `X-AI-Generated`, `X-AI-Source` and `X-AI-Timestamp` headers; every write tool except `submit_issue` also sends a `metadata` field in the request body.

---

## 3. Prompts & Workflows

You can load structured prompt templates to guide your interaction with the user:

- **`triage_vulnerability`**: Helps you gather necessary context to perform initial severity assessment and vulnerability class mapping.
- **`plan_remediation`**: Guides you in drafting a detailed step-by-step remediation and patching plan for a specific security finding.
- **`review_contribution`**: Helps you evaluate pull requests, code contributions, or bug reports, and recommend gamified "Bacon Point" awards.

---

## 4. Best Practices for AI Agents

1.  **Authentication Reality & Key Types**: 
    *   **Public Showcase Key**: If `BLT_API_KEY` is not explicitly set, the MCP server automatically falls back to a **static public showcase API key**. This key provides access to public read-only endpoints (such as `blt://v2/bugs`, `blt://v2/repos`, and `blt://v2/stats`).
    *   **User API Key (`blt_live_...`) Required for Jobs & Hackathons**: The backend BLT-API strictly requires a user-owned API key (`blt_live_...` associated with an active account) for **all jobs and hackathons endpoints**, including read resources (`blt://v2/jobs`, `blt://v2/jobs/stats`, `blt://v2/hackathons`, `blt://v2/hackathons/{slug}`) and mutation tools (`create_job`, `update_job`, `record_job_view`, `create_hackathon`, `update_hackathon`, `register_hackathon_participant`).
    *   **Handling 401 Unauthorized**: Calling jobs or hackathons endpoints using the showcase key returns `401 Unauthorized: User API key required`. **Do not repeatedly retry these tools or resources** if operating under the showcase key. Inform the user that a personal user key is required, which can be configured via:
        ```bash
        uv run -m blt_mcp.cli auth login
        ```
        or by setting `BLT_API_KEY=blt_live_...` in the `.env` configuration.
2.  **Rate Limiting**:
    Be mindful of high-volume queries. Group your requests or reuse fetched resource data when performing bulk triage tasks.
3.  **Vulnerability Data Handling**:
    Always sanitize sensitive credentials (keys, tokens, passwords) found in logs or screenshots before submitting them via `submit_issue`.
