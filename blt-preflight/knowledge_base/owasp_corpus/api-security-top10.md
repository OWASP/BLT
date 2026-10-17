---
title: OWASP Top 10 API Security Risks 2023
source_url: https://owasp.org/API-Security/editions/2023/en/0x11-t10/
category: API
last_updated: 2023
---

# OWASP Top 10 API Security Risks – 2023

## Overview
This list highlights the most critical security risks specific to APIs.

## The Top 10 API Security Risks

**API1:2023 — Broken Object Level Authorization**  
APIs expose endpoints handling object IDs without proper access control, allowing attackers to access or modify other users' data.

**API2:2023 — Broken Authentication**  
Weak authentication mechanisms allow attackers to compromise tokens or impersonate users.

**API3:2023 — Broken Object Property Level Authorization**  
Insufficient authorization at the property level leads to data exposure or manipulation (mass assignment).

**API4:2023 — Unrestricted Resource Consumption**  
APIs can be abused to consume excessive resources (CPU, bandwidth, storage), leading to DoS or high costs.

**API5:2023 — Broken Function Level Authorization**  
Missing or improper checks allow users to access functions they shouldn't (horizontal/vertical privilege escalation).

**API6:2023 — Unrestricted Access to Sensitive Business Flows**  
Business-critical flows (e.g., ticket booking, payments) can be abused through automation.

**API7:2023 — Server Side Request Forgery (SSRF)**  
Application fetches remote resources using unvalidated user-supplied URLs.

**API8:2023 — Security Misconfiguration**  
Insecure default settings, unnecessary features, or improper configurations.

**API9:2023 — Improper Inventory Management**  
Outdated documentation, deprecated API versions, or exposed debug endpoints.

**API10:2023 — Unsafe Consumption of APIs**  
Trusting data from third-party APIs without proper validation.

## Prevention Guidelines (Summary)

- Implement proper authorization checks at object and function level
- Use strong authentication and short-lived tokens
- Validate and sanitize all inputs and third-party responses
- Enforce rate limiting and resource quotas
- Maintain accurate API inventory and retire old versions
- Validate all server-side requests (SSRF protection)
- Follow secure configuration practices

## Signals for RAG Queries
`object level authorization`, `IDOR`, `broken authentication`, `mass assignment`, `rate limiting`, `SSRF`, `API misconfiguration`, `deprecated endpoint`, `third party API`, `privilege escalation`, `business logic abuse`