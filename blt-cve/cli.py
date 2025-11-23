#!/usr/bin/env python3
"""
Command-line interface for managing the BLT-CVE database.
Provides easy access to sync, mine, and query operations.
"""
import argparse
import requests
import json
import sys
from typing import Optional


class BLTCVECLI:
    """CLI for BLT-CVE operations."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
    
    def check_server(self) -> bool:
        """Check if the server is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except (requests.exceptions.RequestException, Exception):
            return False
    
    def health(self) -> None:
        """Check server health."""
        try:
            response = requests.get(f"{self.base_url}/health")
            data = response.json()
            print("\n🏥 Server Health:")
            print(f"  Status: {data['status']}")
            print(f"  Blockchain Valid: {data['blockchain_valid']}")
            print(f"  Blocks: {data['blocks']}")
            print(f"  Pending CVEs: {data['pending_cves']}")
            print(f"  Timestamp: {data['timestamp']}")
        except Exception as e:
            print(f"❌ Error checking health: {str(e)}")
            sys.exit(1)
    
    def sync(self, days: int = 7) -> None:
        """Sync CVEs from NVD."""
        print(f"\n🔄 Syncing CVEs from last {days} days...")
        try:
            response = requests.post(f"{self.base_url}/sync?days={days}")
            data = response.json()
            print(f"  ✅ Fetched: {data['fetched']}")
            print(f"  ✅ New CVEs: {data['new_cves']}")
            print(f"  ⏭️  Duplicates skipped: {data['duplicates_skipped']}")
            print(f"  📝 {data['note']}")
        except Exception as e:
            print(f"❌ Error syncing: {str(e)}")
            sys.exit(1)
    
    def mine(self) -> None:
        """Mine pending CVEs into blockchain."""
        print("\n⛏️  Mining pending CVEs...")
        try:
            response = requests.post(f"{self.base_url}/mine")
            data = response.json()
            
            if 'message' in data and 'No pending' in data['message']:
                print("  ℹ️  No pending CVEs to mine")
            else:
                print(f"  ✅ {data['message']}")
                print(f"  📦 CVEs added: {data['cves_added']}")
                print(f"  ⛓️  Blockchain length: {data['blockchain_length']}")
        except Exception as e:
            print(f"❌ Error mining: {str(e)}")
            sys.exit(1)
    
    def list_cves(self, severity: Optional[str] = None) -> None:
        """List all CVEs."""
        print("\n📋 Listing CVEs...")
        try:
            url = f"{self.base_url}/cves"
            if severity:
                url += f"?severity={severity}"
            
            response = requests.get(url)
            data = response.json()
            
            print(f"  Total CVEs: {data['count']}\n")
            
            if data['count'] == 0:
                print("  No CVEs found.")
                return
            
            for i, cve in enumerate(data['cves'][:10], 1):
                print(f"  {i}. {cve['cve_id']}")
                print(f"     Severity: {cve.get('severity', 'UNKNOWN')}")
                print(f"     Source: {cve.get('source', 'UNKNOWN')}")
                desc = cve.get('description', '')[:100]
                print(f"     Description: {desc}...")
                print()
            
            if data['count'] > 10:
                print(f"  ... and {data['count'] - 10} more CVEs")
        
        except Exception as e:
            print(f"❌ Error listing CVEs: {str(e)}")
            sys.exit(1)
    
    def get_cve(self, cve_id: str) -> None:
        """Get details of a specific CVE."""
        print(f"\n🔍 Looking up {cve_id}...")
        try:
            response = requests.get(f"{self.base_url}/cves/{cve_id}")
            
            if response.status_code == 404:
                print(f"  ❌ CVE not found: {cve_id}")
                return
            
            cve = response.json()
            print(f"\n  CVE ID: {cve['cve_id']}")
            print(f"  Severity: {cve.get('severity', 'UNKNOWN')}")
            print(f"  CVSS Score: {cve.get('cvss_score', 'N/A')}")
            print(f"  Source: {cve.get('source', 'UNKNOWN')}")
            print(f"  Description: {cve.get('description', 'N/A')}")
            
            if cve.get('references'):
                print(f"  References:")
                for ref in cve['references'][:5]:
                    print(f"    - {ref.get('url', 'N/A')}")
        
        except Exception as e:
            print(f"❌ Error getting CVE: {str(e)}")
            sys.exit(1)
    
    def report_cve(self, cve_id: str, description: str, severity: str = "UNKNOWN", reporter: str = "cli") -> None:
        """Report a new CVE."""
        print(f"\n📝 Reporting CVE {cve_id}...")
        try:
            data = {
                'cve_id': cve_id,
                'description': description,
                'severity': severity,
                'reporter': reporter
            }
            
            response = requests.post(
                f"{self.base_url}/report",
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            
            result = response.json()
            
            if response.status_code == 201:
                print(f"  ✅ {result['message']}")
                print(f"  📝 {result['note']}")
            elif response.status_code == 409:
                print(f"  ⚠️  CVE already exists")
            else:
                print(f"  ❌ Error: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            print(f"❌ Error reporting CVE: {str(e)}")
            sys.exit(1)
    
    def blockchain_status(self) -> None:
        """Show blockchain status."""
        print("\n⛓️  Blockchain Status:")
        try:
            response = requests.get(f"{self.base_url}/blockchain")
            data = response.json()
            print(f"  Length: {data['length']} blocks")
            print(f"  Difficulty: {data['difficulty']}")
            print(f"  Valid: {data['is_valid']}")
            print(f"  Pending CVEs: {data['pending_cves']}")
            print(f"  Total CVEs: {data['total_cves']}")
        except Exception as e:
            print(f"❌ Error getting blockchain status: {str(e)}")
            sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='BLT-CVE: Decentralized CVE Database CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s health              # Check server health
  %(prog)s sync                # Sync CVEs from NVD (last 7 days)
  %(prog)s sync --days 30      # Sync CVEs from last 30 days
  %(prog)s mine                # Mine pending CVEs into blockchain
  %(prog)s list                # List all CVEs
  %(prog)s get CVE-2023-12345  # Get specific CVE details
  %(prog)s report CVE-2024-99999 "Test vulnerability" --severity HIGH
        """
    )
    
    parser.add_argument(
        '--url',
        default='http://localhost:5000',
        help='Base URL of the BLT-CVE server (default: http://localhost:5000)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Health command
    subparsers.add_parser('health', help='Check server health')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync CVEs from NVD')
    sync_parser.add_argument('--days', type=int, default=7, help='Number of days to look back (default: 7)')
    
    # Mine command
    subparsers.add_parser('mine', help='Mine pending CVEs into blockchain')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List CVEs')
    list_parser.add_argument('--severity', help='Filter by severity (e.g., HIGH, MEDIUM, LOW)')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get specific CVE details')
    get_parser.add_argument('cve_id', help='CVE ID (e.g., CVE-2023-12345)')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Report a new CVE')
    report_parser.add_argument('cve_id', help='CVE ID (e.g., CVE-2024-99999)')
    report_parser.add_argument('description', help='Vulnerability description')
    report_parser.add_argument('--severity', default='UNKNOWN', help='Severity (e.g., HIGH, MEDIUM, LOW)')
    report_parser.add_argument('--reporter', default='cli', help='Reporter name')
    
    # Blockchain command
    subparsers.add_parser('blockchain', help='Show blockchain status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    cli = BLTCVECLI(args.url)
    
    # Check if server is running
    if not cli.check_server():
        print(f"❌ Server is not running at {args.url}")
        print("   Please start the server with: python app.py")
        sys.exit(1)
    
    # Execute command
    if args.command == 'health':
        cli.health()
    elif args.command == 'sync':
        cli.sync(args.days)
    elif args.command == 'mine':
        cli.mine()
    elif args.command == 'list':
        cli.list_cves(args.severity)
    elif args.command == 'get':
        cli.get_cve(args.cve_id)
    elif args.command == 'report':
        cli.report_cve(args.cve_id, args.description, args.severity, args.reporter)
    elif args.command == 'blockchain':
        cli.blockchain_status()


if __name__ == '__main__':
    main()
