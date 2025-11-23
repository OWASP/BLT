"""
Main application for the decentralized CVE database.
Provides API endpoints for querying CVEs and accepting user reports.
"""
from flask import Flask, jsonify, request
from blockchain import Blockchain
from cve_fetcher import CVEFetcher
import os
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize blockchain
BLOCKCHAIN_FILE = "blockchain_data/cve_blockchain.json"
DIFFICULTY = int(os.getenv('BLOCKCHAIN_DIFFICULTY', 4))

# Create blockchain directory if it doesn't exist
os.makedirs("blockchain_data", exist_ok=True)

# Load or create blockchain
if os.path.exists(BLOCKCHAIN_FILE):
    blockchain = Blockchain.load_from_file(BLOCKCHAIN_FILE, DIFFICULTY)
    print(f"Loaded blockchain with {len(blockchain.chain)} blocks")
else:
    blockchain = Blockchain(difficulty=DIFFICULTY)
    print("Created new blockchain")

# Initialize CVE fetcher
nvd_api_key = os.getenv('NVD_API_KEY')
cve_fetcher = CVEFetcher(nvd_api_key)


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API information."""
    return jsonify({
        'name': 'BLT-CVE Decentralized CVE Database',
        'version': '1.0.0',
        'description': 'A resilient, blockchain-based CVE database that stays online',
        'endpoints': {
            '/': 'This help message',
            '/health': 'Health check',
            '/blockchain': 'Get blockchain status',
            '/cves': 'Get all CVEs from blockchain',
            '/cves/<cve_id>': 'Get specific CVE by ID',
            '/report': 'POST - Report a new CVE',
            '/sync': 'POST - Sync CVEs from NVD',
            '/mine': 'POST - Mine pending CVEs into blockchain'
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'blockchain_valid': blockchain.is_chain_valid(),
        'blocks': len(blockchain.chain),
        'pending_cves': len(blockchain.pending_cves),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    """Get blockchain status and information."""
    return jsonify({
        'length': len(blockchain.chain),
        'difficulty': blockchain.difficulty,
        'is_valid': blockchain.is_chain_valid(),
        'pending_cves': len(blockchain.pending_cves),
        'total_cves': len(blockchain.get_all_cves())
    })


@app.route('/blockchain/full', methods=['GET'])
def get_blockchain_full():
    """Get full blockchain data."""
    return jsonify(blockchain.to_dict())


@app.route('/cves', methods=['GET'])
def get_cves():
    """Get all CVEs from the blockchain."""
    cves = blockchain.get_all_cves()
    
    # Support filtering
    severity = request.args.get('severity')
    source = request.args.get('source')
    
    if severity:
        cves = [cve for cve in cves if cve.get('severity', '').upper() == severity.upper()]
    
    if source:
        cves = [cve for cve in cves if cve.get('source', '').upper() == source.upper()]
    
    return jsonify({
        'count': len(cves),
        'cves': cves
    })


@app.route('/cves/<cve_id>', methods=['GET'])
def get_cve(cve_id):
    """Get a specific CVE by ID."""
    cve = blockchain.find_cve_by_id(cve_id)
    
    if cve:
        return jsonify(cve)
    else:
        return jsonify({'error': 'CVE not found'}), 404


@app.route('/report', methods=['POST'])
def report_cve():
    """
    Allow users to report a new CVE.
    This provides community contribution capability.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    required_fields = ['cve_id', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Add metadata
    cve_data = {
        'cve_id': data['cve_id'],
        'description': data['description'],
        'severity': data.get('severity', 'UNKNOWN'),
        'cvss_score': data.get('cvss_score'),
        'references': data.get('references', []),
        'source': 'USER_REPORTED',
        'reporter': data.get('reporter', 'anonymous'),
        'reported_at': datetime.now().isoformat()
    }
    
    # Check if CVE already exists
    existing = blockchain.find_cve_by_id(cve_data['cve_id'])
    if existing:
        return jsonify({
            'error': 'CVE already exists',
            'existing_cve': existing
        }), 409
    
    # Add to pending CVEs
    blockchain.add_cve(cve_data)
    
    return jsonify({
        'message': 'CVE reported successfully',
        'cve': cve_data,
        'status': 'pending',
        'note': 'CVE will be added to blockchain on next mining operation'
    }), 201


@app.route('/sync', methods=['POST'])
def sync_cves():
    """
    Sync CVEs from NVD and add them to the blockchain.
    This backs up the main CVE database.
    """
    days = request.args.get('days', 7, type=int)
    
    # Fetch CVEs from NVD
    print(f"Syncing CVEs from last {days} days...")
    cves = cve_fetcher.fetch_recent_cves(days=days)
    
    if not cves:
        return jsonify({
            'message': 'No new CVEs fetched',
            'count': 0
        })
    
    # Filter out CVEs that already exist
    new_cves = []
    for cve in cves:
        if not blockchain.find_cve_by_id(cve['cve_id']):
            blockchain.add_cve(cve)
            new_cves.append(cve)
    
    # Backup to cache
    cve_fetcher.backup_to_cache(new_cves)
    
    return jsonify({
        'message': 'CVEs synced successfully',
        'fetched': len(cves),
        'new_cves': len(new_cves),
        'duplicates_skipped': len(cves) - len(new_cves),
        'status': 'pending',
        'note': 'CVEs will be added to blockchain on next mining operation'
    })


@app.route('/mine', methods=['POST'])
def mine_pending():
    """
    Mine pending CVEs into a new block.
    This adds CVEs to the blockchain for immutability.
    """
    if not blockchain.pending_cves:
        return jsonify({
            'message': 'No pending CVEs to mine'
        })
    
    pending_count = len(blockchain.pending_cves)
    print(f"Mining {pending_count} pending CVEs...")
    
    block = blockchain.mine_pending_cves()
    
    # Save blockchain to file
    blockchain.save_to_file(BLOCKCHAIN_FILE)
    
    return jsonify({
        'message': 'Block mined successfully',
        'block': block.to_dict(),
        'cves_added': pending_count,
        'blockchain_length': len(blockchain.chain)
    })


@app.route('/search', methods=['GET'])
def search_cve():
    """Search for a CVE in NVD and add it to pending."""
    cve_id = request.args.get('cve_id')
    
    if not cve_id:
        return jsonify({'error': 'cve_id parameter required'}), 400
    
    # Check if already in blockchain
    existing = blockchain.find_cve_by_id(cve_id)
    if existing:
        return jsonify({
            'message': 'CVE found in blockchain',
            'cve': existing,
            'source': 'blockchain'
        })
    
    # Search in NVD
    cve_data = cve_fetcher.search_cve(cve_id)
    
    if cve_data:
        blockchain.add_cve(cve_data)
        return jsonify({
            'message': 'CVE found in NVD and added to pending',
            'cve': cve_data,
            'status': 'pending'
        })
    else:
        return jsonify({
            'error': 'CVE not found',
            'cve_id': cve_id
        }), 404


if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("=" * 60)
    print("BLT-CVE Decentralized CVE Database")
    print("=" * 60)
    print(f"Starting server on {host}:{port}")
    print(f"Blockchain has {len(blockchain.chain)} blocks")
    print(f"Total CVEs: {len(blockchain.get_all_cves())}")
    print(f"Pending CVEs: {len(blockchain.pending_cves)}")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=debug)
