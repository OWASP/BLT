#!/usr/bin/env python3
"""
BLT Preflight CLI - Command-line interface for the advisory engine.

Run as a pre-commit check with: pf
"""

import argparse
import json
import subprocess
import sys
import os

# Add parent directory to path so the package is importable both when run
# directly (python3 src/blt_preflight.py) and when installed via setup.py.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

from advisory_engine.core import AdvisoryEngine, AdvisoryContext
from advisory_engine.github_integration import GitHubIntegration
from advisory_engine.dashboard import MaintainerDashboard


def cmd_advise(args):
    """Generate advisory for given context."""
    engine = AdvisoryEngine(args.config)
    
    # Build context
    labels = args.labels.split(',') if args.labels else []
    files = args.files.split(',') if args.files else []
    
    context = AdvisoryContext(
        issue_labels=labels,
        repo_metadata={'repository': args.repo or 'unknown'},
        file_patterns=files,
        contributor_intent=args.intent
    )
    
    # Generate advice
    advice_list = engine.evaluate_context(context)
    
    # Generate report
    report = engine.generate_report(advice_list)
    
    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Advisory written to {args.output}")
    else:
        print(report)
    
    # Also output as JSON if requested
    if args.json:
        json_output = {
            'advice': [
                {
                    'severity': a.severity,
                    'title': a.title,
                    'message': a.message,
                    'recommendations': a.recommendations,
                    'documentation_links': a.documentation_links,
                    'timestamp': a.timestamp
                }
                for a in advice_list
            ]
        }
        json_file = args.json
        with open(json_file, 'w') as f:
            json.dump(json_output, f, indent=2)
        print(f"JSON output written to {json_file}")


def cmd_github(args):
    """Run GitHub integration."""
    integration = GitHubIntegration()
    
    # Get PR context
    context = integration.get_pr_context()
    
    if not context:
        print("Error: Could not extract PR context from GitHub event")
        sys.exit(1)
    
    # Generate advice
    advice_list = integration.engine.evaluate_context(context)
    
    # Generate report
    report = integration.engine.generate_report(advice_list)
    
    # Post comment
    if integration.post_advisory_comment(report):
        print("Advisory posted successfully")
    else:
        print("Error posting advisory")
        sys.exit(1)


def cmd_feedback(args):
    """Record feedback on advisory."""
    engine = AdvisoryEngine(args.config)
    
    helpful = args.helpful.lower() in ['yes', 'y', 'true', '1']
    
    engine.record_feedback(
        advice_title=args.pattern,
        helpful=helpful,
        comments=args.comments or ""
    )
    
    print(f"Feedback recorded for pattern: {args.pattern}")


def cmd_intent(args):
    """Capture contributor intent."""
    engine = AdvisoryEngine(args.config)
    
    labels = args.labels.split(',') if args.labels else []
    files = args.files.split(',') if args.files else []
    
    context = AdvisoryContext(
        issue_labels=labels,
        repo_metadata={},
        file_patterns=files
    )
    
    engine.capture_intent(args.intent, context)
    print("Intent captured successfully")


def cmd_dashboard(args):
    """Generate maintainer dashboard."""
    dashboard = MaintainerDashboard()
    
    if args.output:
        dashboard.export_dashboard(args.output)
    else:
        print(dashboard.generate_dashboard())


