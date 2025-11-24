# BLT-CVE: Decentralized CVE Database

A resilient, blockchain-based CVE (Common Vulnerabilities and Exposures) database that ensures continuity of service and community contribution. This system backs up the main CVE database from multiple sources and stores data on a blockchain for immutability and decentralization.

## 🎯 Features

- **Blockchain Storage**: CVE data stored on an immutable blockchain for tamper-proof records
- **Multi-Source Backup**: Automatically backs up CVEs from NVD (National Vulnerability Database)
- **Community Reporting**: Users can report new CVEs directly to the system
- **Resilient Design**: Decentralized architecture ensures the database stays online
- **RESTful API**: Easy-to-use API for querying and managing CVE data
- **Local Caching**: Redundant local storage for additional reliability

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/OWASP-BLT/BLT-CVE.git
cd BLT-CVE
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment (optional):
```bash
cp .env.example .env
# Edit .env with your NVD API key (optional but recommended for higher rate limits)
```

### Running the Server

Start the API server:
```bash
python app.py
```

The server will start on `http://localhost:5000`

## 📖 API Documentation

### Health Check
```bash
GET /health
```
Returns the health status of the system and blockchain validity.

### Get All CVEs
```bash
GET /cves
```
Retrieves all CVEs from the blockchain. Supports filtering:
- `?severity=HIGH` - Filter by severity
- `?source=NVD` - Filter by source

### Get Specific CVE
```bash
GET /cves/<cve_id>
```
Example: `GET /cves/CVE-2023-12345`

### Report a New CVE
```bash
POST /report
Content-Type: application/json

{
  "cve_id": "CVE-2024-12345",
  "description": "Description of the vulnerability",
  "severity": "HIGH",
  "cvss_score": 7.5,
  "references": [
    {"url": "https://example.com/advisory", "source": "vendor"}
  ],
  "reporter": "your_name"
}
```

### Sync from NVD
```bash
POST /sync?days=7
```
Fetches recent CVEs from NVD (last 7 days by default) and adds them to pending.

### Mine Pending CVEs
```bash
POST /mine
```
Mines all pending CVEs into a new block on the blockchain.

### Search for CVE
```bash
GET /search?cve_id=CVE-2023-12345
```
Searches for a CVE in the blockchain and NVD.

### Get Blockchain Status
```bash
GET /blockchain
```
Returns blockchain status and statistics.

## 🔄 Workflow Example

1. **Sync CVEs from NVD**:
```bash
curl -X POST http://localhost:5000/sync?days=7
```

2. **Mine them into the blockchain**:
```bash
curl -X POST http://localhost:5000/mine
```

3. **Query CVEs**:
```bash
curl http://localhost:5000/cves
```

4. **Report a new CVE**:
```bash
curl -X POST http://localhost:5000/report \
  -H "Content-Type: application/json" \
  -d '{
    "cve_id": "CVE-2024-99999",
    "description": "Test vulnerability",
    "severity": "MEDIUM",
    "reporter": "community_user"
  }'
```

5. **Mine the reported CVE**:
```bash
curl -X POST http://localhost:5000/mine
```

## 🏗️ Architecture

### Components

1. **Blockchain (`blockchain.py`)**: 
   - Simple proof-of-work blockchain implementation
   - Stores CVE data in immutable blocks
   - Validates chain integrity

2. **CVE Fetcher (`cve_fetcher.py`)**:
   - Fetches CVE data from NVD API
   - Supports multiple data sources for redundancy
   - Local caching for backup

3. **API Server (`app.py`)**:
   - Flask-based REST API
   - Endpoints for querying and managing CVEs
   - User reporting interface

### Data Flow

```
NVD API → CVE Fetcher → Pending CVEs → Mining → Blockchain
                                    ↑
                              User Reports
```

## 🔐 Security & Resilience

- **Immutability**: Once CVEs are mined into the blockchain, they cannot be altered
- **Decentralization**: Blockchain can be distributed across multiple nodes
- **Redundancy**: Multiple backup sources and local caching
- **Validation**: Blockchain integrity is continuously verified
- **Community Contribution**: Users can report CVEs even if official sources are unavailable

## 📊 Blockchain Details

- **Difficulty**: Configurable proof-of-work difficulty (default: 4)
- **Block Structure**: Each block contains a batch of CVEs with metadata
- **Hash Algorithm**: SHA-256
- **Persistence**: Blockchain saved to JSON file for durability

## 🔧 Configuration

Environment variables (`.env` file):

```bash
# NVD API Configuration
NVD_API_KEY=your_api_key_here  # Get from https://nvd.nist.gov/developers/request-an-api-key
NVD_API_URL=https://services.nvd.nist.gov/rest/json/cves/2.0

# Server Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False

# Blockchain Configuration
BLOCKCHAIN_DIFFICULTY=4  # Higher = more secure but slower
```

## 📝 License

This project is licensed under the terms included in the LICENSE file.

## 🤝 Contributing

Contributions are welcome! This is an OWASP project aimed at ensuring CVE database resilience.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 🌐 OWASP BLT

This project is part of the OWASP BLT initiative. Visit [BLT Website](https://owasp.org/www-project-buglogging-tool/) for more information.

## ⚠️ Important Notes

- This is a backup/mirror system and should not replace official CVE sources
- Always verify critical CVE information with official sources
- NVD API key is recommended for production use to avoid rate limiting
- The blockchain file can grow large over time; plan for storage accordingly
