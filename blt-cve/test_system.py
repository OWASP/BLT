#!/usr/bin/env python3
"""
Test script for the BLT-CVE system.
Tests blockchain functionality, CVE operations, and API endpoints.
"""
import unittest
import json
import os
import sys
from blockchain import Blockchain, Block
from cve_fetcher import CVEFetcher


class TestBlockchain(unittest.TestCase):
    """Test blockchain functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.blockchain = Blockchain(difficulty=2)
    
    def test_genesis_block(self):
        """Test genesis block creation."""
        self.assertEqual(len(self.blockchain.chain), 1)
        self.assertEqual(self.blockchain.chain[0].index, 0)
        self.assertEqual(self.blockchain.chain[0].previous_hash, "0")
    
    def test_add_cve(self):
        """Test adding CVE to pending list."""
        cve_data = {
            'cve_id': 'CVE-2023-TEST',
            'description': 'Test vulnerability',
            'severity': 'HIGH'
        }
        self.blockchain.add_cve(cve_data)
        self.assertEqual(len(self.blockchain.pending_cves), 1)
    
    def test_mine_block(self):
        """Test mining CVEs into a block."""
        cve_data = {
            'cve_id': 'CVE-2023-TEST',
            'description': 'Test vulnerability',
            'severity': 'HIGH'
        }
        self.blockchain.add_cve(cve_data)
        
        block = self.blockchain.mine_pending_cves()
        self.assertIsNotNone(block)
        self.assertEqual(len(self.blockchain.chain), 2)
        self.assertEqual(len(self.blockchain.pending_cves), 0)
    
    def test_blockchain_validity(self):
        """Test blockchain validation."""
        self.assertTrue(self.blockchain.is_chain_valid())
        
        # Add and mine a block
        cve_data = {
            'cve_id': 'CVE-2023-TEST',
            'description': 'Test vulnerability'
        }
        self.blockchain.add_cve(cve_data)
        self.blockchain.mine_pending_cves()
        
        self.assertTrue(self.blockchain.is_chain_valid())
    
    def test_find_cve(self):
        """Test finding CVE by ID."""
        cve_data = {
            'cve_id': 'CVE-2023-FIND',
            'description': 'Findable vulnerability'
        }
        self.blockchain.add_cve(cve_data)
        self.blockchain.mine_pending_cves()
        
        found = self.blockchain.find_cve_by_id('CVE-2023-FIND')
        self.assertIsNotNone(found)
        self.assertEqual(found['cve_id'], 'CVE-2023-FIND')
    
    def test_get_all_cves(self):
        """Test retrieving all CVEs."""
        cves = [
            {'cve_id': 'CVE-2023-001', 'description': 'Test 1'},
            {'cve_id': 'CVE-2023-002', 'description': 'Test 2'},
            {'cve_id': 'CVE-2023-003', 'description': 'Test 3'}
        ]
        
        for cve in cves:
            self.blockchain.add_cve(cve)
        
        self.blockchain.mine_pending_cves()
        
        all_cves = self.blockchain.get_all_cves()
        self.assertEqual(len(all_cves), 3)
    
    def test_save_load_blockchain(self):
        """Test saving and loading blockchain."""
        import tempfile
        
        # Create temporary file
        fd, test_file = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        
        try:
            # Add data and save
            cve_data = {'cve_id': 'CVE-2023-SAVE', 'description': 'Test save'}
            self.blockchain.add_cve(cve_data)
            self.blockchain.mine_pending_cves()
            self.blockchain.save_to_file(test_file)
            
            # Load and verify
            loaded_blockchain = Blockchain.load_from_file(test_file, difficulty=2)
            self.assertEqual(len(loaded_blockchain.chain), len(self.blockchain.chain))
            self.assertTrue(loaded_blockchain.is_chain_valid())
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)


class TestCVEFetcher(unittest.TestCase):
    """Test CVE fetcher functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = CVEFetcher()
    
    def test_extract_cve_data(self):
        """Test CVE data extraction."""
        sample_cve = {
            'id': 'CVE-2023-12345',
            'descriptions': [
                {'lang': 'en', 'value': 'Test vulnerability description'}
            ],
            'metrics': {
                'cvssMetricV31': [{
                    'cvssData': {
                        'baseScore': 7.5,
                        'baseSeverity': 'HIGH'
                    }
                }]
            },
            'references': [
                {'url': 'https://example.com', 'source': 'test'}
            ],
            'published': '2023-01-01T00:00:00.000',
            'lastModified': '2023-01-02T00:00:00.000'
        }
        
        cve_data = self.fetcher.extract_cve_data(sample_cve)
        
        self.assertIsNotNone(cve_data)
        self.assertEqual(cve_data['cve_id'], 'CVE-2023-12345')
        self.assertEqual(cve_data['severity'], 'HIGH')
        self.assertEqual(cve_data['cvss_score'], 7.5)
    
    def test_validate_cve_data(self):
        """Test CVE data validation."""
        valid_cve = {
            'cve_id': 'CVE-2023-12345',
            'description': 'Test description'
        }
        self.assertTrue(self.fetcher.validate_cve_data(valid_cve))
        
        invalid_cve = {
            'cve_id': 'CVE-2023-12345'
            # Missing description
        }
        self.assertFalse(self.fetcher.validate_cve_data(invalid_cve))


class TestBlock(unittest.TestCase):
    """Test individual block functionality."""
    
    def test_block_creation(self):
        """Test block creation."""
        block = Block(1, 1234567890, {'test': 'data'}, 'previous_hash')
        self.assertEqual(block.index, 1)
        self.assertEqual(block.timestamp, 1234567890)
        self.assertEqual(block.previous_hash, 'previous_hash')
    
    def test_block_hash_calculation(self):
        """Test block hash calculation."""
        block = Block(1, 1234567890, {'test': 'data'}, 'previous_hash')
        hash1 = block.calculate_hash()
        hash2 = block.calculate_hash()
        self.assertEqual(hash1, hash2)
    
    def test_block_mining(self):
        """Test block mining with proof of work."""
        block = Block(1, 1234567890, {'test': 'data'}, 'previous_hash')
        difficulty = 2
        block.mine_block(difficulty)
        
        # Check that hash starts with correct number of zeros
        self.assertTrue(block.hash.startswith('0' * difficulty))
    
    def test_block_to_dict(self):
        """Test block serialization."""
        block = Block(1, 1234567890, {'test': 'data'}, 'previous_hash')
        block_dict = block.to_dict()
        
        self.assertEqual(block_dict['index'], 1)
        self.assertEqual(block_dict['timestamp'], 1234567890)
        self.assertIn('hash', block_dict)


def run_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running BLT-CVE System Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests
    suite.addTests(loader.loadTestsFromTestCase(TestBlock))
    suite.addTests(loader.loadTestsFromTestCase(TestBlockchain))
    suite.addTests(loader.loadTestsFromTestCase(TestCVEFetcher))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
