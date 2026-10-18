# OWASP BLT-Toasty API Reference

Welcome to the OWASP BLT-Toasty backend API reference. This document details the endpoints available in the service, authentication mechanisms, common request/response structures, and rate limits.

## Base URL

All endpoints are relative to the root URL of your deployed Cloudflare Worker or backend service.

## Authentication

Authentication is required for most secure endpoints under the `/mcp/*`, `/admin/*`, and `/conversations/*` paths. The API uses RS256 JWTs passed via the `Authorization` header.

**Header Format**:
```http
Authorization: Bearer <RS256_JWT>
```

**Required JWT Claims**:
- `iss`: Must be `owasp-blt-service`
- `aud`: Must be `toasty-mcp`
- `sub`: The agent or user ID
- `exp`: Standard expiration timestamp

**Admin Endpoints**: Endpoints under `/admin/dashboard` require the JWT to contain an admin role claim.

## Rate Limiting

The API implements rate limiting via the Cloudflare Durable Object `RateLimiterDO`.
- **Limit**: 100 requests per 60 seconds per IP/Agent.
- **Exceeded Limit**: If the limit is exceeded, the server responds with HTTP `429 Too Many Requests`.

## CORS (Cross-Origin Resource Sharing)

All responses include the `Access-Control-Allow-Origin: *` header, making the API accessible from any origin. `OPTIONS` preflight requests are fully supported across all routes.

## Standard Error Response Format

Across all endpoints, an error response generally adheres to the following JSON schema:

```json
{
  "error": "Human readable error description",
  "status": 400
}
```

## Endpoints

### General & System

#### Root Landing Page
- **Method**: `GET` / `HEAD`
- **Path**: `/`
- **Auth Required**: No
- **Description**: Root landing page. Returns an HTML welcome page.
- **Responses**:
  - `200 OK`: Returns HTML.

#### Health Check
- **Method**: `GET` / `HEAD`
- **Path**: `/health`
- **Auth Required**: No
- **Description**: Returns the health status of the backend service.
- **Responses**:
  - `200 OK`:
    ```json
    {
      "status": "healthy",
      "service": "toasty-backend",
      "timestamp": 1714521234
    }
    ```

#### API Status
- **Method**: `GET` / `HEAD`
- **Path**: `/api/status`
- **Auth Required**: No
- **Description**: Provides current API operational status and version.
- **Responses**:
  - `200 OK`:
    ```json
    {
      "status": "operational",
      "version": "1.0.0"
    }
    ```

### Core Features

#### Code Review
- **Method**: `POST`
- **Path**: `/api/review`
- **Auth Required**: No (Not specified)
- **Description**: Submits code or patches for automated security review.
- **Request Body**: JSON payload containing the code to review.
- **Responses**:
  - `200 OK`: Returns review results.

#### GitLab Webhook Ingestion
- **Method**: `POST`
- **Path**: `/webhook/gitlab`
- **Auth Required**: Custom Headers
- **Description**: Ingests incoming webhooks from GitLab (e.g., issues, merge requests, push events).
- **Required Headers**:
  - `X-Gitlab-Token`: Shared secret token.
  - `X-Gitlab-Event-UUID`: Unique identifier for the event.
  - `X-Gitlab-Event`: Event type descriptor.
- **Request Body**: Raw GitLab webhook JSON payload.
- **Responses**:
  - `202 Accepted`: Event queued successfully.
    ```json
    {
      "event_id": "a1b2c3d4...",
      "status": "pending"
    }
    ```
  - `401 Unauthorized`: Missing or invalid `X-Gitlab-Token`.
  - `409 Conflict`: Duplicate event (replay detected via `delivery_id`).
  - `422 Unprocessable Entity`: Missing headers, invalid JSON payload, or normalization failure.
  - `500 Internal Server Error`: Server failure during ingestion.

#### Triage Rationale
- **Method**: `GET`
- **Path**: `/triage/{event_id}/rationale`
- **Auth Required**: No
- **Description**: Fetches the structural reasoning and evidence for why a specific event was triaged in a certain way.
- **Path Parameters**:
  - `event_id` (string): URL-decoded event ID. Must not contain `/`.
- **Responses**:
  - `200 OK`: Returns a structured rationale including CWE evidence, duplicate reasoning, and severity scoring data.
  - `400 Bad Request`: Invalid `event_id`.

### Model Context Protocol (MCP)

#### MCP Triage Export
- **Method**: `GET`
- **Path**: `/mcp/triage/{triage_id}`
- **Auth Required**: Yes (Bearer JWT)
- **Description**: Exports a specific triage item in MCP-compatible format.
- **Path Parameters**:
  - `triage_id` (string): URL-decoded triage ID. Must not contain `/`.
- **Responses**:
  - `200 OK`: Returns MCP-formatted triage data.
  - `400 Bad Request`: Missing or invalid `triage_id`.
  - `401 Unauthorized`: Missing or invalid JWT.

### Agent Conversations

#### Add Reply to Conversation
- **Method**: `POST`
- **Path**: `/conversations/{triage_id}/reply`
- **Auth Required**: Yes (Bearer JWT)
- **Description**: Appends a new message turn to an ongoing agent-triage conversation.
- **Path Parameters**:
  - `triage_id` (string): Target conversation ID.
- **Request Limits**:
  - Max body size: 1MB.
  - Content string max length: 20,000 characters.
- **Request Body**:
  ```json
  {
    "role": "developer", // or "ai"
    "content": "Message content here..."
  }
  ```
- **Responses**:
  - `200 OK`:
    ```json
    {
      "turn_count": 5,
      "conversation_id": "conv_12345"
    }
    ```
  - `400 Bad Request`: Invalid payload format or role.
  - `401 Unauthorized`: Missing or invalid JWT.
  - `409 Conflict`: Attempted to reply to a closed/archived conversation.
  - `413 Payload Too Large`: Request body or content exceeds maximum allowed limits.

#### Get Conversation History
- **Method**: `GET`
- **Path**: `/conversations/{triage_id}/history`
- **Auth Required**: Yes (Bearer JWT)
- **Description**: Retrieves the message history for a specific conversation.
- **Path Parameters**:
  - `triage_id` (string): Target conversation ID.
- **Query Parameters**:
  - `full` (boolean): Fetch full history if true.
  - `cursor` (integer): Pagination cursor.
- **Responses**:
  - `200 OK`:
    ```json
    {
      "conversation_id": "conv_12345",
      "turns": [],
      "turn_count": 5,
      "status": "active",
      "next_cursor": 6
    }
    ```
  - `401 Unauthorized`: Missing or invalid JWT.

#### Delete/Archive Conversation
- **Method**: `DELETE`
- **Path**: `/conversations/{triage_id}`
- **Auth Required**: Yes (Bearer JWT)
- **Description**: Archives or deletes an active conversation.
- **Path Parameters**:
  - `triage_id` (string): Target conversation ID.
- **Responses**:
  - `200 OK`:
    ```json
    {
      "archived": true,
      "turns_archived": 5
    }
    ```
  - `401 Unauthorized`: Missing or invalid JWT.

### Administration

#### Admin Dashboard
- **Method**: `GET`
- **Path**: `/admin/dashboard`
- **Auth Required**: Yes (Bearer JWT with `role: "admin"`)
- **Description**: Returns aggregated system metrics, activity data, and backend statistics.
- **Responses**:
  - `200 OK`: Returns structured JSON dashboard data.
  - `401 Unauthorized`: Missing auth, invalid JWT, or token lacks the required admin role.

