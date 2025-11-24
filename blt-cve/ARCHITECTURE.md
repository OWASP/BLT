# BLT-CVE Architecture

## Overview

BLT-CVE is a decentralized CVE (Common Vulnerabilities and Exposures) database built on blockchain technology to ensure resilience, immutability, and community participation. The system backs up the official NVD database and allows users to contribute CVE reports.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      External Sources                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │   NVD    │  │  MITRE   │  │   Other  │  │  Users   │    │
│  │   API    │  │   CVE    │  │  Sources │  │ Reports  │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │       CVE Fetcher Module             │
        │  - Data normalization                │
        │  - Multi-source aggregation          │
        │  - Local caching                     │
        │  - Data validation                   │
        └─────────────┬───────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────────┐
        │      Pending CVEs Queue              │
        │  - Temporary storage                 │
        │  - Deduplication                     │
        │  - Batch preparation                 │
        └─────────────┬───────────────────────┘
                      │
                      ▼ (Mining Operation)
        ┌─────────────────────────────────────┐
        │       Blockchain Engine              │
        │  ┌─────────────────────────────┐    │
        │  │  Block 0: Genesis           │    │
        │  └─────────────────────────────┘    │
        │  ┌─────────────────────────────┐    │
        │  │  Block 1: CVE Batch 1       │    │
        │  │  - CVE-2023-XXXX            │    │
        │  │  - CVE-2023-YYYY            │    │
        │  │  - ...                      │    │
        │  └─────────────────────────────┘    │
        │  ┌─────────────────────────────┐    │
        │  │  Block 2: CVE Batch 2       │    │
        │  └─────────────────────────────┘    │
        │          ...                         │
        └─────────────┬───────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────────┐
        │      Persistence Layer               │
        │  - JSON file storage                 │
        │  - Blockchain state                  │
        │  - Cache files                       │
        └─────────────┬───────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────────┐
        │         API Server                   │
        │  - REST endpoints                    │
        │  - Query interface                   │
        │  - Report submissions                │
        │  - Health monitoring                 │
        └─────────────┬───────────────────────┘
                      │
        ┌─────────────┴───────────────┐
        │                             │
        ▼                             ▼
┌──────────────┐            ┌──────────────┐
│   CLI Tool   │            │  Web Clients │
│              │            │              │
└──────────────┘            └──────────────┘
```

## Components

### 1. Blockchain Engine (`blockchain.py`)

**Purpose**: Core blockchain implementation for immutable CVE storage

**Key Features**:
- SHA-256 cryptographic hashing
- Proof-of-work consensus mechanism
- Configurable mining difficulty
- Chain validation
- Block persistence

**Data Structure**:
```python
Block:
  - index: Block number in chain
  - timestamp: Creation time
  - data: CVE batch information
  - previous_hash: Link to previous block
  - nonce: Proof-of-work nonce
  - hash: Block's SHA-256 hash

Blockchain:
  - chain: List of blocks
  - pending_cves: CVEs waiting to be mined
  - difficulty: Mining difficulty level
```

**Security**:
- Immutable once mined
- Tamper-evident (any change invalidates chain)
- Proof-of-work prevents rapid chain manipulation

### 2. CVE Fetcher (`cve_fetcher.py`)

**Purpose**: Fetch and normalize CVE data from multiple sources

**Key Features**:
- NVD API v2.0 integration
- Data extraction and normalization
- Local caching for redundancy
- Multi-source capability (extensible)
- Search functionality

**Data Sources**:
1. **Primary**: NVD (National Vulnerability Database)
   - Official CVE data
   - CVSS scores
   - References and metadata
   
2. **Alternative**: Configurable fallback sources
   - MITRE CVE
   - CVE Details
   - Other databases

**Caching Strategy**:
- Timestamp-based cache files
- JSON format for portability
- Redundant local storage

### 3. API Server (`app.py`)

**Purpose**: RESTful API for system interaction

**Endpoints**:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | API documentation |
| GET | `/health` | Health check |
| GET | `/blockchain` | Blockchain status |
| GET | `/cves` | List all CVEs |
| GET | `/cves/<id>` | Get specific CVE |
| POST | `/report` | Report new CVE |
| POST | `/sync` | Sync from NVD |
| POST | `/mine` | Mine pending CVEs |
| GET | `/search` | Search CVE by ID |

**Features**:
- JSON responses
- Query parameter filtering
- Error handling
- Auto-save blockchain
- CORS ready (can be enabled)

### 4. CLI Tool (`cli.py`)

**Purpose**: Command-line interface for operations

**Commands**:
- `health`: System status
- `sync`: Fetch from NVD
- `mine`: Mine pending CVEs
- `list`: Display CVEs
- `get`: Query specific CVE
- `report`: Submit new CVE
- `blockchain`: Chain status

**Benefits**:
- Scriptable operations
- Batch processing
- Automation friendly
- User-friendly output

## Data Flow

### 1. CVE Ingestion Flow

```
External Source → CVE Fetcher → Validation → Pending Queue
                                    ↓
                            Check for duplicates
                                    ↓
                              Add to pending
