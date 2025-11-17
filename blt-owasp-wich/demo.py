#!/usr/bin/env python3
"""
Demo script to show compliance checker functionality without requiring GitHub API access.
"""

import json


def generate_demo_report():
    """Generate a demo compliance report."""
    
    demo_results = {
        "url": "https://github.com/OWASP/example-project",
        "score": 85,
        "max_score": 100,
        "percentage": 85.0,
        "categories": {
            "General Compliance & Governance": {
                "score": 9,
                "max_score": 10,
                "checks": [
                    {"name": "Clearly defined project goal and scope", "passed": True, "points": 1, "max_points": 1, "details": "Checked README for project description"},
                    {"name": "Open-source license file present", "passed": True, "points": 1, "max_points": 1, "details": "License: Apache-2.0"},
                    {"name": "README file provides project overview", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Under OWASP organization", "passed": True, "points": 1, "max_points": 1, "details": "Repository owner: OWASP"},
                    {"name": "Contribution guidelines (CONTRIBUTING.md)", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Issue tracker is active", "passed": True, "points": 1, "max_points": 1, "details": "Open issues: 12"},
                    {"name": "Active maintainers with recent commits", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Code of Conduct present", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Project roadmap or milestones documented", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Well-governed with active maintainers", "passed": False, "points": 0, "max_points": 1, "details": "Collaborators: 0"},
                ]
            },
            "Documentation & Usability": {
                "score": 8,
                "max_score": 10,
                "checks": [
                    {"name": "Installation guide in README", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Usage examples provided", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Wiki or docs/ directory", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "API documentation available", "passed": False, "points": 0, "max_points": 1, "details": ""},
                    {"name": "Inline code comments present", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Scripts and configuration documented", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "FAQ or troubleshooting guide", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Well-defined error messages", "passed": True, "points": 1, "max_points": 1, "details": "Manual review recommended"},
                    {"name": "Clear versioning strategy", "passed": True, "points": 1, "max_points": 1, "details": "Releases: 5"},
                    {"name": "CHANGELOG maintained", "passed": False, "points": 0, "max_points": 1, "details": ""},
                ]
            },
            "Code Quality & Best Practices": {
                "score": 9,
                "max_score": 10,
                "checks": [
                    {"name": "Code follows style guide", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Uses linters", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Code is modular and maintainable", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Adheres to DRY principle", "passed": True, "points": 1, "max_points": 1, "details": "Manual code review recommended"},
                    {"name": "Secure coding practices followed", "passed": True, "points": 1, "max_points": 1, "details": "Verified by security checks"},
                    {"name": "No hardcoded credentials or secrets", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Uses parameterized queries", "passed": True, "points": 1, "max_points": 1, "details": "Verify manually for SQL databases"},
                    {"name": "Strong cryptographic algorithms", "passed": True, "points": 1, "max_points": 1, "details": "Manual review recommended"},
                    {"name": "Input validation implemented", "passed": True, "points": 1, "max_points": 1, "details": "Verified by security scanning"},
                    {"name": "Output encoding for XSS prevention", "passed": False, "points": 0, "max_points": 1, "details": "Verified by security scanning"},
                ]
            },
            "Security & OWASP Compliance": {
                "score": 13,
                "max_score": 15,
                "checks": [
                    {"name": "Security policy (SECURITY.md)", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Dependency scanning configured", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Uses secure headers (CSP, HSTS, etc.)", "passed": True, "points": 1, "max_points": 1, "details": "Manual review for web applications"},
                    {"name": "Input validation enforced", "passed": True, "points": 1, "max_points": 1, "details": "Requires code review"},
                    {"name": "RBAC implemented where applicable", "passed": True, "points": 1, "max_points": 1, "details": "Manual review recommended"},
                    {"name": "Secure authentication mechanisms", "passed": True, "points": 1, "max_points": 1, "details": "Manual review recommended"},
                    {"name": "Secrets stored securely", "passed": True, "points": 1, "max_points": 1, "details": "Check for .env.example, no .env in repo"},
                    {"name": "Uses HTTPS for communication", "passed": True, "points": 1, "max_points": 1, "details": "Manual verification needed"},
                    {"name": "Adheres to OWASP ASVS", "passed": True, "points": 1, "max_points": 1, "details": "Requires security assessment"},
                    {"name": "Secure cookie attributes", "passed": True, "points": 1, "max_points": 1, "details": "For web applications only"},
                    {"name": "No unnecessary ports exposed", "passed": True, "points": 1, "max_points": 1, "details": "Manual infrastructure review"},
                    {"name": "Logs security events", "passed": True, "points": 1, "max_points": 1, "details": "Verify logging implementation"},
                    {"name": "Least privilege principle", "passed": False, "points": 0, "max_points": 1, "details": "Manual review recommended"},
                    {"name": "No outdated/unsafe dependencies", "passed": True, "points": 1, "max_points": 1, "details": "Run dependency-check tools"},
                    {"name": "Complies with OWASP Top 10", "passed": False, "points": 0, "max_points": 1, "details": "Requires security testing"},
                ]
            },
            "CI/CD & DevSecOps": {
                "score": 9,
                "max_score": 10,
                "checks": [
                    {"name": "Automated unit tests implemented", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Continuous Integration configured", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "CI/CD includes security scanning", "passed": True, "points": 1, "max_points": 1, "details": "Check workflow files for SAST/DAST"},
                    {"name": "Dependency scanning automated", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Code coverage reports generated", "passed": True, "points": 1, "max_points": 1, "details": "Check for coverage tools in CI"},
                    {"name": "Container security scanning", "passed": True, "points": 1, "max_points": 1, "details": "If using containers"},
                    {"name": "IaC security checks", "passed": True, "points": 1, "max_points": 1, "details": "If using IaC tools"},
                    {"name": "Secure secrets management in CI/CD", "passed": True, "points": 1, "max_points": 1, "details": "Verify no secrets in workflows"},
                    {"name": "Environment configurations managed", "passed": True, "points": 1, "max_points": 1, "details": "Check for .env.example"},
                    {"name": "Rollback mechanisms available", "passed": False, "points": 0, "max_points": 1, "details": "Manual deployment review"},
                ]
            },
            "Testing & Validation": {
                "score": 8,
                "max_score": 10,
                "checks": [
                    {"name": "Tests cover edge cases", "passed": True, "points": 1, "max_points": 1, "details": "Requires test review"},
                    {"name": "Unit, integration, and E2E tests", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Uses mocks and stubs", "passed": True, "points": 1, "max_points": 1, "details": "Check test files"},
                    {"name": "Achieves 80%+ test coverage", "passed": True, "points": 1, "max_points": 1, "details": "Run coverage tools"},
                    {"name": "Tests validate input sanitization", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Automated fuzz testing", "passed": False, "points": 0, "max_points": 1, "details": "Advanced feature"},
                    {"name": "Fails gracefully with error logging", "passed": True, "points": 1, "max_points": 1, "details": "Manual verification"},
                    {"name": "No sensitive data in logs", "passed": True, "points": 1, "max_points": 1, "details": "Code review needed"},
                    {"name": "Uses dependency injection", "passed": True, "points": 1, "max_points": 1, "details": "Architecture review"},
                    {"name": "Regression tests for compatibility", "passed": False, "points": 0, "max_points": 1, "details": ""},
                ]
            },
            "Performance & Scalability": {
                "score": 8,
                "max_score": 10,
                "checks": [
                    {"name": "Code optimized for performance", "passed": True, "points": 1, "max_points": 1, "details": "Requires profiling"},
                    {"name": "Asynchronous processing where needed", "passed": True, "points": 1, "max_points": 1, "details": "Architecture review"},
                    {"name": "Caching strategies implemented", "passed": True, "points": 1, "max_points": 1, "details": "Check for cache configuration"},
                    {"name": "Optimized database queries", "passed": True, "points": 1, "max_points": 1, "details": "Database review needed"},
                    {"name": "Rate limiting to prevent abuse", "passed": True, "points": 1, "max_points": 1, "details": "For web services"},
                    {"name": "No memory leaks", "passed": True, "points": 1, "max_points": 1, "details": "Profiling required"},
                    {"name": "Load testing performed", "passed": False, "points": 0, "max_points": 1, "details": "Check for load test scripts"},
                    {"name": "Supports horizontal scaling", "passed": True, "points": 1, "max_points": 1, "details": "Architecture review"},
                    {"name": "Uses lazy loading", "passed": True, "points": 1, "max_points": 1, "details": "Manual code review"},
                    {"name": "Pagination for large datasets", "passed": False, "points": 0, "max_points": 1, "details": "API/UI review"},
                ]
            },
            "Logging & Monitoring": {
                "score": 7,
                "max_score": 10,
                "checks": [
                    {"name": "Logging implemented", "passed": True, "points": 1, "max_points": 1, "details": "Check for logging framework"},
                    {"name": "Configurable log levels", "passed": True, "points": 1, "max_points": 1, "details": "Check configuration files"},
                    {"name": "Logs don't contain sensitive data", "passed": True, "points": 1, "max_points": 1, "details": "Code review required"},
                    {"name": "Monitoring integration", "passed": False, "points": 0, "max_points": 1, "details": "Check for monitoring setup"},
                    {"name": "Structured logging format", "passed": True, "points": 1, "max_points": 1, "details": "Check logging implementation"},
                    {"name": "Audit logs for security actions", "passed": True, "points": 1, "max_points": 1, "details": "Security review needed"},
                    {"name": "Alerts configured", "passed": False, "points": 0, "max_points": 1, "details": "Manual infrastructure check"},
                    {"name": "Log rotation and archival", "passed": True, "points": 1, "max_points": 1, "details": "Operations review"},
                    {"name": "Incident response playbook", "passed": False, "points": 0, "max_points": 1, "details": "Check documentation"},
                    {"name": "Logging config separate from code", "passed": True, "points": 1, "max_points": 1, "details": "Check for config files"},
                ]
            },
            "Community & Support": {
                "score": 9,
                "max_score": 10,
                "checks": [
                    {"name": "Maintainers actively engage", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Security vulnerability reporting process", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Security policy file (SECURITY.md)", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Community guidelines present", "passed": True, "points": 1, "max_points": 1, "details": "Check CODE_OF_CONDUCT.md"},
                    {"name": "Responsive to security issues", "passed": True, "points": 1, "max_points": 1, "details": "Check issue response time"},
                    {"name": "Regular project updates", "passed": True, "points": 1, "max_points": 1, "details": "Last update: 2024-11-15"},
                    {"name": "Multiple support channels", "passed": True, "points": 1, "max_points": 1, "details": "GitHub Discussions enabled"},
                    {"name": "Clear escalation path", "passed": True, "points": 1, "max_points": 1, "details": "Check SECURITY.md"},
                    {"name": "PR reviews before merging", "passed": True, "points": 1, "max_points": 1, "details": "Check branch protection"},
                    {"name": "Good issue tracking hygiene", "passed": False, "points": 0, "max_points": 1, "details": "Open issues: 12"},
                ]
            },
            "Legal & Compliance": {
                "score": 5,
                "max_score": 5,
                "checks": [
                    {"name": "GDPR/CCPA compliance", "passed": True, "points": 1, "max_points": 1, "details": "Manual legal review needed"},
                    {"name": "Dependencies properly licensed", "passed": True, "points": 1, "max_points": 1, "details": "Check third-party licenses"},
                    {"name": "No proprietary/restricted code", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Users informed of data collection", "passed": True, "points": 1, "max_points": 1, "details": ""},
                    {"name": "Responsible disclosure policy", "passed": True, "points": 1, "max_points": 1, "details": ""},
                ]
            }
        }
    }
    
    return demo_results


def print_report(results):
    """Pretty print the compliance report."""
    print("="*80)
    print(f"OWASP Project Compliance Report (DEMO)")
    print("="*80)
    print(f"\nProject URL: {results['url']}")
    print(f"Overall Score: {results['score']}/{results['max_score']} ({results['percentage']}%)")
    print("\n" + "="*80)
    
    for category_name, category_data in results.get('categories', {}).items():
        print(f"\n{category_name}")
        print(f"Score: {category_data['score']}/{category_data['max_score']}")
        print("-" * 80)
        
        for check in category_data['checks']:
            status = "✓" if check['passed'] else "✗"
            points_str = f"({check['points']}/{check['max_points']} pts)"
            print(f"  {status} {check['name']} {points_str}")
            if check['details']:
                print(f"      → {check['details']}")
    
    print("\n" + "="*80)
    if results['percentage'] >= 80:
        print("Status: EXCELLENT COMPLIANCE ✓")
    elif results['percentage'] >= 60:
        print("Status: GOOD COMPLIANCE")
    elif results['percentage'] >= 40:
        print("Status: NEEDS IMPROVEMENT")
    else:
        print("Status: SIGNIFICANT IMPROVEMENTS NEEDED")
    print("="*80)
    
    print("\n💡 This is a demo report showing what the compliance checker generates.")
    print("   To check a real repository, use: python compliance_checker.py <repo-url>")


if __name__ == "__main__":
    results = generate_demo_report()
    print_report(results)
