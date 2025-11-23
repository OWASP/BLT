#!/usr/bin/env python3
"""
Demo script for BLT-CVE system.
Demonstrates key functionality without requiring NVD API access.
"""
from blockchain import Blockchain
from cve_fetcher import CVEFetcher
import json


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def demo_blockchain():
    """Demonstrate blockchain functionality."""
    print_section("1. Blockchain Creation")
    
    # Create blockchain
    blockchain = Blockchain(difficulty=2)
    print(f"✓ Created blockchain with difficulty {blockchain.difficulty}")
    print(f"✓ Genesis block created: {blockchain.chain[0].hash[:16]}...")
    
    print_section("2. Adding CVEs")
    
    # Add sample CVEs
    sample_cves = [
        {
            'cve_id': 'CVE-2023-12345',
            'description': 'Buffer overflow in example software',
            'severity': 'HIGH',
            'cvss_score': 8.5,
            'source': 'DEMO'
        },
        {
            'cve_id': 'CVE-2023-12346',
            'description': 'SQL injection vulnerability',
            'severity': 'CRITICAL',
            'cvss_score': 9.2,
            'source': 'DEMO'
        },
        {
            'cve_id': 'CVE-2023-12347',
            'description': 'Cross-site scripting (XSS) vulnerability',
            'severity': 'MEDIUM',
            'cvss_score': 6.1,
            'source': 'DEMO'
        }
    ]
    
    for cve in sample_cves:
        blockchain.add_cve(cve)
        print(f"✓ Added {cve['cve_id']} (Severity: {cve['severity']})")
    
    print(f"\nPending CVEs: {len(blockchain.pending_cves)}")
    
    print_section("3. Mining Block")
    
    print("Mining CVEs into blockchain (proof-of-work)...")
    block = blockchain.mine_pending_cves()
    print(f"✓ Block mined successfully!")
    print(f"  Block Index: {block.index}")
    print(f"  Block Hash: {block.hash[:32]}...")
    print(f"  CVEs in Block: {block.data['count']}")
    print(f"  Nonce: {block.nonce}")
    
    print_section("4. Blockchain Validation")
    
    is_valid = blockchain.is_chain_valid()
    print(f"Blockchain Valid: {'✓ YES' if is_valid else '✗ NO'}")
    print(f"Total Blocks: {len(blockchain.chain)}")
    print(f"Total CVEs: {len(blockchain.get_all_cves())}")
    
    print_section("5. Querying CVEs")
    
    # Find specific CVE
    cve_id = 'CVE-2023-12346'
    cve = blockchain.find_cve_by_id(cve_id)
    if cve:
        print(f"\n✓ Found {cve_id}:")
        print(f"  Description: {cve['description']}")
        print(f"  Severity: {cve['severity']}")
        print(f"  CVSS Score: {cve['cvss_score']}")
    
    # List all CVEs
    print("\nAll CVEs in blockchain:")
    for cve in blockchain.get_all_cves():
        print(f"  - {cve['cve_id']}: {cve['severity']}")
    
    print_section("6. User Reporting")
    
    # Simulate user-reported CVE
    user_cve = {
        'cve_id': 'CVE-2024-99999',
        'description': 'User-reported vulnerability in web application',
        'severity': 'HIGH',
        'source': 'USER_REPORTED',
        'reporter': 'community_user'
    }
    
    blockchain.add_cve(user_cve)
    print(f"✓ User reported: {user_cve['cve_id']}")
    print(f"  Reporter: {user_cve['reporter']}")
    print(f"  Status: Pending (will be mined in next block)")
    
    # Mine user-reported CVE
    print("\nMining user-reported CVE...")
    block = blockchain.mine_pending_cves()
    print(f"✓ Block {block.index} mined with user-reported CVE")
    
    print_section("7. Persistence")
    
    # Save blockchain
    filename = "/tmp/demo_blockchain.json"
    blockchain.save_to_file(filename)
    print(f"✓ Blockchain saved to {filename}")
    
    # Load blockchain
    loaded_blockchain = Blockchain.load_from_file(filename, difficulty=2)
    print(f"✓ Blockchain loaded from file")
    print(f"  Blocks: {len(loaded_blockchain.chain)}")
    print(f"  Valid: {'✓ YES' if loaded_blockchain.is_chain_valid() else '✗ NO'}")
    print(f"  CVEs: {len(loaded_blockchain.get_all_cves())}")
    
    print_section("8. Blockchain Statistics")
    
    stats = blockchain.to_dict()
    print(f"Chain Length: {stats['length']} blocks")
    print(f"Difficulty: {stats['difficulty']}")
    print(f"Total CVEs Stored: {len(blockchain.get_all_cves())}")
    print(f"Pending CVEs: {stats['pending_cves']}")
    
    # Show chain structure
    print("\nBlockchain Structure:")
    for block in blockchain.chain:
        cve_count = block.data.get('count', 0) if block.data.get('type') == 'cve_batch' else 0
        print(f"  Block {block.index}: {block.hash[:16]}... ({cve_count} CVEs)")


def demo_cve_fetcher():
    """Demonstrate CVE fetcher functionality."""
    print_section("CVE Fetcher Demo")
    
    fetcher = CVEFetcher()
    print("✓ CVE Fetcher initialized")
    print(f"  NVD API URL: {fetcher.nvd_api_url}")
    print(f"  Alternative Sources: {len(fetcher.alternative_sources)}")
    
    # Demo data extraction
    print("\n✓ CVE data extraction capability available")
    print("  Note: Live NVD fetching requires API key and internet access")
    print("  The system supports:")
    print("    - Fetching recent CVEs from NVD")
    print("    - Searching for specific CVEs")
    print("    - Backing up to local cache")
    print("    - Multiple source redundancy")


def main():
    """Run the demo."""
    print("\n" + "=" * 60)
    print("  BLT-CVE: Decentralized CVE Database Demo")
    print("  A resilient blockchain-based CVE storage system")
    print("=" * 60)
    
    demo_blockchain()
    demo_cve_fetcher()
    
    print_section("Demo Complete")
    print("\n✓ All core functionality demonstrated")
    print("\nNext steps:")
    print("  1. Start the API server: python app.py")
    print("  2. Use the CLI tool: python cli.py --help")
    print("  3. Access API at: http://localhost:5000")
    print("  4. Sync real CVEs: curl -X POST http://localhost:5000/sync")
    print("  5. Mine CVEs: curl -X POST http://localhost:5000/mine")
    print("\n" + "=" * 60 + "\n")


if __name__ == '__main__':
    main()
