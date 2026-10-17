# Workflow: How BLT-Preflight Works

This document provides a visual walkthrough of how the BLT-Preflight advisory system works in practice.

## Overview Diagram

```
┌─────────────────┐
│  Contributor    │
│  Opens PR/Issue │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  GitHub Actions         │
│  (advisory.yml)         │
│  - Triggered on PR/Issue│
│  - Collects context     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Advisory Engine        │
│  (core.py)              │
│  - Analyzes labels      │
│  - Matches file patterns│
│  - Loads security config│
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Generate Advisory      │
│  - Select patterns      │
│  - Create recommendations│
│  - Link documentation   │
│  - Apply learning data  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Post Comment to PR     │
│  - Formatted markdown   │
│  - Severity indicators  │
│  - Actionable advice    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Contributor Reviews    │
│  - Reads advisory       │
│  - Updates code         │
│  - Provides feedback    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Learning Loop          │
│  - Records feedback     │
│  - Captures intent      │
│  - Refines guidance     │
└─────────────────────────┘
```

## Step-by-Step Workflow

### Step 1: Contributor Action

**Trigger**: Contributor opens a PR or creates an issue with specific labels

```
Event: Pull Request Opened
Title: "Add OAuth2 authentication support"
Files Changed: 
  - src/auth/oauth.py
  - src/auth/providers.py
Labels: security, authentication
```

### Step 2: GitHub Action Activation

The GitHub Action (`.github/workflows/advisory.yml`) is triggered:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
```

**Actions taken:**
1. Checkout repository
2. Set up Python environment
3. Extract PR context (files, labels)
4. Run advisory engine

### Step 3: Context Extraction

The system extracts:

```python
context = AdvisoryContext(
    issue_labels=["security", "authentication"],
    repo_metadata={
        "repository": "OWASP-BLT/BLT",
        "pr_number": 123,
        "author": "contributor",
        "title": "Add OAuth2 authentication support"
    },
    file_patterns=["src/auth/oauth.py", "src/auth/providers.py"],
    contributor_intent="Add OAuth2 authentication support"
)
```

### Step 4: Pattern Matching

The engine matches against configured patterns:

```json
{
  "file_patterns": {
    "authentication": {
      "patterns": ["**/auth/**"],
      "severity": "critical"
    }
  },
  "label_patterns": {
    "security": {
      "severity": "critical"
    },
    "authentication": {
      "severity": "critical"
    }
  }
}
```

**Matches found:**
- ✓ File pattern: `authentication` (files in `auth/` directory)
- ✓ Label pattern: `security`
- ✓ Label pattern: `authentication`

### Step 5: Advisory Generation

For each match, the engine generates advice:

```python
advice = SecurityAdvice(
    severity="critical",
    title="Security Advisory: Authentication",
    message="Authentication changes require careful review...",
    recommendations=[
        "Use multi-factor authentication where possible",
        "Implement proper session management",
        ...
    ],
    documentation_links=[
        "https://cheatsheetseries.owasp.org/...",
        ...
    ]
)
```

### Step 6: Learning Loop Integration

Before finalizing, the engine:

1. Checks past feedback for this pattern
2. Adjusts guidance based on effectiveness
3. Incorporates historical patterns

```python
# If pattern had low helpfulness in past:
if avg_helpful < 0.5:
    advice.message += "\n\nNote: This guidance is being refined..."
```

### Step 7: Report Formatting

The engine formats advice into markdown:

```markdown
# 🛡️ BLT Preflight Security Advisory

## 🔴 Critical Security Considerations

### Security Advisory: Authentication
...
```

### Step 8: Comment Posting

The GitHub Action posts the advisory as a PR comment:

```javascript
// Check for existing advisory comment
// If exists: update it
// If not: create new comment

await github.rest.issues.createComment({
  owner: context.repo.owner,
  repo: context.repo.repo,
  issue_number: pr_number,
  body: advisory
});
```

### Step 9: Contributor Review

The contributor sees the advisory and:

1. **Reads recommendations**
   - Reviews each security recommendation
   - Checks linked documentation

2. **Takes action**
   - Updates code to address concerns
   - Implements suggested security measures
   - Asks questions if unclear

3. **Provides feedback**
   - Comments on advisory helpfulness
   - Suggests improvements

### Step 10: Feedback Recording

Contributors can record structured feedback:

```bash
python3 src/blt_preflight.py feedback \
  --pattern "Security Advisory: Authentication" \
  --helpful yes \
  --comments "OAuth2 recommendations were spot-on"
```

This is stored in `config/learning_data.json`:

```json
{
  "feedback": [
    {
      "pattern": "Security Advisory: Authentication",
      "helpful": 1,
      "comments": "OAuth2 recommendations were spot-on",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Step 11: Dashboard Updates

Maintainers can view aggregated metrics:

```bash
python3 src/blt_preflight.py dashboard
```

Output:
```
📊 BLT Preflight Maintainer Dashboard

Overview:
- Total Advisory Feedback: 42
- Helpful Rate: 85.7%
- Total Intents Captured: 28

Pattern Effectiveness:
1. Authentication - 0.92 effectiveness
2. API Keys - 0.88 effectiveness
...
```

### Step 12: Continuous Improvement

The system learns and improves:

1. **High effectiveness patterns**: Kept as-is
2. **Low effectiveness patterns**: Flagged for review
3. **Common intents**: Used to identify new patterns
4. **Feedback comments**: Inform guidance updates

## Data Flow

```
PR/Issue → Context → Pattern Matching → Advisory Generation
                                              │
                                              ▼
                                        Learning Data
                                              │
                                              ▼
                                    Future Refinements
```

## Example Timeline

**Day 1:**
- PR opened with auth changes
- Advisory posted within 2 minutes
- Contributor reads and updates code

**Day 2:**
- Contributor provides feedback: "helpful"
- Feedback recorded in learning data

**Week 1:**
- 10 similar PRs processed
- Average helpfulness: 90%
- Pattern kept unchanged

**Month 1:**
- Dashboard shows pattern effectiveness
- Maintainers review low-performing patterns
- Configuration updated based on insights

## Benefits

### For Contributors
- ✅ Clear security guidance upfront
- ✅ Learning opportunity
- ✅ Reduced back-and-forth with maintainers
- ✅ Confidence in security approach

### For Maintainers
- ✅ Reduced manual security review effort
- ✅ Consistent security guidance
- ✅ Data-driven insights
- ✅ Proactive issue prevention

### For the Project
- ✅ Improved security posture
- ✅ Better contributor education
- ✅ Reduced security vulnerabilities
- ✅ Enhanced collaboration

## Customization Points

The workflow can be customized at:

1. **Trigger events** (`.github/workflows/advisory.yml`)
2. **Security patterns** (`config/security_patterns.json`)
3. **Recommendations** (`src/advisory_engine/core.py`)
4. **Documentation links** (`src/advisory_engine/core.py`)
5. **Dashboard metrics** (`src/advisory_engine/dashboard.py`)

## Summary

BLT-Preflight creates a **virtuous cycle**:

1. Contributors get immediate security guidance
2. They learn and improve their code
3. They provide feedback on guidance quality
4. The system learns and refines advice
5. Future contributors get better guidance

This cycle **continuously improves** both the system and contributor security knowledge.
