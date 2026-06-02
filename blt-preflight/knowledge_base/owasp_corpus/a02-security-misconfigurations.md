---
title: A02:2025 Security Misconfiguration
source_url: https://owasp.org/Top10/2025/A02_2025-Security_Misconfiguration/
category: A02
last_updated: 2025
---

# A02:2025 Security Misconfiguration

## Background
Security Misconfiguration moved up to **#2** in the OWASP Top 10 2025 from **#5** in the previous edition. OWASP reports that 100% of tested applications contained some form of security misconfiguration, with over 719,000 recorded occurrences in the contributed dataset. As modern applications rely increasingly on cloud services, infrastructure-as-code, containers, and highly configurable platforms, configuration mistakes have become one of the most common security risks.

## Description
Security Misconfiguration occurs when applications, servers, databases, cloud services, frameworks, or security controls are configured insecurely, left with default settings, or deployed without proper hardening. These weaknesses often expose sensitive information and create attack paths without requiring sophisticated exploits.

**Common vulnerabilities include:**
- Default accounts and unchanged default passwords
- Debug mode enabled in production
- Verbose error messages and stack trace disclosure
- Unnecessary services, ports, APIs, or sample applications enabled
- Misconfigured cloud storage permissions
- Missing or weak security headers
- Overly permissive CORS policies
- Insecure framework or application server settings
- Exposed administrative interfaces
- Hardcoded secrets and credentials in configuration files

## How to Prevent

- Establish a **repeatable security hardening process** for all environments.
- Keep development, staging, and production environments consistently configured.
- Remove unused services, sample applications, documentation, and unnecessary features.
- Regularly review and update security configurations after patches and upgrades.
- Configure cloud resources using the **principle of least privilege**.
- Implement network segmentation, container isolation, and security groups.
- Use secure HTTP security headers (CSP, HSTS, X-Frame-Options, etc.).
- Disable detailed error messages for end users.
- Automate configuration validation and compliance checks.
- Use identity federation, short-lived credentials, and role-based access controls instead of embedded secrets.
- Continuously monitor for configuration drift across environments.

## Example Attack Scenarios

**Scenario #1:**  
A production server still contains a default administrative console and default credentials. An attacker discovers the console and logs in using publicly known credentials, gaining full control of the application environment.

**Scenario #2:**
Directory listing is enabled on a web server. An attacker browses application directories, downloads compiled source files, reverse engineers the code, and identifies additional vulnerabilities.

**Scenario #3:**
An application returns detailed stack traces and framework version information whenever an exception occurs. An attacker uses the exposed information to identify known vulnerabilities and launch targeted attacks.