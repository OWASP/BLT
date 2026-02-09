# Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER'S BROWSER                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      index.html                               │  │
│  │  ┌────────────┐  ┌──────────────────┐  ┌──────────────────┐  │  │
│  │  │  Sidebar   │  │   Main Content   │  │   Vanilla JS     │  │  │
│  │  │            │  │                  │  │                  │  │  │
│  │  │ Repo List  │  │  PR Input Field  │  │  Event Handlers  │  │  │
│  │  │            │  │                  │  │  API Calls       │  │  │
│  │  │ - All      │  │  PR Cards:       │  │  DOM Updates     │  │  │
│  │  │ - Repo 1   │  │  - Avatar        │  │  State Mgmt      │  │  │
│  │  │ - Repo 2   │  │  - Title         │  │                  │  │  │
│  │  │            │  │  - Badges        │  │                  │  │  │
│  │  │            │  │  - Details       │  │                  │  │  │
│  │  │            │  │  - Checks        │  │                  │  │  │
│  │  └────────────┘  └──────────────────┘  └──────────────────┘  │  │
│  │                                                                │  │
│  │  Embedded CSS (GitHub Dark Theme)                             │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  ↕ HTTPS
┌─────────────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE WORKERS (Edge)                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                       index.py                                │  │
│  │                                                               │  │
│  │  ┌──────────────────────────────────────────────────────┐    │  │
│  │  │  on_fetch(request, env)                              │    │  │
│  │  │  - Route: /                    → Serve HTML          │    │  │
│  │  │  - Route: /api/repos          → List Repos          │    │  │
│  │  │  - Route: /api/prs            → List/Add PRs        │    │  │
│  │  │  - Route: /api/refresh        → Refresh PR          │    │  │
│  │  └──────────────────────────────────────────────────────┘    │  │
│  │                                                               │  │
│  │  ┌──────────────────────────────────────────────────────┐    │  │
│  │  │  fetch_pr_data(owner, repo, pr_number)               │    │  │
│  │  │  - Call GitHub API (4 endpoints)                     │    │  │
│  │  │  - Aggregate data                                    │    │  │
│  │  │  - Handle rate limits                                │    │  │
│  │  └──────────────────────────────────────────────────────┘    │  │
│  │                                                               │  │
│  │  ┌──────────────────────────────────────────────────────┐    │  │
│  │  │  handle_add_pr / handle_list_prs / etc.             │    │  │
│  │  │  - Parse PR URL                                      │    │  │
│  │  │  - Fetch from GitHub                                 │    │  │
│  │  │  - Store in D1                                       │    │  │
│  │  └──────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         ↕ Python async fetch                    ↕ SQL queries
┌────────────────────────────┐         ┌────────────────────────────┐
│    GITHUB API (REST v3)    │         │   CLOUDFLARE D1 DATABASE   │
│                            │         │        (SQLite)            │
│  • GET /pulls/{number}     │         │                            │
│  • GET /pulls/{number}/    │         │  ┌──────────────────────┐  │
│        files               │         │  │   prs table          │  │
│  • GET /pulls/{number}/    │         │  │                      │  │
│        reviews             │         │  │  - id (PK)           │  │
│  • GET /commits/{sha}/     │         │  │  - pr_url (unique)   │  │
│        check-runs          │         │  │  - repo_owner        │  │
│                            │         │  │  - repo_name         │  │
│  Rate Limit: 60/hour       │         │  │  - pr_number         │  │
│  (unauthenticated)         │         │  │  - title             │  │
│                            │         │  │  - state             │  │
└────────────────────────────┘         │  │  - is_merged         │  │
                                       │  │  - mergeable_state   │  │
                                       │  │  - files_changed     │  │
                                       │  │  - author_login      │  │
                                       │  │  - author_avatar     │  │
                                       │  │  - checks_*          │  │
                                       │  │  - review_status     │  │
                                       │  │  - timestamps        │  │
                                       │  └──────────────────────┘  │
                                       │                            │
                                       │  Indexes:                  │
                                       │  - idx_repo                │
                                       │  - idx_pr_number           │
                                       └────────────────────────────┘
