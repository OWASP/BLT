#!/usr/bin/env python3
"""
Quick Start Script for BLT-Preflight
Demonstrates the advisory system with sample scenarios
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from advisory_engine.core import AdvisoryEngine, AdvisoryContext


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def demo_authentication_advisory():
    """Demonstrate authentication advisory."""
    print_header("Demo 1: Authentication Changes")
    
    print("Scenario: Developer modifying authentication code")
    print("Files: src/auth/login.py, src/auth/password.py")
    print("Labels: security, authentication\n")
    
    engine = AdvisoryEngine()
    
    context = AdvisoryContext(
        issue_labels=["security", "authentication"],
        repo_metadata={"repository": "OWASP-BLT/BLT", "pr_number": 123},
        file_patterns=["src/auth/login.py", "src/auth/password.py"]
    )
    
    advice_list = engine.evaluate_context(context)
    report = engine.generate_report(advice_list)
    
    print(report[:500] + "...\n")
    print(f"✓ Generated {len(advice_list)} security advisories")


def demo_api_advisory():
    """Demonstrate API advisory."""
    print_header("Demo 2: API Endpoint Changes")
    
    print("Scenario: Developer adding new API endpoints")
    print("Files: src/api/v2/users.py")
    print("Labels: api\n")
    
    engine = AdvisoryEngine()
    
    context = AdvisoryContext(
        issue_labels=["api"],
        repo_metadata={"repository": "OWASP-BLT/BLT", "pr_number": 124},
        file_patterns=["src/api/v2/users.py"]
    )
    
    advice_list = engine.evaluate_context(context)
    
    print(f"✓ Generated {len(advice_list)} API security advisories")
    for advice in advice_list:
        print(f"  - {advice.title} ({advice.severity})")


def demo_intent_capture():
    """Demonstrate intent capture."""
    print_header("Demo 3: Intent Capture")
    
    print("Scenario: Developer stating their intent")
    print("Intent: 'Adding OAuth2 support for Google authentication'\n")
    
    engine = AdvisoryEngine()
    
    context = AdvisoryContext(
        issue_labels=["authentication", "oauth"],
        repo_metadata={},
        file_patterns=["src/oauth/google.py"]
    )
    
    engine.capture_intent("Adding OAuth2 support for Google authentication", context)
    
    print("✓ Intent captured and stored for learning")
    print("  This helps the system provide better guidance in the future")


def demo_feedback():
    """Demonstrate feedback recording."""
    print_header("Demo 4: Feedback Recording")
    
    print("Scenario: Developer provides feedback on advisory\n")
    
    engine = AdvisoryEngine()
    
    engine.record_feedback(
        advice_title="Security Advisory: Authentication",
        helpful=True,
        comments="Very clear recommendations, helped me improve my code"
    )
    
    print("✓ Feedback recorded")
    print("  Helpful: Yes")
    print("  Comments: 'Very clear recommendations, helped me improve my code'")


def demo_dashboard():
    """Demonstrate dashboard generation."""
    print_header("Demo 5: Maintainer Dashboard")
    
    print("Scenario: Maintainer viewing advisory statistics\n")
    
    from advisory_engine.dashboard import MaintainerDashboard
    
    dashboard = MaintainerDashboard()
    report = dashboard.generate_dashboard()
    
    # Show first few lines
    lines = report.split('\n')[:15]
    print('\n'.join(lines))
    print("\n... (truncated for demo)")
    print("\n✓ Dashboard generated with feedback analysis and pattern effectiveness")


def demo_learning_loop():
    """Demonstrate learning loop."""
    print_header("Demo 6: Learning Loop")
    
    print("Scenario: System learns from past patterns\n")
    
    engine = AdvisoryEngine()
    
    # Show learning data
    intents_count = len(engine.learning_data.get("intents", []))
    feedback_count = len(engine.learning_data.get("feedback", []))
    
    print(f"✓ Learning data loaded:")
    print(f"  - {intents_count} contributor intents captured")
    print(f"  - {feedback_count} feedback entries recorded")
    print(f"\nThis data helps refine future advisories")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  🛡️  BLT-Preflight Quick Start Demonstration")
    print("=" * 70)
    print("\nThis script demonstrates the key features of BLT-Preflight")
    print("advisory system with sample scenarios.\n")
    
    input("Press Enter to start the demonstration...")
    
    try:
        demo_authentication_advisory()
        input("\nPress Enter to continue...")
        
        demo_api_advisory()
        input("\nPress Enter to continue...")
        
        demo_intent_capture()
        input("\nPress Enter to continue...")
        
        demo_feedback()
        input("\nPress Enter to continue...")
        
        demo_dashboard()
        input("\nPress Enter to continue...")
        
        demo_learning_loop()
        
        print_header("Demonstration Complete!")
        
        print("Next Steps:")
        print("\n1. Try generating your own advisory:")
        print("   python3 src/blt_preflight.py advise --labels security --files your/file.py")
        print("\n2. Read the documentation:")
        print("   - README.md - Overview and features")
        print("   - docs/SECURITY_GUIDANCE.md - Security best practices")
        print("   - docs/CONFIGURATION.md - Customization guide")
        print("\n3. Enable the GitHub Action in your repository")
        print("   - Already configured in .github/workflows/advisory.yml")
        print("\n4. Provide feedback to help improve the system")
        print("   python3 src/blt_preflight.py feedback --pattern 'Pattern Name' --helpful yes\n")
        
        print("=" * 70)
        print("  Thank you for trying BLT-Preflight!")
        print("=" * 70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nDemonstration interrupted. Goodbye!")
        return 1
    except Exception as e:
        print(f"\n\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
