#!/usr/bin/env python3
"""
Test script for BLT Preflight Advisory Engine
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from advisory_engine.core import AdvisoryEngine, AdvisoryContext, SecurityAdvice
from advisory_engine.dashboard import MaintainerDashboard


def test_advisory_generation():
    """Test basic advisory generation."""
    print("Testing advisory generation...")
    
    engine = AdvisoryEngine()
    
    # Test 1: Authentication advisory
    context = AdvisoryContext(
        issue_labels=["security", "authentication"],
        repo_metadata={"repository": "OWASP-BLT/BLT"},
        file_patterns=["src/auth/login.py", "src/auth/password.py"]
    )
    
    advice_list = engine.evaluate_context(context)
    assert len(advice_list) > 0, "Should generate advice"
    assert any(a.severity == "critical" for a in advice_list), "Should have critical advice"
    
    print("✓ Authentication advisory test passed")
    
    # Test 2: API advisory
    context = AdvisoryContext(
        issue_labels=["api"],
        repo_metadata={"repository": "OWASP-BLT/BLT"},
        file_patterns=["src/api/endpoints.py"]
    )
    
    advice_list = engine.evaluate_context(context)
    assert len(advice_list) > 0, "Should generate advice"
    
    print("✓ API advisory test passed")
    
    # Test 3: General advice (no specific patterns)
    context = AdvisoryContext(
        issue_labels=[],
        repo_metadata={"repository": "OWASP-BLT/BLT"},
        file_patterns=["src/utils.py"]
    )
    
    advice_list = engine.evaluate_context(context)
    assert len(advice_list) > 0, "Should generate general advice"
    assert any("General Security Guidance" in a.title for a in advice_list)
    
    print("✓ General advice test passed")


def test_report_generation():
    """Test report generation."""
    print("\nTesting report generation...")
    
    engine = AdvisoryEngine()
    
    context = AdvisoryContext(
        issue_labels=["security"],
        repo_metadata={"repository": "OWASP-BLT/BLT"},
        file_patterns=["src/auth/login.py"]
    )
    
    advice_list = engine.evaluate_context(context)
    report = engine.generate_report(advice_list)
    
    assert "BLT Preflight Security Advisory" in report
    assert "Recommendations:" in report
    assert "Learn more:" in report
    
    print("✓ Report generation test passed")


def test_feedback_recording():
    """Test feedback recording."""
    print("\nTesting feedback recording...")
    
    engine = AdvisoryEngine()
    
    # Record feedback
    engine.record_feedback(
        advice_title="Test Pattern",
        helpful=True,
        comments="Test comment"
    )
    
    # Check if feedback was recorded
    assert "feedback" in engine.learning_data
    assert len(engine.learning_data["feedback"]) > 0
    
    print("✓ Feedback recording test passed")


def test_intent_capture():
    """Test intent capture."""
    print("\nTesting intent capture...")
    
    engine = AdvisoryEngine()
    
    context = AdvisoryContext(
        issue_labels=["security"],
        repo_metadata={},
        file_patterns=["src/auth.py"]
    )
    
    # Capture intent
    engine.capture_intent("Adding two-factor authentication", context)
    
    # Check if intent was captured
    assert "intents" in engine.learning_data
    assert len(engine.learning_data["intents"]) > 0
    
    print("✓ Intent capture test passed")


def test_dashboard():
    """Test dashboard generation."""
    print("\nTesting dashboard generation...")
    
    dashboard = MaintainerDashboard()
    report = dashboard.generate_dashboard()
    
    assert "BLT Preflight Maintainer Dashboard" in report
    assert "Overview" in report
    assert "Feedback Analysis" in report
    
    print("✓ Dashboard generation test passed")


def test_pattern_matching():
    """Test file pattern matching."""
    print("\nTesting pattern matching...")
    
    engine = AdvisoryEngine()
    
    # Test various file patterns
    test_cases = [
        ("src/auth/login.py", "authentication"),
        ("config/api_key.conf", "api_keys"),
        ("db/migrations/001.sql", "database"),
        ("lib/crypto/encrypt.py", "encryption"),
    ]
    
    for file_path, expected_pattern in test_cases:
        context = AdvisoryContext(
            issue_labels=[],
            repo_metadata={},
            file_patterns=[file_path]
        )
        
        advice_list = engine.evaluate_context(context)
        pattern_found = any(expected_pattern.replace("_", " ").lower() in a.title.lower() 
                          for a in advice_list)
        
        assert pattern_found, f"Pattern {expected_pattern} should match {file_path}"
    
    print("✓ Pattern matching test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("BLT Preflight Advisory Engine - Test Suite")
    print("=" * 60)
    
    try:
        test_advisory_generation()
        test_report_generation()
        test_feedback_recording()
        test_intent_capture()
        test_dashboard()
        test_pattern_matching()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
