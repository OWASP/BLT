# Extending BLT-Preflight

This guide shows how to extend and customize BLT-Preflight for your specific needs.

## Adding New Security Patterns

### Step 1: Identify the Pattern

Decide what security concern you want to address:
- Specific file types or directories
- Particular security labels
- Common vulnerability patterns

**Example**: Adding guidance for payment processing

### Step 2: Add File Patterns

Edit `config/security_patterns.json`:

```json
{
  "file_patterns": {
    "payment_processing": {
      "patterns": [
        "**/payment/**",
        "**/billing/**",
        "**/*stripe*",
        "**/*paypal*",
        "**/checkout/**"
      ],
      "severity": "critical",
      "guidance": "Payment processing requires PCI DSS compliance and secure handling of financial data. Never store full credit card numbers or CVV codes."
    }
  }
}
```

### Step 3: Add Label Patterns

```json
{
  "label_patterns": {
    "payment": {
      "severity": "critical",
      "guidance": "Payment-related changes must comply with PCI DSS standards"
    },
    "pci-compliance": {
      "severity": "critical",
      "guidance": "Ensure all payment card data handling follows PCI DSS requirements"
    }
  }
}
```

### Step 4: Add Custom Recommendations

Edit `src/advisory_engine/core.py`:

```python
def _get_recommendations(self, pattern_key: str, severity: str) -> List[str]:
    recommendations = {
        # ... existing patterns ...
        "payment_processing": [
            "Never store full credit card numbers",
            "Use tokenization for card data",
            "Implement PCI DSS security controls",
            "Use TLS 1.2+ for all payment transactions",
            "Log all payment operations securely",
            "Implement fraud detection mechanisms"
        ]
    }
    return recommendations.get(pattern_key, default_recommendations)
```

### Step 5: Add Documentation Links

```python
def _get_documentation_links(self, pattern_key: str) -> List[str]:
    docs = {
        # ... existing patterns ...
        "payment_processing": [
            "https://www.pcisecuritystandards.org/pci_security/",
            "https://cheatsheetseries.owasp.org/cheatsheets/Payment_Card_Industry_Data_Security_Standard_Cheat_Sheet.html",
            "https://stripe.com/docs/security/best-practices"
        ]
    }
    return docs.get(pattern_key, default_docs)
```

## Adding Industry-Specific Patterns

### Healthcare (HIPAA)

```json
{
  "file_patterns": {
    "patient_data": {
      "patterns": [
        "**/patient/**",
        "**/medical/**",
        "**/health/**",
        "**/*phi*"
      ],
      "severity": "critical",
      "guidance": "Patient health information (PHI) must comply with HIPAA privacy and security rules"
    }
  },
  "label_patterns": {
    "hipaa": {
      "severity": "critical",
      "guidance": "HIPAA compliance required for all patient data handling"
    }
  }
}
```

### Financial Services (SOX)

```json
{
  "file_patterns": {
    "financial_reporting": {
      "patterns": [
        "**/financial/**",
        "**/accounting/**",
        "**/audit/**"
      ],
      "severity": "critical",
      "guidance": "Financial data changes must maintain SOX compliance and audit trails"
    }
  }
}
```

### Privacy Regulations (GDPR/CCPA)

```json
{
  "file_patterns": {
    "personal_data": {
      "patterns": [
        "**/user/data/**",
        "**/privacy/**",
        "**/consent/**",
        "**/*pii*"
      ],
      "severity": "critical",
      "guidance": "Personal data handling must comply with GDPR, CCPA, and other privacy regulations"
    }
  }
}
```

## Custom Advisory Logic

### Advanced Pattern Matching

Create custom logic in `src/advisory_engine/core.py`:

