# AI Agent Guide for BLT-MCP

This guide explains how to interact with the OWASP Bug Logging Tool (BLT) ecosystem using the **`blt-mcp`** Model Context Protocol (MCP) server. Use these tools, resources, and prompts to help users find, triage, report, and remediate security vulnerabilities.

---

## 1. Available Resources (`blt://`)

You can read structured JSON data from the BLT ecosystem using the following URIs:

*   **`blt://v2/bugs`** - Retrieves the list of all active bug reports and vulnerabilities.
*   **`blt://v2/bugs/{id}`** - Fetches detailed info for a specific bug, including screenshots, OCR text, and user comments.
*   **`blt://v2/repos`** - Lists all tracked repositories registered in the BLT platform.
*   **`blt://v2/repos/{id}`** - Fetches details for a specific repository.
*   **`blt://v2/stats`** - Retrieves global platform stats (total bugs, active repos, bacon points).
*   **`blt://v2/leaderboard`** - Fetches the global contributor leaderboard rankings.

---

## 2. Executable Tools

You can perform actions on the BLT platform by calling the following MCP tools:

### `submit_issue`
Submit a new bug or security vulnerability to the OWASP BLT database.
*   **Arguments**:
    *   `url` (string, required): The target URL of the vulnerability.
    *   `description` (string, required): Detailed description of the vulnerability.
    *   `title` (string, optional): Title of the bug.
    *   `severity` (string, optional): `Critical`, `High`, `Medium`, or `Low`.
    *   `bug_type` (string, optional): Type of bug (e.g. `SQLi`, `XSS`, `IDOR`).
    *   `steps_to_reproduce` (string, optional): Numbered steps to reproduce the issue.
    *   `screenshot` (string, optional): Base64-encoded image string.

### `triage_vulnerability`
Analyze a vulnerability description using Cloudflare Workers AI (Llama 3.1) to automatically determine class, severity, and mitigation steps.
*   **Arguments**:
    *   `prompt` (string, required): Contextual description of the issue to analyze.

### `add_comment`
Add comments or feedback to a specific bug report.
*   **Arguments**:
    *   `issue_id` (string, required): Target bug report ID.
    *   `text` (string, required): The comment content.

---

## 3. Prompts & Workflows

You can load structured prompt templates to guide your interaction with the user:

*   **`triage_vulnerability`**: Helps you gather necessary context to perform initial severity assessment and vulnerability class mapping.
*   **`plan_remediation`**: Guides you in drafting a detailed step-by-step remediation and patching plan for a specific security finding.
*   **`review_contribution`**: Helps you evaluate pull requests, code contributions, or bug reports, and recommend gamified "Bacon Point" awards.

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
