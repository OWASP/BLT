#!/usr/bin/env python3
"""
Week 1 Comprehensive Test Suite – BLT-Preflight RAG Pipeline

This script tests:
1. RAG Retriever quality and hallucination prevention
2. Metadata validation and completeness
3. Similarity scoring and filtering
4. Knowledge base coverage
5. End-to-end retrieval scenarios
"""

import sys
import json
from pathlib import Path
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from advisory_engine.retriever import RAGRetriever
from advisory_engine.rag.config import RAGConfig


class Week1TestSuite:
    """Comprehensive testing for Week 1 deliverables."""
    
    def __init__(self):
        self.retriever = RAGRetriever(similarity_threshold=0.6)
        self.test_results = []
        self.passed = 0
        self.failed = 0
        
    def print_header(self, text: str):
        """Print formatted header."""
        print("\n" + "=" * 80)
        print(f" {text}")
        print("=" * 80 + "\n")
    
    def print_subheader(self, text: str):
        """Print formatted subheader."""
        print(f"\n→ {text}")
        print("-" * 80)
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"  {details}")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
    
    # ── Test Suite 1: Retriever Quality ──────────────────────────────────────
    
    def test_retriever_initialization(self):
        """Test: RAG Retriever initializes correctly."""
        self.print_subheader("Test 1: Retriever Initialization")
        
        try:
            assert self.retriever is not None, "Retriever not initialized"
            assert self.retriever.embedder is not None, "Embedder not initialized"
            assert self.retriever.collection is not None, "ChromaDB collection not loaded"
            
            self.log_result("Retriever initialization", True, "All components ready")
            return True
        except Exception as e:
            self.log_result("Retriever initialization", False, str(e))
            return False
    
    def test_contributor_intent_retrieval(self):
        """Test: Retrieve for typical contributor intents."""
        self.print_subheader("Test 2: Contributor Intent Retrieval")
        
        test_cases = [
            ("I modified the login flow", "Authentication changes"),
            ("I added a new API endpoint", "API security considerations"),
            ("I changed how passwords are stored", "Cryptographic best practices"),
            ("I updated third-party dependencies", "Supply chain security"),
            ("I modified the session handling", "Session management security"),
        ]
        
        all_passed = True
        
        for query, intent in test_cases:
            print(f"\nQuery: '{query}'")
            print(f"Intent: {intent}")
            
            result = self.retriever.retrieve(query, top_k=2)
            
            # Validation checks
            passed = True
            details = []
            
            # Check 1: Status should be success or no_match (not error)
            if result['status'] not in ['success', 'no_match']:
                passed = False
                details.append(f"Unexpected status: {result['status']}")
            
            # Check 2: If success, should have chunks
            if result['status'] == 'success':
                if not result['retrieved_chunks']:
                    passed = False
                    details.append("Success status but no chunks retrieved")
                else:
                    details.append(f"Retrieved {len(result['retrieved_chunks'])} chunks")
                    
                    # Check 3: Quality scoring present
                    for chunk in result['retrieved_chunks']:
                        if 'quality_score' not in chunk:
                            passed = False
                            details.append("Missing quality_score")
                            break
                    
                    if passed and result['retrieved_chunks']:
                        details.append(
                            f"Quality: {result['retrieval_quality']} | "
                            f"Avg Score: {result.get('average_quality_score', 0):.3f}"
                        )
            
            # Check 4: Message should be informative
            if result['message']:
                details.append(f"Message: {result['message']}")
            
            self.log_result(f"  Intent: {intent}", passed, " | ".join(details))
            all_passed = all_passed and passed
        
        return all_passed
    
    def test_quality_thresholds(self):
        """Test: Quality filtering prevents low-confidence retrievals."""
        self.print_subheader("Test 3: Quality Threshold Filtering")
        
        # Query that should match well
        query_good = "authentication and login security"
        result_good = self.retriever.retrieve(query_good, top_k=3)
        
        # Query that might not match well
        query_poor = "xyzabc qwerty nonexistent domain jargon"
        result_poor = self.retriever.retrieve(query_poor, top_k=3)
        
        passed = True
        details = []
        
        # Good query should retrieve successfully
        if result_good['status'] != 'success':
            passed = False
            details.append(f"Good query failed: {result_good['message']}")
        else:
            details.append(f"Good query: Retrieved {len(result_good['retrieved_chunks'])} chunks")
            if result_good['retrieved_chunks']:
                details.append(
                    f"  Quality: {result_good['retrieval_quality']} | "
                    f"Scores: {[c['quality_score'] for c in result_good['retrieved_chunks']]}"
                )
        
        # Poor query should gracefully handle no matches
        if result_poor['status'] == 'error':
            passed = False
            details.append(f"Poor query error: {result_poor['message']}")
        else:
            details.append(f"Poor query: Status={result_poor['status']}")
            details.append(f"  Message: {result_poor['message']}")
        
        self.log_result("Quality threshold filtering", passed, " | ".join(details))
        return passed
    
    def test_metadata_validation(self):
        """Test: Retrieved chunks have complete metadata."""
        self.print_subheader("Test 4: Metadata Validation")
        
        query = "authentication security best practices"
        result = self.retriever.retrieve(query, top_k=3)
        
        passed = True
        details = []
        
        if result['status'] == 'success' and result['retrieved_chunks']:
            required_fields = ['title', 'category', 'source_url', 'filename', 'chunk_index']
            
            for i, chunk in enumerate(result['retrieved_chunks']):
                metadata = chunk.get('metadata', {})
                missing_fields = [f for f in required_fields if not metadata.get(f)]
                
                if missing_fields:
                    passed = False
                    details.append(f"Chunk {i}: Missing {missing_fields}")
                else:
                    details.append(
                        f"Chunk {i}: ✓ Complete metadata "
                        f"(title={metadata.get('title', 'N/A')[:30]}..., "
                        f"category={metadata.get('category', 'N/A')})"
                    )
        else:
            details.append("No chunks to validate (status != success)")
        
        self.log_result("Metadata validation", passed, " | ".join(details))
        return passed
    
    def test_chunk_content_quality(self):
        """Test: Retrieved chunks are substantive (not tiny/empty)."""
        self.print_subheader("Test 5: Chunk Content Quality")
        
        query = "password storage cryptography"
        result = self.retriever.retrieve(query, top_k=3)
        
        passed = True
        details = []
        min_chars = 50
        
        if result['status'] == 'success' and result['retrieved_chunks']:
            for i, chunk in enumerate(result['retrieved_chunks']):
                text = chunk.get('text', '')
                char_count = len(text.strip())
                
                if char_count < min_chars:
                    passed = False
                    details.append(f"Chunk {i}: Too short ({char_count} chars)")
                else:
                    details.append(
                        f"Chunk {i}: ✓ Substantive ({char_count} chars, "
                        f"{len(text.split())} words)"
                    )
        else:
            details.append("No chunks to evaluate")
        
        self.log_result("Chunk content quality", passed, " | ".join(details))
        return passed
    
    def test_similarity_scoring(self):
        """Test: Similarity scores are reasonable (0-1) and well-distributed."""
        self.print_subheader("Test 6: Similarity Scoring")
        
        query = "SQL injection prevention techniques"
        result = self.retriever.retrieve(query, top_k=3)
        
        passed = True
        details = []
        
        if result['status'] == 'success' and result['retrieved_chunks']:
            scores = [c['similarity'] for c in result['retrieved_chunks']]
            quality_scores = [c['quality_score'] for c in result['retrieved_chunks']]
            
            # All scores should be 0-1
            if all(0 <= s <= 1 for s in scores):
                details.append(f"✓ Similarity scores valid: {[f'{s:.3f}' for s in scores]}")
            else:
                passed = False
                details.append(f"✗ Invalid similarity scores: {scores}")
            
            # Quality scores should be 0-1
            if all(0 <= s <= 1 for s in quality_scores):
                details.append(f"✓ Quality scores valid: {[f'{s:.3f}' for s in quality_scores]}")
            else:
                passed = False
                details.append(f"✗ Invalid quality scores: {quality_scores}")
            
            # Scores should be in descending order
            if scores == sorted(scores, reverse=True):
                details.append("✓ Scores properly sorted (descending)")
            else:
                passed = False
                details.append("✗ Scores not properly sorted")
        else:
            details.append("No chunks to evaluate")
        
        self.log_result("Similarity scoring", passed, " | ".join(details))
        return passed
    
    # ── Test Suite 2: Knowledge Base Coverage ────────────────────────────────
    
    def test_knowledge_base_coverage(self):
        """Test: Knowledge base covers major security topics."""
        self.print_subheader("Test 7: Knowledge Base Coverage")
        
        coverage_queries = {
            "authentication": "Authentication & login security",
            "api": "API security",
            "injection": "Injection attacks (SQL, XSS, etc.)",
            "access": "Access control & authorization",
            "encryption": "Encryption & cryptography",
            "session": "Session management",
            "supply_chain": "Supply chain security",
        }
        
        coverage = {}
        all_covered = True
        
        for topic, description in coverage_queries.items():
            result = self.retriever.retrieve(description, top_k=1)
            
            if result['status'] == 'success' and result['retrieved_chunks']:
                coverage[topic] = "✓"
                print(f"✓ {topic}: Covered")
            else:
                coverage[topic] = "✗"
                all_covered = False
                print(f"✗ {topic}: Not covered")
        
        covered_count = sum(1 for v in coverage.values() if v == "✓")
        self.log_result(
            "Knowledge base coverage",
            all_covered,
            f"{covered_count}/{len(coverage_queries)} topics covered: {coverage}"
        )
        return all_covered
    
    # ── Test Suite 3: No Hallucination ──────────────────────────────────────
    
    def test_hallucination_prevention(self):
        """Test: Nonsense queries don't return false positives."""
        self.print_subheader("Test 8: Hallucination Prevention")
        
        nonsense_queries = [
            "xyzabc qwerty zxcvbn",
            "banana hammock purple elephant",
            "12345 !@#$% ~~~~~",
            "zzzzz yyyyy xxxxx",
        ]
        
        false_positives = 0
        
        for query in nonsense_queries:
            result = self.retriever.retrieve(query, top_k=3)
            
            # Nonsense queries should either:
            # 1. Return no_match status
            # 2. Return low-quality results that wouldn't be used
            
            if result['status'] == 'no_match':
                print(f"✓ '{query[:30]}...': Correctly rejected (no_match)")
            elif result['status'] == 'error':
                print(f"✓ '{query[:30]}...': Correctly rejected (error)")
            elif result['retrieved_chunks']:
                min_quality = min(c['quality_score'] for c in result['retrieved_chunks'])
                if min_quality < 0.5:
                    print(f"✓ '{query[:30]}...': Low quality results ({min_quality:.3f})")
                else:
                    false_positives += 1
                    print(f"✗ '{query[:30]}...': Suspicious match with quality {min_quality:.3f}")
            else:
                print(f"✓ '{query[:30]}...': No results")
        
        passed = false_positives == 0
        self.log_result(
            "Hallucination prevention",
            passed,
            f"{4 - false_positives}/4 nonsense queries properly rejected"
        )
        return passed
    
    # ── Main Test Runner ────────────────────────────────────────────────────
    
    def run_all_tests(self):
        """Run complete test suite."""
        self.print_header("WEEK 1 TEST SUITE – BLT-Preflight RAG Pipeline")
        
        print(f"Configuration:")
        print(f"  Embedding Model: {self.retriever.config.EMBEDDING_MODEL}")
        print(f"  Similarity Threshold: {self.retriever.similarity_threshold}")
        print(f"  ChromaDB Dir: {self.retriever.config.CHROMADB_DIR}")
        
        # Run tests
        self.test_retriever_initialization()
        self.test_contributor_intent_retrieval()
        self.test_quality_thresholds()
        self.test_metadata_validation()
        self.test_chunk_content_quality()
        self.test_similarity_scoring()
        self.test_knowledge_base_coverage()
        self.test_hallucination_prevention()
        
        # Print summary
        self.print_header("TEST SUMMARY")
        
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✓ Passed: {self.passed}")
        print(f"✗ Failed: {self.failed}")
        print(f"Success Rate: {100 * self.passed / (self.passed + self.failed):.1f}%")
        
        # Status
        status = "✓ ALL TESTS PASSED" if self.failed == 0 else f"✗ {self.failed} TESTS FAILED"
        print(f"\nStatus: {status}\n")
        
        # Detailed results
        print("\nDetailed Results (JSON):")
        print(json.dumps(self.test_results, indent=2))
        
        return self.failed == 0


if __name__ == "__main__":
    suite = Week1TestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)
