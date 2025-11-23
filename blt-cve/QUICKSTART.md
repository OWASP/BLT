# Quick Start Guide

Get the BLT-CVE decentralized CVE database up and running in minutes.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Running the Demo

See the system in action without any setup:

```bash
python demo.py
```

This will demonstrate:
- Blockchain creation
- Adding CVEs
- Mining blocks
- Querying CVEs
- User reporting
- Data persistence

## Starting the Server

```bash
python app.py
```

The API server will start on `http://localhost:5000`

## Using the CLI

The CLI provides easy access to all features:

```bash
# Check server health
python cli.py health

# Sync CVEs from NVD (last 7 days)
python cli.py sync

# Sync CVEs from last 30 days
python cli.py sync --days 30

# Mine pending CVEs into blockchain
python cli.py mine

# List all CVEs
python cli.py list

# Get specific CVE
python cli.py get CVE-2023-12345

# Report a new CVE
python cli.py report CVE-2024-99999 "Test vulnerability" --severity HIGH

# Check blockchain status
python cli.py blockchain
```

## Using the API

### Health Check
```bash
curl http://localhost:5000/health
```

### Sync CVEs from NVD
```bash
curl -X POST http://localhost:5000/sync?days=7
```

### Mine Pending CVEs
```bash
curl -X POST http://localhost:5000/mine
```

### List All CVEs
```bash
curl http://localhost:5000/cves
```

### Get Specific CVE
```bash
curl http://localhost:5000/cves/CVE-2023-12345
```

### Report New CVE
```bash
curl -X POST http://localhost:5000/report \
  -H "Content-Type: application/json" \
  -d '{
    "cve_id": "CVE-2024-99999",
    "description": "Test vulnerability",
    "severity": "HIGH",
    "reporter": "your_name"
  }'
```

## Complete Workflow

1. **Start the server:**
```bash
python app.py
```

2. **In another terminal, sync CVEs:**
```bash
python cli.py sync --days 7
```

3. **Mine them into the blockchain:**
```bash
python cli.py mine
```

4. **Check the results:**
```bash
python cli.py list
python cli.py blockchain
```

## Running Tests

```bash
python test_system.py
```

## Configuration

Create a `.env` file (optional):

```bash
cp .env.example .env
```

Edit `.env` to add your NVD API key for higher rate limits:
- Get a free API key from: https://nvd.nist.gov/developers/request-an-api-key

## Common Operations

### Full Sync and Mine
```bash
python cli.py sync --days 30 && python cli.py mine
```

### Check System Status
```bash
python cli.py health && python cli.py blockchain
```

### Report and Mine User CVE
```bash
python cli.py report CVE-2024-12345 "New vulnerability" --severity CRITICAL
python cli.py mine
```

## Troubleshooting

**Server won't start?**
- Check if port 5000 is available
- Install all dependencies: `pip install -r requirements.txt`

**Can't sync from NVD?**
- Add NVD API key to `.env` file
- Check internet connection
- NVD may have rate limits without API key

**Tests failing?**
- Ensure all dependencies are installed
- Run: `pip install -r requirements.txt`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API endpoints at http://localhost:5000/
- Check out the source code to understand the implementation
- Contribute to the project!