```

### 2. Mining Flow

```
Pending CVEs → Batch preparation → Create block → Proof-of-work
                                         ↓
                              Calculate hash (nonce++)
                                         ↓
                          Hash meets difficulty? → Add to chain
                                         ↓
                              Save to persistent storage
```

### 3. Query Flow

```
API Request → Parse parameters → Query blockchain
                                       ↓
                              Extract CVE data
                                       ↓
                          Filter (if parameters)
                                       ↓
                              Return JSON response
```

## Blockchain Mechanics

### Block Structure

Each block contains:
- **Index**: Sequential block number
- **Timestamp**: Creation time (Unix timestamp)
- **Data**: Batch of CVEs with metadata
- **Previous Hash**: Links to parent block
- **Nonce**: Proof-of-work counter
- **Hash**: Block's unique identifier

### Mining Process

1. Collect pending CVEs into batch
2. Create new block with batch data
3. Link to previous block via hash
4. Start proof-of-work:
   - Calculate block hash
   - Check if hash meets difficulty (leading zeros)
   - If not, increment nonce and retry
5. Once valid hash found, add to chain
6. Save blockchain to disk

### Difficulty

Configurable via `BLOCKCHAIN_DIFFICULTY`:
- Higher = More secure, slower mining
- Lower = Faster mining, less computational cost
- Default: 4 (4 leading zeros = ~65,536 attempts)

### Validation

Chain validation checks:
1. Each block's hash is correctly calculated
2. Each block properly links to previous block
3. All blocks meet difficulty requirement
4. No tampering or corruption

## Resilience Features

### 1. Decentralization
- Blockchain can be distributed across nodes
- No single point of failure
- Community-driven

### 2. Redundancy
- Multiple data sources
- Local caching
- Persistent storage
- Blockchain immutability

### 3. Availability
- Continue operating if NVD is down
- User reports provide alternative data source
- Local cache serves as backup

### 4. Integrity
- Cryptographic verification
- Tamper-evident design
- Chain validation

## Scalability Considerations

### Current Implementation
- Single-node blockchain
- File-based persistence
- Suitable for moderate scale (thousands of CVEs)

### Future Enhancements
- Distributed nodes (P2P network)
- Database backend (PostgreSQL, MongoDB)
- Sharding for large datasets
- API rate limiting
- Caching layer (Redis)
- Message queue for async processing

## Security

### Data Integrity
- SHA-256 cryptographic hashing
- Chain validation prevents tampering
- Immutable once mined

### API Security
- Input validation on all endpoints
- JSON parsing safeguards
- Error handling prevents information leakage

### Future Security Enhancements
- Authentication/Authorization (JWT, OAuth)
- Rate limiting
- HTTPS/TLS encryption
- API key management
- Audit logging

## Performance

### Metrics
- Mining time: ~1-60 seconds (depends on difficulty)
- Query time: <100ms for most operations
- Sync time: Depends on NVD API response
- Storage: ~1KB per CVE (JSON format)

### Optimization Opportunities
- Index CVE IDs for faster lookups
- Compress blockchain data
- Cache frequently accessed CVEs
- Batch sync operations
- Async mining

## Deployment

### Development
```bash
python app.py  # Runs on localhost:5000
```

### Production Considerations
- Use WSGI server (Gunicorn, uWSGI)
- Reverse proxy (Nginx, Apache)
- Process manager (systemd, supervisor)
- Environment-based configuration
- Log aggregation
- Monitoring and alerting

### Example Production Setup
```
Internet → Nginx (443) → Gunicorn → Flask App
                                        ↓
                                  Blockchain Storage
```

## Monitoring

### Health Checks
- `/health` endpoint
- Blockchain validity
- Pending CVE count
- Block count

### Metrics to Track
- API response times
- Mining duration
- Sync success rate
- Error rates
- Storage usage
- Chain validation time

## Future Roadmap

### Phase 1 (Current)
✅ Core blockchain implementation
✅ NVD integration
✅ User reporting
✅ REST API
✅ CLI tool

### Phase 2 (Planned)
- Web interface
- Enhanced search
- CVE analytics
- Export functionality
- Webhook notifications

### Phase 3 (Future)
- Distributed nodes (P2P)
- Consensus mechanism
- Smart contracts for validation
- Integration with security tools
- Real-time updates
- Mobile app

## Contributing

See main README.md for contribution guidelines.

## License

See LICENSE file for terms and conditions.