def _get_staged_files():
    """Return a list of files staged for commit (git diff --cached)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        return files
    except subprocess.CalledProcessError:
        return []
    except FileNotFoundError:
        # git not available
        return []


def cmd_check(args):
    """Run a pre-commit security check on staged (or specified) files.

    Exits with code 0 when there are no critical advisories, or 1 when
    critical issues are found, matching the behaviour expected by git hooks
    and CI pipelines.
    """
    # Resolve the files to check
    if args.files:
        files = [f.strip() for f in args.files.split(',') if f.strip()]
    else:
        files = _get_staged_files()

    if not files:
        print("pf: no staged files found – nothing to check.")
        sys.exit(0)

    print(f"pf: checking {len(files)} file(s)…\n")

    engine = AdvisoryEngine(args.config)

    context = AdvisoryContext(
        issue_labels=[],
        repo_metadata={},
        file_patterns=files,
    )

    advice_list = engine.evaluate_context(context)
    report = engine.generate_report(advice_list)
    print(report)

    # Mirror pre-commit behaviour: non-zero exit when critical issues exist
    has_critical = any(a.severity == "critical" for a in advice_list)
    if has_critical:
        print("\npf: ⚠️  critical security advisories found – please review before committing.")
        sys.exit(1)

    print("\npf: ✅ no critical security issues detected.")
    sys.exit(0)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='BLT Preflight - pre-commit security advisory check',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run as a pre-commit check on all staged files (default when no command given)
  pf

  # Check specific files
  pf check --files "src/auth.py,src/login.py"

  # Generate advisory for authentication changes
  pf advise --labels security,authentication --files "src/auth.py,src/login.py"
  
  # Run GitHub integration
  pf github
  
  # Record feedback
  pf feedback --pattern "Security Advisory: Authentication" --helpful yes
  
  # Generate dashboard
  pf dashboard --output docs/MAINTAINER_DASHBOARD.md
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Check command (pre-commit style)
    check_parser = subparsers.add_parser(
        'check',
        help='Run pre-commit security check on staged (or specified) files'
    )
    check_parser.add_argument('--files', help='Comma-separated file paths to check (defaults to git staged files)')
    check_parser.add_argument('--config', default='config/security_patterns.json',
                              help='Path to configuration file')
    check_parser.set_defaults(func=cmd_check)
    
    # Advise command
    advise_parser = subparsers.add_parser('advise', help='Generate security advisory')
    advise_parser.add_argument('--labels', help='Comma-separated issue labels')
    advise_parser.add_argument('--files', help='Comma-separated file patterns')
    advise_parser.add_argument('--intent', help='Contributor intent')
    advise_parser.add_argument('--repo', help='Repository name')
    advise_parser.add_argument('--config', default='config/security_patterns.json',
                               help='Path to configuration file')
    advise_parser.add_argument('--output', help='Output file for advisory')
    advise_parser.add_argument('--json', help='Output JSON to file')
    advise_parser.set_defaults(func=cmd_advise)
    
    # GitHub command
    github_parser = subparsers.add_parser('github', help='Run GitHub integration')
    github_parser.set_defaults(func=cmd_github)
    
    # Feedback command
    feedback_parser = subparsers.add_parser('feedback', help='Record feedback')
    feedback_parser.add_argument('--pattern', required=True, help='Advisory pattern name')
    feedback_parser.add_argument('--helpful', required=True, 
                                 choices=['yes', 'no', 'y', 'n', 'true', 'false', '1', '0'],
                                 help='Was the advice helpful?')
    feedback_parser.add_argument('--comments', help='Additional feedback comments')
    feedback_parser.add_argument('--config', default='config/security_patterns.json',
                                help='Path to configuration file')
    feedback_parser.set_defaults(func=cmd_feedback)
    
    # Intent command
    intent_parser = subparsers.add_parser('intent', help='Capture contributor intent')
    intent_parser.add_argument('--intent', required=True, help='Contributor intent description')
    intent_parser.add_argument('--labels', help='Comma-separated issue labels')
    intent_parser.add_argument('--files', help='Comma-separated file patterns')
    intent_parser.add_argument('--config', default='config/security_patterns.json',
                              help='Path to configuration file')
    intent_parser.set_defaults(func=cmd_intent)
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Generate maintainer dashboard')
    dashboard_parser.add_argument('--output', help='Output file for dashboard')
    dashboard_parser.set_defaults(func=cmd_dashboard)
    
    args = parser.parse_args()
    
    # Default behaviour: run the pre-commit check when no sub-command is given.
    if not args.command:
        args.files = None
        args.config = 'config/security_patterns.json'
        cmd_check(args)
        return

    args.func(args)


if __name__ == '__main__':
    main()
