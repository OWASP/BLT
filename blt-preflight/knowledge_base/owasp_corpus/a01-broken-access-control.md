---
title: A01:2025 Broken Access Control
source_url: https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/
category: A01
last_updated: 2025
---

# A01:2025 Broken Access Control

## Background
Broken Access Control maintains its position at **#1** in the OWASP Top 10 2025.  
100% of tested applications had some form of broken access control. It has the highest number of occurrences in the contributed dataset.

## Description
Access control enforces policy so that users cannot act outside of their intended permissions. Failures typically lead to unauthorized information disclosure, modification or destruction of data, or performing business functions outside a user's limits.

**Common vulnerabilities include:**
- Violating the principle of least privilege (deny by default)
- URL parameter tampering / force browsing
- Insecure Direct Object References (IDOR)
- Missing access control on APIs (POST, PUT, DELETE)
- Elevation of privilege
- Metadata manipulation (JWT tampering, cookie tampering)
- CORS misconfiguration
- Accessing privileged pages as a normal user

## How to Prevent

- **Deny by default** — except for public resources.
- Implement access control mechanisms **once** and reuse them throughout the application.
- Enforce record ownership in domain models (users can only access their own data).
- Disable directory listing and remove sensitive files (`.git`, backups) from web roots.
- Log access control failures and alert on suspicious activity.
- Use rate limiting on APIs.
- Implement proper session invalidation and short-lived JWTs.
- Use well-established frameworks and libraries for authorization.

## Example Attack Scenarios

**Scenario #1:**  
An application uses unverified data in a database query:

```sql
pstmt.setString(1, request.getParameter("acct"));
ResultSet results = pstmt.executeQuery(); 
```

**Scenario #2:**
An API endpoint allows any authenticated user to delete records of other users because there is no ownership check.
