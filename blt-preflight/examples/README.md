# BLT-Preflight Examples

This directory contains practical examples demonstrating the BLT-Preflight advisory system.

## Available Examples

### 1. [Authentication Example](authentication_example.md)

Demonstrates how the system provides guidance for authentication-related changes.

**Key Patterns:**
- File pattern matching (`**/auth/**`)
- Security labels (`security`, `authentication`)
- Critical severity advisories
- Authentication-specific recommendations

**Use Case:** Contributor modifying login or password reset functionality

### 2. [API Example](api_example.md)

Shows guidance provided for API endpoint changes.

**Key Patterns:**
- API endpoint pattern matching
- Warning severity advisories
- Input validation and rate limiting guidance
- Intent capture demonstration

**Use Case:** Contributor adding or modifying REST API endpoints

## How to Use These Examples

### Running Locally

Each example includes commands you can run locally to see the advisory in action:

```bash
# Authentication example
python3 src/blt_preflight.py advise \
  --labels "security,authentication" \
  --files "src/auth/login.py,src/auth/password_reset.py" \
  --repo "OWASP-BLT/BLT" \
  --output examples/advisory_authentication.md

# API example
python3 src/blt_preflight.py advise \
  --labels "api" \
  --files "src/api/v2/users.py,src/routes/payment.py" \
  --repo "OWASP-BLT/BLT" \
  --output examples/advisory_api.md
```

### Creating Your Own Examples

To create examples for your project:

1. **Identify Common Patterns**
   - Review past PRs for recurring security concerns
   - Note file types that require special attention
   - Document security-related labels in use

2. **Create Test Scenarios**
   ```bash
   python3 src/blt_preflight.py advise \
     --labels "your,labels" \
     --files "your/files.py" \
     --output examples/your_example.md
   ```

3. **Document the Pattern**
   - Explain the scenario
   - Show the generated advisory
   - Provide context for contributors
   - Include feedback mechanism

## Common Scenarios

### Database Changes

```bash
python3 src/blt_preflight.py advise \
  --labels "database" \
  --files "db/migrations/001_add_users.sql" \
  --output examples/advisory_database.md
```

**Expected Advisory:**
- SQL injection prevention
- Parameterized queries
- Access control considerations

### File Upload Features

```bash
python3 src/blt_preflight.py advise \
  --files "src/upload/handler.py,src/storage/files.py" \
  --output examples/advisory_file_upload.md
```

**Expected Advisory:**
- File type validation
- Size limits
- Malware scanning

### Encryption Implementation

```bash
python3 src/blt_preflight.py advise \
  --files "src/crypto/encryption.py" \
  --labels "encryption" \
  --output examples/advisory_encryption.md
```

**Expected Advisory:**
- Use established libraries
- Strong key lengths
- Key management

## Testing Pattern Effectiveness

Use examples to test pattern effectiveness:

1. **Generate Advisory**
   ```bash
   python3 src/blt_preflight.py advise \
     --labels "test-label" \
     --files "test/file.py"
   ```

2. **Review Output**
   - Is the guidance relevant?
   - Are recommendations actionable?
   - Are documentation links helpful?

3. **Provide Feedback**
   ```bash
   python3 src/blt_preflight.py feedback \
     --pattern "Pattern Name" \
     --helpful yes \
     --comments "Specific feedback"
   ```

4. **Check Dashboard**
   ```bash
   python3 src/blt_preflight.py dashboard
   ```

## Real-World Example Flow

### Scenario: New Contributor Adding OAuth2 Support

1. **Contributor Opens PR**
   - Files: `src/auth/oauth.py`, `src/auth/providers/google.py`
   - Labels: `authentication`, `oauth`
   - Intent: "Adding Google OAuth2 authentication"

2. **Advisory Generated**
   ```markdown
   # 🛡️ BLT Preflight Security Advisory
   
   ## 🔴 Critical Security Considerations
   
   ### Security Advisory: Authentication
   Authentication changes require careful review...
   ```

3. **Contributor Actions**
   - Reads recommendations
   - Reviews OWASP Authentication Cheat Sheet
   - Implements token validation
   - Adds rate limiting
   - Updates PR

4. **Feedback Provided**
   ```bash
   python3 src/blt_preflight.py feedback \
     --pattern "Security Advisory: Authentication" \
     --helpful yes \
     --comments "OAuth2 recommendations were perfect"
   ```

5. **Learning Loop**
   - Feedback recorded
   - Pattern effectiveness tracked
   - Future advice refined

## Example Output Format

All advisories follow this format:

```markdown
# 🛡️ BLT Preflight Security Advisory

## [Severity Level] Security [Type]

### [Advisory Title]

[Guidance Message]

**Recommendations:**
- Recommendation 1
- Recommendation 2
- ...

**Learn more:**
- Documentation Link 1
- Documentation Link 2
- ...
```

## Severity Indicators

- 🔴 **Critical**: Immediate security concern, careful review required
- 🟡 **Warning**: Important consideration, review recommended  
- 🔵 **Info**: General guidance, good to know

## Contributing Examples

To contribute new examples:

1. Create a scenario that others might encounter
2. Generate the advisory
3. Document the context and expected outcome
4. Submit a PR with your example

## Resources

- [Security Guidance](../docs/SECURITY_GUIDANCE.md)
- [Configuration Guide](../docs/CONFIGURATION.md)
- [Workflow Documentation](../docs/WORKFLOW.md)
- [Extension Guide](../docs/EXTENDING.md)

## Feedback

Found these examples helpful? Have suggestions for new examples? Open an issue with the `examples` label!

---

*Examples help everyone understand how BLT-Preflight works in practice.*