```

## Request Flow: Adding a PR

```
User enters PR URL
      ↓
Frontend validates format
      ↓
POST /api/prs {"pr_url": "https://github.com/..."}
      ↓
Backend: parse_pr_url() extracts owner, repo, number
      ↓
Backend: fetch_pr_data() makes 4 parallel GitHub API calls:
      ├─→ GET /repos/{owner}/{repo}/pulls/{number}
      ├─→ GET /repos/{owner}/{repo}/pulls/{number}/files
      ├─→ GET /repos/{owner}/{repo}/pulls/{number}/reviews
      └─→ GET /repos/{owner}/{repo}/commits/{sha}/check-runs
      ↓
Backend: Aggregate data, calculate review status, count checks
      ↓
Backend: INSERT or UPDATE in D1 database
      ↓
Backend: Return JSON response
      ↓
Frontend: Update UI with new PR card
```

## Request Flow: Listing PRs

```
Page load or repo filter click
      ↓
GET /api/prs?repo=owner/name (optional filter)
      ↓
Backend: Query D1 database
      ↓
Backend: SELECT * FROM prs WHERE ... ORDER BY last_updated_at DESC
      ↓
Backend: Return JSON array of PRs
      ↓
Frontend: renderPrList() creates PR cards
      ↓
Frontend: Display with badges, checks, and details
```

## Data Flow: PR Information

```
GITHUB API DATA                STORED IN D1               DISPLAYED ON UI
─────────────────              ──────────────             ───────────────
PR Details:
• title                    →   title                  →   Card title
• state                    →   state                  →   Badge (Open/Closed)
• merged                   →   is_merged              →   Badge (Merged)
• mergeable_state          →   mergeable_state        →   Merge status
• updated_at               →   last_updated_at        →   Time ago
• user.login               →   author_login           →   Author name
• user.avatar_url          →   author_avatar          →   Avatar image

Files:
• Array length             →   files_changed          →   Files changed count

Reviews:
• Latest per user          →   review_status          →   Review badge
• APPROVED                 →   'approved'             →   Green badge
• CHANGES_REQUESTED        →   'changes_requested'    →   Red badge

Check Runs:
• conclusion: success      →   checks_passed          →   ✓ X passed
• conclusion: failure      →   checks_failed          →   ✗ X failed
• conclusion: skipped      →   checks_skipped         →   - X skipped
```

## Security Layers

```
User Input → Frontend Validation → Backend Validation → GitHub API
    ↓             ↓                      ↓                    ↓
 Sanitize      URL Format          Parse & Verify       Rate Limit
 XSS Filter    Regex Check         Error Handling       Status Check
 Escape HTML   Client-side         Server-side          403/429 Handle
```

## Deployment Architecture

```
Developer Machine               Cloudflare Edge            Cloudflare D1
─────────────────              ──────────────             ─────────────
wrangler.toml
src/index.py        →  Deploy  →  Python Worker    ←──→   SQLite DB
public/index.html   →  Upload  →  Static Assets          (Distributed)
schema.sql          →  Execute →  Initialize Schema

Commands:
1. wrangler d1 create pr-tracker
2. wrangler d1 execute pr-tracker --file=schema.sql
3. wrangler deploy
```

## Performance Characteristics

- **Initial Page Load**: < 1s (single HTML file, ~23 KB)
- **Add PR**: 2-5s (4 parallel GitHub API calls)
- **List PRs**: < 500ms (cached in D1)
- **Refresh PR**: 2-5s (4 parallel GitHub API calls)
- **Database Query**: < 100ms (indexed queries)

## Scalability

- **Cloudflare Workers**: Scales automatically, runs in 200+ cities
- **D1 Database**: Distributed SQLite, automatic replication
- **GitHub API**: Rate limited (60/hr unauthenticated, 5000/hr authenticated)
- **Client**: No server-side sessions, stateless
