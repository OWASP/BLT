---
title: Authentication Cheat Sheet
source_url: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
category: A07
last_updated: 2025
---

# Authentication Cheat Sheet

## Introduction
Authentication is the process of verifying that someone is who they claim to be. It is a critical control for protecting user accounts and sensitive data.

## Core Authentication Principles

### Password Security
- **Minimum length**: 15 characters (without MFA) or 8 characters (with MFA)
- Allow **passphrases** up to 64+ characters
- **No** complex composition rules (no forced uppercase + numbers + symbols)
- Block common and previously breached passwords (Have I Been Pwned)
- Use a strong password strength meter (e.g., zxcvbn)

### Secure Password Storage
- Never store passwords in plaintext
- Use slow, memory-hard hashing: **Argon2**, **scrypt**, or **PBKDF2** (with high iterations)
- Always use unique per-user salts

### Transmission
- Always use **TLS/HTTPS** for login and authenticated pages
- Enable **HSTS**

### Multi-Factor Authentication (MFA)
- Implement MFA wherever possible (especially for privileged accounts)
- Prefer TOTP (authenticator apps) or WebAuthn/Passkeys over SMS

### Session Management
- Generate new session ID after successful login
- Use `Secure` + `HttpOnly` cookies
- Implement idle and absolute session timeouts
- Invalidate session on logout

## Important Controls

### Prevent Automated Attacks
- Rate limit login attempts
- Use progressive delay or temporary account lockout
- Implement generic error messages to prevent user enumeration:
  - Correct: `"Invalid username or password"`
  - Wrong: `"User not found"` or `"Incorrect password"`

### Sensitive Actions
- Require re-authentication (password or MFA) before changing email, password, or performing high-risk actions

### Error Handling
- Always return generic messages for failed logins, password resets, and account creation
- Do not reveal whether a username exists

## Signals for RAG Queries
`login`, `password`, `authentication`, `MFA`, `2FA`, `session fixation`, `credential stuffing`, `password spray`, `brute force`, `account lockout`, `password reset`, `session management`

## References
- OWASP Session Management Cheat Sheet
- OWASP Password Storage Cheat Sheet
- NIST SP 800-63B Digital Identity Guidelines