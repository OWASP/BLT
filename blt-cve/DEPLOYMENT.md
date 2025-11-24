# Deployment Guide

This guide covers deploying the BLT-CVE decentralized CVE database in various environments.

## Quick Deploy (Development)

```bash
# Clone repository
git clone https://github.com/OWASP-BLT/BLT-CVE.git
cd BLT-CVE

# Install dependencies
pip install -r requirements.txt

# Start server
python app.py
```

Server will be available at `http://localhost:5000`

## Production Deployment

### Prerequisites

- Python 3.7+
- pip
- Web server (Nginx/Apache) - recommended
- Process manager (systemd/supervisor) - recommended
- NVD API key (optional but recommended)

### 1. System Setup

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash bltcve

# Create application directory
sudo mkdir -p /opt/blt-cve
sudo chown bltcve:bltcve /opt/blt-cve

# Switch to application user
sudo su - bltcve
```

### 2. Application Setup

```bash
cd /opt/blt-cve

# Clone repository
git clone https://github.com/OWASP-BLT/BLT-CVE.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install production WSGI server
pip install gunicorn
```

### 3. Configuration

```bash
# Copy and edit environment file
cp .env.example .env
nano .env
```

Configure:
- `NVD_API_KEY`: Your NVD API key
- `FLASK_HOST`: 127.0.0.1 (if behind proxy)
- `FLASK_PORT`: 5000 or custom port
- `BLOCKCHAIN_DIFFICULTY`: 4-6 for production

### 4. Systemd Service

Create `/etc/systemd/system/blt-cve.service`:

```ini
[Unit]
Description=BLT-CVE Decentralized CVE Database
After=network.target

[Service]
Type=simple
User=bltcve
WorkingDirectory=/opt/blt-cve
Environment="PATH=/opt/blt-cve/venv/bin"
ExecStart=/opt/blt-cve/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable blt-cve
sudo systemctl start blt-cve
sudo systemctl status blt-cve
```

### 5. Nginx Configuration

Create `/etc/nginx/sites-available/blt-cve`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Optional: rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20;
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/blt-cve /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. SSL/TLS with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 7. Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Deny direct access to app port (optional)
sudo ufw deny 5000/tcp
```

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN mkdir -p blockchain_data cve_cache

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  blt-cve:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./blockchain_data:/app/blockchain_data
      - ./cve_cache:/app/cve_cache
    environment:
      - NVD_API_KEY=${NVD_API_KEY}
      - BLOCKCHAIN_DIFFICULTY=4
    restart: unless-stopped
```

Build and run:

```bash
docker-compose up -d
```

## Cloud Deployment

### AWS EC2

1. Launch EC2 instance (t2.small or larger)
2. Configure security group (ports 80, 443)
3. Follow production deployment steps
4. Use Elastic IP for static address
5. Consider RDS for future database needs

### Google Cloud Platform

```bash
# Deploy to Google App Engine
gcloud app deploy

# Or use Compute Engine
gcloud compute instances create blt-cve \
  --image-family=ubuntu-2004-lts \
  --machine-type=e2-small
```

### Heroku

Create `Procfile`:

```
web: gunicorn app:app
```

Deploy:

```bash
heroku create your-app-name
git push heroku main
heroku config:set NVD_API_KEY=your_key
```

## Monitoring

### Health Checks

```bash
# Simple health check
curl http://localhost:5000/health

# Detailed status
curl http://localhost:5000/blockchain
```

### Logging

Configure logging in production:

```python
# Add to app.py
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/blt-cve/app.log'),
        logging.StreamHandler()
    ]
)
```

### Monitoring Tools

- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **ELK Stack**: Log aggregation
- **Uptime Robot**: Availability monitoring

## Maintenance

### Backup Blockchain

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR=/backup/blt-cve
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp /opt/blt-cve/blockchain_data/cve_blockchain.json \
   $BACKUP_DIR/blockchain_$DATE.json

# Keep only last 30 days
find $BACKUP_DIR -name "blockchain_*.json" -mtime +30 -delete
```

Add to crontab:

```bash
0 0 * * * /usr/local/bin/backup-blt-cve.sh
```

### Updates

```bash
# Pull latest code
cd /opt/blt-cve
git pull

# Activate virtualenv
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Restart service
sudo systemctl restart blt-cve
```

### Sync CVEs Automatically

```bash
# Add to crontab
0 */6 * * * curl -X POST http://localhost:5000/sync?days=1
5 */6 * * * curl -X POST http://localhost:5000/mine
```

This syncs and mines CVEs every 6 hours.

## Performance Tuning

### Gunicorn Workers

```bash
# Rule of thumb: (2 x CPU cores) + 1
gunicorn -w 9 -b 0.0.0.0:5000 app:app
```

### Nginx Caching

Add to Nginx config:

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=blt_cache:10m;

location / {
    proxy_cache blt_cache;
    proxy_cache_valid 200 5m;
    # ... rest of proxy config
}
```

### Database Migration (Future)

For large scale, consider migrating to PostgreSQL:

1. Install PostgreSQL
2. Update blockchain.py to use database backend
3. Migrate existing JSON data
4. Update connection in app.py

## Security Hardening

### API Rate Limiting

```bash
# Install Flask-Limiter
pip install Flask-Limiter

# Add to app.py
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: request.remote_addr)

@limiter.limit("100 per hour")
@app.route('/sync')
def sync_cves():
    # ...
```

### HTTPS Only

Update Nginx:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

### API Authentication (Optional)

For future enhancement, add JWT authentication:

```bash
pip install PyJWT Flask-JWT-Extended
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u blt-cve -n 50

# Check permissions
ls -la /opt/blt-cve/blockchain_data

# Test manually
source /opt/blt-cve/venv/bin/activate
cd /opt/blt-cve
python app.py
```

### High Memory Usage

- Reduce Gunicorn workers
- Implement caching
- Lower blockchain difficulty
- Archive old blocks

### Slow Mining

- Adjust `BLOCKCHAIN_DIFFICULTY` lower
- Use more CPU cores
- Batch smaller numbers of CVEs

## Scaling

### Horizontal Scaling

1. Use shared storage (NFS/S3) for blockchain
2. Load balancer (Nginx/HAProxy)
3. Multiple application servers
4. Consistent hashing for distribution

### Vertical Scaling

- Increase server resources
- Use SSD storage
- Add more RAM for caching

## Support

For issues and questions:
- GitHub Issues: https://github.com/OWASP-BLT/BLT-CVE/issues
- OWASP BLT: https://owasp.org/www-project-buglogging-tool/

## License

See LICENSE file for details.