```python
def _evaluate_advanced_patterns(self, context: AdvisoryContext) -> List[SecurityAdvice]:
    """Custom logic for complex pattern evaluation."""
    advice_list = []
    
    # Example: Check for multiple security-sensitive patterns in same PR
    auth_files = [f for f in context.file_patterns if 'auth' in f.lower()]
    db_files = [f for f in context.file_patterns if 'db' in f.lower()]
    
    if auth_files and db_files:
        advice_list.append(SecurityAdvice(
            severity="critical",
            title="Combined Security Advisory: Authentication + Database",
            message="Changes affecting both authentication and database require extra scrutiny",
            recommendations=[
                "Review authentication and database interaction patterns",
                "Ensure secure credential storage",
                "Verify proper SQL injection prevention",
                "Test authentication flows thoroughly"
            ],
            documentation_links=[
                "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html",
                "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
            ],
            timestamp=datetime.utcnow().isoformat()
        ))
    
    return advice_list
```

### Context-Aware Guidance

```python
def _adjust_for_contributor_experience(
    self, advice_list: List[SecurityAdvice], context: AdvisoryContext
) -> List[SecurityAdvice]:
    """Adjust advice based on contributor experience level."""
    
    # Check if contributor is new (could check via GitHub API)
    is_new_contributor = context.repo_metadata.get('is_new_contributor', False)
    
    if is_new_contributor:
        # Add more detailed, beginner-friendly advice
        for advice in advice_list:
            if advice.severity == "critical":
                advice.message += "\n\n**New Contributor Tip**: This is a security-critical area. Don't hesitate to ask questions or request a security review from maintainers."
    
    return advice_list
```

## Integrating External Tools

### Static Analysis Integration

```python
def run_static_analysis(file_paths: List[str]) -> Dict[str, List[str]]:
    """Run static analysis tools and return findings."""
    findings = {}
    
    # Example: Run Bandit for Python files
    python_files = [f for f in file_paths if f.endswith('.py')]
    if python_files:
        # Run bandit (pseudo-code)
        # results = subprocess.run(['bandit', '-r', ...])
        # findings['bandit'] = parse_results(results)
        pass
    
    return findings

# Integrate in advisory generation
def evaluate_context(self, context: AdvisoryContext) -> List[SecurityAdvice]:
    advice_list = []
    
    # ... existing pattern matching ...
    
    # Add static analysis findings
    static_findings = run_static_analysis(context.file_patterns)
    if static_findings:
        advice_list.append(self._create_static_analysis_advice(static_findings))
    
    return advice_list
```

### Dependency Vulnerability Checking

```python
def check_dependencies(file_paths: List[str]) -> List[SecurityAdvice]:
    """Check for vulnerable dependencies."""
    advice_list = []
    
    # Look for dependency files
    dep_files = [f for f in file_paths if f in ['requirements.txt', 'package.json', 'Gemfile']]
    
    for dep_file in dep_files:
        # Run security audit (pseudo-code)
        # For Python: pip-audit
        # For Node: npm audit
        # For Ruby: bundle audit
        
        vulnerabilities = check_for_vulnerabilities(dep_file)
        if vulnerabilities:
            advice_list.append(SecurityAdvice(
                severity="warning",
                title="Dependency Vulnerabilities Detected",
                message=f"Found {len(vulnerabilities)} known vulnerabilities in dependencies",
                recommendations=[
                    "Run security audit on dependencies",
                    "Update vulnerable packages",
                    "Review security advisories"
                ],
                documentation_links=[
                    "https://owasp.org/www-project-dependency-check/"
                ],
                timestamp=datetime.utcnow().isoformat()
            ))
    
    return advice_list
```

## Custom Dashboard Metrics

### Add Custom Metrics

Edit `src/advisory_engine/dashboard.py`:

```python
def _generate_custom_metrics(self) -> str:
    """Generate custom metrics for your project."""
    lines = []
    
    # Example: Track security labels over time
    security_prs = self._count_security_labeled_prs()
    lines.append(f"- **Security-Labeled PRs (This Month)**: {security_prs}")
    
    # Example: Track time to address security issues
    avg_time = self._calculate_avg_resolution_time()
    lines.append(f"- **Avg Time to Address Security Issues**: {avg_time} hours")
    
    # Example: Top security contributors
    top_contributors = self._get_top_security_contributors()
    lines.append("\n**Top Security Contributors:**\n")
    for name, count in top_contributors[:5]:
        lines.append(f"- {name}: {count} security contributions")
    
    return "\n".join(lines)
```

