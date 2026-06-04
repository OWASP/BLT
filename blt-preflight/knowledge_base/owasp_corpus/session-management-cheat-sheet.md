---
title: Session Management Cheat Sheet
source_url: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
category: A07
last_updated: 2025
---

# Session Management Cheat Sheet

## Introduction
Session Management is the process by which a web application maintains state for a user across multiple requests. A secure session management system is critical to prevent session hijacking, fixation, and impersonation attacks.

## Core Principles

### Session ID Generation
- Use a **Cryptographically Secure Pseudorandom Number Generator (CSPRNG)**
- Minimum **64 bits of entropy** (ideally 128 bits)
- Session ID should be **long enough** (e.g., 16+ hex characters)
- Make it **meaningless** (no user info, no predictable patterns)
- Change default session ID name (e.g., avoid `PHPSESSID`, `JSESSIONID`)

### Cookie Security Flags (Critical)
- **`Secure`** — Only send over HTTPS
- **`HttpOnly`** — Prevent JavaScript access (protects against XSS)
- **`SameSite=Strict`** (preferred) or `SameSite=Lax` — CSRF protection
- Use `__Host-` prefix when possible for stronger binding

### Session Lifecycle
- **Regenerate session ID** after login (privilege change)
- Implement **Idle Timeout** (15–30 mins typical)
- Implement **Absolute Timeout** (4–8 hours typical)
- Invalidate session on logout
- Require **re-authentication** for sensitive actions

### Additional Defenses
- Bind session to User-Agent + IP (where feasible)
- Do **not** accept session IDs from URL parameters
- Use generic error messages to prevent enumeration
- Log session creation, renewal, and destruction

## Common Vulnerabilities
- Session Fixation
- Session Hijacking
- Weak Session ID generation
- Missing `Secure` / `HttpOnly` flags
- Session ID in URL
- Insufficient session timeouts

## Signals for RAG Queries
`session`, `session id`, `session fixation`, `session hijacking`, `cookie secure`, `httponly`, `samesite`, `session timeout`, `session regeneration`, `logout`, `re-authentication`