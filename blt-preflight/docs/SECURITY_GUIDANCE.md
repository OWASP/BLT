# BLT-Preflight Security Guidance

This document provides comprehensive security guidance for contributors to the OWASP BLT project.

## Overview

BLT Preflight is an advisory system that helps contributors understand security expectations before opening pull requests. It's designed to:

- Prevent common security mistakes
- Educate contributors on security best practices
- Reduce maintainer workload by catching issues early
- Provide plain-language guidance with documentation links

**Important**: This is an advisory system, not enforcement. The guidance is meant to help, not block contributions.

## Security Topics

### 🔐 Authentication

Authentication is a critical security component. When working with authentication code:

**Best Practices:**
- Use multi-factor authentication (MFA) where possible
- Implement secure session management with proper timeout
- Hash passwords using bcrypt, Argon2, or scrypt (never MD5 or SHA1)
- Add rate limiting to prevent brute force attacks
- Use secure password reset flows with time-limited tokens
- Implement account lockout after failed attempts

**Common Mistakes to Avoid:**
- Storing passwords in plain text
- Using weak hashing algorithms
- Not implementing rate limiting
- Insufficient session timeout
- Weak password requirements

**Resources:**
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

### 🔑 API Keys and Secrets Management

Never commit secrets to version control. This is one of the most common security mistakes.

**Best Practices:**
- Use environment variables for all secrets
- Use a secrets manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
- Rotate keys regularly
- Use different keys for development, staging, and production
- Implement proper key revocation procedures
- Add `.env` files to `.gitignore`

**Common Mistakes to Avoid:**
- Committing `.env` files or config files with secrets
- Hardcoding API keys in source code
- Using the same keys across environments
- Not rotating compromised keys immediately

**Resources:**
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

### 🗄️ Database Security

Database security is crucial for protecting sensitive data.

**Best Practices:**
- Use parameterized queries or ORMs to prevent SQL injection
- Implement proper access controls with least privilege
- Encrypt sensitive data at rest and in transit
- Validate and sanitize all inputs
- Use database-level encryption for sensitive fields
- Regular backups with secure storage
- Audit database access logs

**Common Mistakes to Avoid:**
- Building SQL queries with string concatenation
- Using overly permissive database user permissions
- Storing sensitive data unencrypted
- Not validating user inputs

**Resources:**
- [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [OWASP Query Parameterization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html)

### 🔒 Encryption

Proper encryption is essential for protecting sensitive data.

**Best Practices:**
- Use well-tested cryptographic libraries (OpenSSL, libsodium, etc.)
- Never create custom encryption algorithms
- Use strong key lengths: AES-256, RSA-2048 or higher
- Implement proper key management and rotation
- Use authenticated encryption (AES-GCM, ChaCha20-Poly1305)
- Keep cryptographic libraries up to date

**Common Mistakes to Avoid:**
- Rolling your own crypto
- Using weak encryption algorithms (DES, RC4)
- Hardcoding encryption keys
- Using ECB mode
- Not authenticating encrypted data

**Resources:**
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [OWASP Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)

### 🌐 API Security

APIs are common attack vectors and require careful security consideration.

**Best Practices:**
- Implement proper authentication (OAuth2, JWT, API keys)
- Add rate limiting to prevent abuse
- Validate all input data with strict schemas
- Use HTTPS only (TLS 1.2+)
- Implement proper error handling (don't leak sensitive info)
- Version your APIs for backward compatibility
- Use CORS headers appropriately
- Implement request size limits

**Common Mistakes to Avoid:**
- Exposing APIs without authentication
- Not implementing rate limiting
- Returning detailed error messages to clients
- Not validating input data types and ranges
- Using GET requests for state-changing operations

**Resources:**
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)

### 📤 File Upload Security

File upload functionality can be exploited if not properly secured.

**Best Practices:**
- Validate file types using content inspection (not just extensions)
- Implement file size limits
- Scan uploaded files for malware
- Store files outside the web root
- Use random filenames to prevent overwrites
- Implement access controls on uploaded files
- Strip metadata from images

**Common Mistakes to Avoid:**
- Trusting file extensions
- Allowing executable files
- Storing files in web-accessible directories
- Not implementing size limits
- Executing or parsing uploaded files without validation

**Resources:**
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

### ⚠️ Input Validation

All user input is untrusted and must be validated.

**Best Practices:**
- Validate input on the server side (never trust client validation alone)
- Use allowlists rather than denylists
- Sanitize output for the specific context (HTML, SQL, etc.)
- Implement strict type checking
- Use parameterized queries for databases
- Escape output appropriately for the context
- Implement Content Security Policy (CSP)

**Common Mistakes to Avoid:**
- Client-side only validation
- Using denylist-based validation
- Not escaping output
- Trusting user-supplied data
- Not validating data types

**Resources:**
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)

## General Security Principles

### Defense in Depth

Implement multiple layers of security controls. If one layer fails, others provide protection.

### Principle of Least Privilege

Grant only the minimum permissions necessary for a function to work.

### Fail Securely

When errors occur, fail in a secure state. Don't expose sensitive information in error messages.

### Don't Trust User Input

Treat all user input as potentially malicious. Validate, sanitize, and escape appropriately.

### Keep Security Simple

Complex security mechanisms are harder to implement correctly. Use simple, well-tested solutions.

### Security by Design

Consider security from the beginning of development, not as an afterthought.

## OWASP Top 10 (2021)

Familiarize yourself with the OWASP Top 10 security risks:

1. **Broken Access Control** - Restrictions on authenticated users not properly enforced
2. **Cryptographic Failures** - Failures related to cryptography leading to sensitive data exposure
3. **Injection** - User data sent to interpreters as commands or queries
4. **Insecure Design** - Missing or ineffective security controls in design
5. **Security Misconfiguration** - Missing security hardening or improperly configured permissions
6. **Vulnerable and Outdated Components** - Using components with known vulnerabilities
7. **Identification and Authentication Failures** - Broken authentication mechanisms
8. **Software and Data Integrity Failures** - Code and infrastructure without integrity verification
9. **Security Logging and Monitoring Failures** - Insufficient logging and monitoring
10. **Server-Side Request Forgery (SSRF)** - Fetching remote resources without validating URL

[Learn more about OWASP Top 10](https://owasp.org/www-project-top-ten/)

## Getting Help

- **Questions?** Open an issue with the `question` label
- **Security concerns?** Email security@owasp.org
- **Documentation issues?** Submit a PR to improve this guide

## Feedback

Your feedback helps improve this advisory system! When you receive security guidance:

- Let us know if it was helpful
- Suggest improvements to make guidance clearer
- Report any false positives or unnecessary warnings

Use the CLI to provide feedback:
```bash
python3 src/blt_preflight.py feedback \
  --pattern "Security Advisory: Authentication" \
  --helpful yes \
  --comments "Very helpful, clear recommendations"
```

---

*This guidance is provided as an advisory to help contributors. It's not meant to be comprehensive security training, but rather a quick reference for common security considerations.*
