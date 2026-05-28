# BLT API Documentation

## Overview

The BLT API is built on Cloudflare Python Workers, providing fast, secure, and globally distributed endpoints for dynamic features.

**Base URL**: `https://api.owaspblt.org` (or your configured worker URL)

**Authentication**: JWT Bearer tokens

## Authentication

### Register a New User

**POST** `/api/auth/signup`

Creates a new user account.

**Request Body:**
```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com"
  }
}
```

### Login

**POST** `/api/auth/login`

Authenticates a user and returns a JWT token.

**Request Body:**
```json
{
  "email": "alice@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com"
  }
}
```

### Get Current User

**GET** `/api/auth/me`

Returns the currently authenticated user's information.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "points": 2500,
    "rank": 15
  }
}
```

### Logout

**POST** `/api/auth/logout`

Invalidates the current session token.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true
}
```

## Bugs

### List Bugs

**GET** `/api/bugs`

Returns a list of reported bugs.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)
- `status` (optional): Filter by status (open, verified, fixed, invalid)
- `severity` (optional): Filter by severity (critical, high, medium, low, info)
- `project_id` (optional): Filter by project

**Response:**
```json
{
  "bugs": [
    {
      "id": 1,
      "title": "SQL Injection in login form",
      "severity": "critical",
      "status": "open",
      "reporter": "alice",
      "reward": 500,
      "created_at": "2026-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20
}
```

### Get Bug Details

**GET** `/api/bugs/:id`

Returns detailed information about a specific bug.

**Response:**
```json
{
  "id": 1,
  "title": "SQL Injection in login form",
  "description": "The login form is vulnerable to SQL injection...",
  "severity": "critical",
  "status": "verified",
  "type": "security",
  "url": "https://example.com/login",
  "steps": "1. Navigate to login\n2. Enter ' OR '1'='1...",
  "reporter": {
    "id": 1,
    "username": "alice"
  },
  "reward": 500,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-16T14:20:00Z"
}
```

### Report a Bug

**POST** `/api/bugs`

Creates a new bug report.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "XSS vulnerability in comments",
  "description": "Detailed description of the vulnerability",
  "severity": "high",
  "type": "security",
  "url": "https://example.com/comments",
  "steps": "1. Go to comments\n2. Submit <script>alert(1)</script>",
  "project_id": 5
}
```

**Response:**
```json
{
  "success": true,
  "bug": {
    "id": 42,
    "title": "XSS vulnerability in comments",
    "status": "open",
    "created_at": "2026-02-18T12:00:00Z"
  }
}
```

### Update Bug

**PUT** `/api/bugs/:id`

Updates an existing bug report.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "status": "fixed",
  "notes": "Fixed in version 2.1.0"
}
```

### Delete Bug

**DELETE** `/api/bugs/:id`

Deletes a bug report (admin only).

**Headers:**
```
Authorization: Bearer <token>
```

## Leaderboard

### Get Leaderboard

**GET** `/api/leaderboard`

Returns the top researchers ranked by points.

**Query Parameters:**
- `limit` (optional): Number of results (default: 100, max: 500)
- `timeframe` (optional): Filter by timeframe (all-time, year, month, week)

**Response:**
```json
{
  "leaderboard": [
    {
      "rank": 1,
      "username": "alice",
      "points": 2500,
      "bugs": 45,
      "avatar": "https://example.com/avatar.jpg"
    },
    {
      "rank": 2,
      "username": "bob",
      "points": 2100,
      "bugs": 38,
      "avatar": null
    }
  ],
  "updated_at": "2026-02-18T12:00:00Z"
}
```

## Projects

### List Projects

**GET** `/api/projects`

Returns active bug bounty projects.

**Query Parameters:**
- `page` (optional): Page number
- `limit` (optional): Items per page
- `status` (optional): Filter by status (active, paused, completed)

**Response:**
```json
{
  "projects": [
    {
      "id": 1,
      "name": "OWASP BLT",
      "description": "Bug bounty program for OWASP BLT",
      "logo": "https://example.com/logo.png",
      "website": "https://owaspblt.org",
      "reward_range": "$100-$5000",
      "bugs_submitted": 245,
      "status": "active"
    }
  ],
  "total": 15
}
```

### Get Project Details

**GET** `/api/projects/:id`

Returns detailed project information.

### Create Project

**POST** `/api/projects`

Creates a new bug bounty project (authenticated users only).

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "name": "My Awesome App",
  "description": "Bug bounty program for My Awesome App",
  "website": "https://myawesomeapp.com",
  "reward_range": "$50-$2000",
  "scope": ["https://myawesomeapp.com/*"],
  "out_of_scope": ["https://myawesomeapp.com/blog/*"]
}
```

## Statistics

### Get Platform Stats

**GET** `/api/stats`

Returns platform-wide statistics.

**Response:**
```json
{
  "bugs_reported": 15234,
  "active_researchers": 3421,
  "rewards_distributed": "$248,500",
  "projects_protected": 892
}
```

## User Profile

### Get User Profile

**GET** `/api/users/:username`

Returns public profile information for a user.

**Response:**
```json
{
  "id": 1,
  "username": "alice",
  "bio": "Security researcher",
  "avatar": "https://example.com/avatar.jpg",
  "points": 2500,
  "rank": 15,
  "bugs_reported": 45,
  "bugs_verified": 38,
  "joined_at": "2025-06-10T08:00:00Z",
  "badges": ["Top Contributor", "Bug Hunter"]
}
```

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request
```json
{
  "error": "Invalid input",
  "message": "Email is required"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "error": "Forbidden",
  "message": "You don't have permission to access this resource"
}
```

### 404 Not Found
```json
{
  "error": "Not found",
  "message": "The requested resource was not found"
}
```

### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "message": "Please try again later"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

## Rate Limits

- **Authenticated requests**: 1000 requests per hour
- **Unauthenticated requests**: 100 requests per hour

Rate limit information is included in response headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1708268400
```

## CORS

The API supports CORS for allowed origins. Include these headers in requests:

```
Origin: https://owasp-blt.github.io
```

## Pagination

Endpoints that return lists support pagination:

**Request:**
```
GET /api/bugs?page=2&limit=50
```

**Response includes:**
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 50,
    "total": 500,
    "pages": 10
  }
}
```

## Filtering

Many endpoints support filtering via query parameters:

```
GET /api/bugs?status=open&severity=critical
GET /api/bugs?project_id=5&reporter=alice
```

## Webhooks (Coming Soon)

Subscribe to events:
- Bug reported
- Bug verified
- Bug fixed
- Reward distributed

## SDK Support (Planned)

Official SDKs coming soon:
- JavaScript/TypeScript
- Python
- Go
- Ruby
