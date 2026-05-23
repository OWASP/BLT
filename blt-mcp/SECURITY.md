# Security Policy

## Supported Versions

Currently, only the latest version of BLT-MCP is supported for security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of BLT-MCP seriously. If you believe you have found a security vulnerability, please report it to us as follows:

1. **Do not** open a public GitHub issue.
2. Send an email to the project maintainers (see the OWASP project page for contact details).
3. Provide a detailed description of the vulnerability and steps to reproduce it.

### What to Expect

- You will receive an acknowledgment of your report within 48-72 hours.
- We will work with you to understand the issue and develop a fix.
- We will coordinate a disclosure timeline with you.

## Best Practices for Users

- **Protect your API Keys**: Always use environment variables for `BLT_API_KEY`. Never hardcode keys or commit them to your repository.
- **Run in Isolated Environments**: When testing AI agents with write access to BLT, consider using a staging or test environment first.
- **Review Tool Calls**: Many MCP clients allow you to review tool calls before they are executed. We recommend enabling this for tools like `submit_issue` or `award_bacon`.
