# BLT Preflight Configuration Guide

This guide explains how to configure the BLT Preflight advisory system for your repository.

## Configuration Files

### security_patterns.json

The main configuration file that defines security patterns and their associated guidance.

**Location**: `config/security_patterns.json`

**Structure**:
```json
{
  "file_patterns": {
    "pattern_name": {
      "patterns": ["glob", "patterns"],
      "severity": "info|warning|critical",
      "guidance": "Plain-language guidance message"
    }
  },
  "label_patterns": {
    "label_name": {
      "severity": "info|warning|critical",
      "guidance": "Plain-language guidance message"
    }
  }
}
```

### Severity Levels

- **info**: General information, no immediate security concern
- **warning**: Potential security consideration, review recommended
- **critical**: High-priority security concern, careful review required

## File Patterns

File patterns use glob syntax to match file paths:

- `*` - Matches any characters within a path segment
- `**` - Matches any characters across multiple path segments
- `?` - Matches a single character
- `[abc]` - Matches any character in brackets

**Examples**:
```json
{
  "authentication": {
    "patterns": [
      "**/auth/**",        // Matches any file in auth directory
      "**/login.js",       // Matches login.js in any directory
      "**/*password*"      // Matches files with 'password' in name
    ],
    "severity": "critical",
    "guidance": "Authentication changes require careful review"
  }
}
```

## Label Patterns

Label patterns match GitHub issue/PR labels exactly (case-insensitive).

**Examples**:
```json
{
  "security": {
    "severity": "critical",
    "guidance": "Security-related changes require thorough review"
  },
  "api": {
    "severity": "warning",
    "guidance": "API changes should include input validation"
  }
}
```

## Customizing Patterns

### Adding New Patterns

1. Edit `config/security_patterns.json`
2. Add your pattern under `file_patterns` or `label_patterns`
3. Specify severity and guidance
4. Commit the changes

**Example** - Adding a pattern for payment processing:
```json
{
  "file_patterns": {
    "payment": {
      "patterns": [
        "**/payment/**",
        "**/billing/**",
        "**/*stripe*",
        "**/*paypal*"
      ],
      "severity": "critical",
      "guidance": "Payment processing requires PCI DSS compliance and secure handling of financial data"
    }
  }
}
```

### Modifying Existing Patterns

To change guidance for an existing pattern:

1. Locate the pattern in `config/security_patterns.json`
2. Update the `guidance` text
3. Optionally adjust `severity` level
4. Commit changes

### Removing Patterns

To disable a pattern:

1. Remove the pattern from `config/security_patterns.json`, or
2. Change severity to `"info"` to make it less prominent

## Recommendations and Documentation

The advisory engine provides context-specific recommendations and documentation links based on matched patterns. These are defined in the code (`src/advisory_engine/core.py`) in the following methods:

- `_get_recommendations()` - Returns recommendation lists
- `_get_documentation_links()` - Returns relevant OWASP/security documentation

To customize these:

1. Edit `src/advisory_engine/core.py`
2. Update the dictionaries in these methods
3. Add your pattern key and associated recommendations/links

## GitHub Action Configuration

The GitHub Action is configured in `.github/workflows/advisory.yml`.

### Trigger Events

By default, the advisory runs on:
- Pull request opened, synchronized, or reopened
- Issues opened or labeled

To modify triggers, edit the `on:` section:
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main, develop]  # Limit to specific branches
  issues:
    types: [opened, labeled]
```

### Permissions

The workflow requires these permissions:
```yaml
permissions:
  pull-requests: write  # To comment on PRs
  issues: write         # To comment on issues
  contents: read        # To read repository files
```

### Disabling the Action

To temporarily disable the advisory:

1. Rename `.github/workflows/advisory.yml` to `advisory.yml.disabled`, or
2. Delete the workflow file

## Learning Loop

The system learns from feedback over time and stores data in `config/learning_data.json`.

### Data Collected

- **Feedback**: Whether advice was helpful
- **Intents**: Contributor-stated intentions
- **Patterns**: Historical pattern matches

### Using Learning Data

The learning data influences:
- Future advisory refinement
- Maintainer dashboard insights
- Pattern effectiveness metrics

### Privacy

Learning data does not include:
- Personal information
- Code content
- Sensitive project details

Only metadata about patterns and feedback is stored.

## Maintainer Dashboard

Generate a dashboard to view advisory statistics:

```bash
python3 src/blt_preflight.py dashboard --output docs/MAINTAINER_DASHBOARD.md
```

The dashboard shows:
- Feedback statistics
- Pattern effectiveness
- Contributor intent patterns
- Recommendations for improvement

### Automating Dashboard Updates

Add to your GitHub Action workflow:
```yaml
- name: Update dashboard
  run: |
    python3 src/blt_preflight.py dashboard --output docs/MAINTAINER_DASHBOARD.md
    
- name: Commit dashboard
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add docs/MAINTAINER_DASHBOARD.md
    git commit -m "Update maintainer dashboard" || true
    git push || true
```

## CLI Usage

The CLI provides direct access to the advisory engine.

### Generate Advisory

```bash
python3 src/blt_preflight.py advise \
  --labels "security,authentication" \
  --files "src/auth.py,src/login.py" \
  --output advisory.md
```

### Record Feedback

```bash
python3 src/blt_preflight.py feedback \
  --pattern "Security Advisory: Authentication" \
  --helpful yes \
  --comments "Clear and actionable"
```

### Capture Intent

```bash
python3 src/blt_preflight.py intent \
  --intent "Adding OAuth2 support for third-party authentication" \
  --labels "authentication,oauth" \
  --files "src/oauth.py"
```

## Testing Configuration

Test your configuration locally before committing:

```bash
# Test with sample file patterns
python3 src/blt_preflight.py advise \
  --files "test/auth/login.py,test/api/endpoints.py" \
  --labels "security"

# Test with your actual PR files
python3 src/blt_preflight.py advise \
  --files "$(git diff --name-only origin/main...HEAD | tr '\n' ',')" \
  --labels "security,api"
```

## Best Practices

1. **Start Conservative**: Begin with fewer patterns and add more as needed
2. **Clear Guidance**: Write guidance in plain language, avoid jargon
3. **Link Documentation**: Always provide relevant documentation links
4. **Iterate**: Use feedback to improve patterns over time
5. **Review Regularly**: Check the maintainer dashboard monthly
6. **Be Helpful**: Remember the goal is to help contributors, not block them

## Troubleshooting

### Advisory Not Appearing

1. Check workflow is enabled in `.github/workflows/advisory.yml`
2. Verify permissions in workflow file
3. Check workflow runs in Actions tab
4. Ensure Python and dependencies install successfully

### Patterns Not Matching

1. Test patterns locally with CLI
2. Verify glob syntax (use `**` for recursive matching)
3. Check for typos in pattern names
4. Ensure severity levels are valid

### Configuration Not Loading

1. Verify `config/security_patterns.json` is valid JSON
2. Check file path in code is correct
3. Ensure file is committed to repository

## Examples

See `examples/` directory for:
- Sample configurations
- Example PRs with advisory responses
- Common pattern collections

## Support

- **Issues**: Open a GitHub issue with the `configuration` label
- **Questions**: Check existing issues or documentation
- **Contributions**: PRs welcome to improve configuration options

---

*Configuration is key to an effective advisory system. Start simple and iterate based on your project's needs.*