## Webhook Integration

### Slack Notifications

Create `src/advisory_engine/notifications.py`:

```python
import requests
from typing import List
from .core import SecurityAdvice

class SlackNotifier:
    """Send advisory notifications to Slack."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def notify_critical_advisory(self, advice_list: List[SecurityAdvice], pr_url: str):
        """Notify on critical security advisories."""
        critical = [a for a in advice_list if a.severity == "critical"]
        
        if not critical:
            return
        
        message = {
            "text": f"🔴 Critical Security Advisory",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Critical security patterns detected in PR*\n<{pr_url}|View PR>"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Patterns:*\n" + "\n".join([a.title for a in critical])
                        }
                    ]
                }
            ]
        }
        
        requests.post(self.webhook_url, json=message)
```

## Multi-Language Support

### Add Language-Specific Patterns

```json
{
  "file_patterns": {
    "python_security": {
      "patterns": ["**/*.py"],
      "language": "python",
      "severity": "warning",
      "guidance": "Python security considerations",
      "recommendations": [
        "Use parameterized queries with SQLAlchemy",
        "Validate user input with pydantic or marshmallow",
        "Use secrets module for cryptographic operations"
      ]
    },
    "javascript_security": {
      "patterns": ["**/*.js", "**/*.ts"],
      "language": "javascript",
      "severity": "warning",
      "guidance": "JavaScript security considerations",
      "recommendations": [
        "Sanitize user input to prevent XSS",
        "Use helmet.js for Express security",
        "Implement CSRF protection"
      ]
    }
  }
}
```

## Testing Custom Extensions

### Unit Tests

Create `tests/test_custom_patterns.py`:

```python
import unittest
from advisory_engine.core import AdvisoryEngine, AdvisoryContext

class TestCustomPatterns(unittest.TestCase):
    
    def test_payment_pattern(self):
        """Test payment processing pattern."""
        engine = AdvisoryEngine()
        
        context = AdvisoryContext(
            issue_labels=["payment"],
            repo_metadata={},
            file_patterns=["src/payment/checkout.py"]
        )
        
        advice_list = engine.evaluate_context(context)
        
        # Verify payment advisory is generated
        payment_advice = [a for a in advice_list if "payment" in a.title.lower()]
        self.assertTrue(len(payment_advice) > 0)
        self.assertEqual(payment_advice[0].severity, "critical")
```

## Best Practices for Extensions

1. **Start Simple**: Add patterns incrementally
2. **Test Thoroughly**: Validate each new pattern
3. **Document Well**: Explain custom patterns in comments
4. **Monitor Effectiveness**: Track feedback for new patterns
5. **Iterate**: Refine based on contributor feedback
6. **Version Control**: Track pattern evolution over time

## Example: Complete Custom Pattern

Here's a complete example for blockchain/crypto projects:

```json
{
  "file_patterns": {
    "smart_contracts": {
      "patterns": [
        "**/*.sol",
        "**/contracts/**",
        "**/blockchain/**"
      ],
      "severity": "critical",
      "guidance": "Smart contract changes require security audits and formal verification"
    },
    "wallet_operations": {
      "patterns": [
        "**/wallet/**",
        "**/*wallet*",
        "**/keys/**"
      ],
      "severity": "critical",
      "guidance": "Wallet and key management must follow cryptocurrency security best practices"
    }
  },
  "label_patterns": {
    "smart-contract": {
      "severity": "critical",
      "guidance": "Smart contract security is critical - consider professional audit"
    },
    "defi": {
      "severity": "critical",
      "guidance": "DeFi protocols require special attention to reentrancy, oracle, and economic attacks"
    }
  }
}
```

## Support

For help with extensions:
- Review existing patterns in `config/security_patterns.json`
- Check `src/advisory_engine/core.py` for implementation details
- Open an issue with the `extension` label
- Consult [CONFIGURATION.md](CONFIGURATION.md)

---

*The flexibility of BLT-Preflight allows it to adapt to any project's security needs.*
