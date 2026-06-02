---
title: A04:2025 Cryptographic Failures
source_url: https://owasp.org/Top10/2025/A04_2025-Cryptographic_Failures/
category: A04
last_updated: 2025
---

# A03:2025 Cryptographic Failures

## Background
Cryptographic Failures ranks **#4** in the OWASP Top 10 2025, dropping two positions from the previous edition. This category focuses on failures involving missing encryption, weak cryptography, poor key management, insecure randomness, and misuse of cryptographic controls. OWASP reports over 1.6 million occurrences across the contributed dataset, making it one of the most significant causes of sensitive data exposure and system compromise.

## Description
Cryptographic Failures occur when sensitive data is insufficiently protected due to weak, outdated, incorrectly implemented, or completely absent cryptographic controls. These failures can expose credentials, personal information, financial records, health data, business secrets, and other sensitive information to attackers.

**Common vulnerabilities include:**
- Transmission of sensitive data over unencrypted channels (HTTP)
- Weak or deprecated cryptographic algorithms (MD5, SHA-1, DES)
- Improper key generation, storage, rotation, or management
- Hardcoded cryptographic keys and secrets
- Weak pseudo-random number generators (PRNGs)
- Insufficient entropy during key generation
- Missing encryption for sensitive data at rest
- Improper certificate validation and trust verification
- Insecure cryptographic modes (e.g., ECB mode)
- Passwords stored using weak or unsalted hashes
- Reused initialization vectors (IVs) or nonces
- Cryptographic downgrade attacks
- Failure to use authenticated encryption

## How to Prevent

- Classify and identify all sensitive data processed, stored, or transmitted by the application.
- Encrypt sensitive data both in transit and at rest.
- Enforce TLS 1.2+ (preferably TLS 1.3) for all communications.
- Use trusted, well-maintained cryptographic libraries instead of custom implementations.
- Download software only from trusted and verified sources.
- Verify package signatures and artifact integrity.
- Secure code repositories with MFA and branch protection.
- Harden CI/CD pipelines using least-privilege principles.
- Implement separation of duties for code review, approval, and deployment.
- Monitor and audit all changes to repositories, build systems, and deployment pipelines.
- Keep developer tools, build servers, and dependencies updated.
- Use staged or canary deployments instead of deploying updates everywhere at once.
- Establish a formal patch management and vulnerability response process.

## Example Attack Scenarios

**Scenario #1:**  
A widely trusted software vendor is compromised. Attackers inject malware into a legitimate software update, which is then distributed to thousands of customers. Organizations install the update believing it is safe, resulting in large-scale compromise. The SolarWinds attack is a well-known example.

**Scenario #2:**
A developer unknowingly installs a malicious package from a public package repository. The package contains hidden code that steals API keys, credentials, and sensitive environment variables during installation.

**Scenario #3:**
An attacker gains access to a CI/CD pipeline and modifies the build process to inject malicious code into application releases. Every future deployment contains the attacker's backdoor despite the source code appearing legitimate.

**Scenario #4:**
An organization continues using an outdated logging library containing a critical remote code execution vulnerability. Attackers exploit the vulnerable dependency to gain control of production servers. A notable example is the Log4Shell vulnerability (CVE-2021-44228).