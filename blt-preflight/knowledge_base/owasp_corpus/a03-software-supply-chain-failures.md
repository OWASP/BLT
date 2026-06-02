---
title: A03:2025 Software Supply Chain Failures
source_url: https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/
category: A03
last_updated: 2025
---

# A03:2025 Software Supply Chain Failures

## Background
Software Supply Chain Failures is ranked **#3** in the OWASP Top 10 2025. It was the highest-ranked category in the community survey, with 50% of respondents placing it at **#1**. This category expands the previous focus on vulnerable components to include risks across the entire software supply chain, including dependencies, build systems, CI/CD pipelines, package registries, developer tools, and software distribution infrastructure.

## Description
Software Supply Chain Failures occur when vulnerabilities, malicious modifications, or security weaknesses are introduced through third-party software, dependencies, build environments, development tools, or deployment pipelines that an application relies upon. Instead of attacking the application directly, attackers compromise trusted components within the software ecosystem.

**Common vulnerabilities include:**
- Using vulnerable or outdated third-party libraries
- Unmaintained or unsupported dependencies
- Dependency confusion attacks
- Malicious packages in package repositories
- Compromised CI/CD pipelines
- Weak access controls on code repositories
- Insecure artifact repositories and container registries
- Lack of Software Bill of Materials (SBOM)
- Unsigned or unverified software packages
- Inadequate monitoring of supply chain changes
- Excessive privileges in build and deployment systems

## How to Prevent

- Maintain a complete **Software Bill of Materials (SBOM)** for all applications.
- Track both direct and transitive dependencies.
- Continuously scan dependencies for known vulnerabilities.
- Remove unused libraries, packages, and components.
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