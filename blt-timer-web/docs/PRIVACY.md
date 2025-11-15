# Privacy Policy & Data Handling

## Our Commitment to Privacy

Fresh Time Tracker is built with privacy as the foundation. We believe that productivity tracking should never compromise your personal data or security.

## Data Collection

### Activity Data
We collect the following activity metrics:

#### Keyboard Activity
- **What we collect**: Number of keystrokes per time period
- **What we DON'T collect**: Actual keys pressed, text content, passwords
- **Purpose**: Measure active work time
- **Storage**: Aggregated counts only

#### Mouse Activity  
- **What we collect**: Click counts, movement distance (pixels)
- **What we DON'T collect**: Screen coordinates, cursor screenshots, clicked elements
- **Purpose**: Measure active engagement
- **Storage**: Aggregated metrics only

#### GitHub Activity
- **What we collect**: Public event metadata (commits, PRs, issues)
- **What we DON'T collect**: Private repository content, code diffs, commit messages
- **Purpose**: Track development activity
- **Storage**: Event type, timestamp, repository name only

#### Agent Prompts
- **What we collect**: Prompt length, agent name, response length
- **What we DON'T collect**: Actual prompt content, responses, context
- **Purpose**: Measure AI assistant usage
- **Storage**: Metadata only

#### Screenshots (Optional)
- **What we collect**: NOTHING - screenshots never leave your device
- **Local processing**: Analysis happens on your machine with your own LLM
- **What we store**: Only generic activity classification (e.g., "coding")
- **Image data**: Immediately deleted after local analysis

## Data Storage

### Location
- **Primary storage**: Cloudflare KV (encrypted at rest)
- **Processing**: Cloudflare Workers (edge network)
- **Geographic distribution**: Global (follows Cloudflare's infrastructure)

### Encryption
- All data encrypted at rest using AES-256
- TLS 1.3 for data in transit
- User IDs are hashed
- GitHub tokens stored encrypted, never exposed in API responses

### Retention
- Active sessions: Retained while session is active
- Completed sessions: Configurable retention (default: 90 days)
- Activity data: Configurable retention (default: 90 days)
- Users can delete their data at any time

## Data Access

### Who Has Access
- **You**: Full access to your own data via API
- **System administrators**: No access to unencrypted user data
- **Third parties**: Zero access - we never share data

### Your Rights
- **Access**: Download all your data at any time
- **Deletion**: Delete all your data permanently
- **Portability**: Export your data in JSON format
- **Control**: Enable/disable any tracking feature

## Local LLM Processing

### How It Works
1. Screenshot captured on your local machine
2. Sent to YOUR local LLM (Ollama, LocalAI, etc.)
3. LLM analyzes and classifies activity
4. Screenshot immediately deleted
5. Only generic classification sent to server

### Guarantees
- Screenshot images NEVER uploaded to any server
- No third-party LLM services used
- All processing happens on your hardware
- You control the LLM and can inspect its behavior

## Security Measures

### Technical Safeguards
- Rate limiting to prevent abuse
- API authentication (user-provided)
- Encrypted communication (HTTPS/WSS)
- Input validation and sanitization
- Regular security audits

### Access Control
- User authentication required for all endpoints
- Session-based authorization
- No cross-user data access
- Audit logging for security events

## Compliance

### GDPR (EU)
- ✅ Data minimization
- ✅ Purpose limitation
- ✅ Right to access
- ✅ Right to deletion
- ✅ Right to portability
- ✅ Consent-based processing

### CCPA (California)
- ✅ Notice of data collection
- ✅ Right to know
- ✅ Right to delete
- ✅ Right to opt-out
- ✅ No sale of personal data

## Data Sharing

### We NEVER Share
- Individual activity data
- Screenshot images or analyses
- User credentials
- Personal information

### Public Statistics
We may publish anonymized, aggregated statistics:
- Overall usage trends (e.g., "users tracked X hours this month")
- Feature adoption rates
- Performance metrics

All statistics are:
- Anonymized (no individual users identifiable)
- Aggregated (minimum 100 users per metric)
- Opt-out available

## Third-Party Services

### Services We Use
- **Cloudflare Workers**: Infrastructure (PII: none)
- **Cloudflare KV**: Data storage (PII: encrypted)

### Services We DON'T Use
- ❌ No third-party analytics
- ❌ No third-party LLMs (OpenAI, Anthropic, etc.)
- ❌ No advertising networks
- ❌ No data brokers

## Updates to This Policy

- Policy changes announced 30 days in advance
- Users notified via email and in-app notification
- Continued use implies acceptance
- Can always review historical versions

## Contact

Privacy questions or concerns:
- Email: privacy@example.com
- Web: https://example.com/privacy
- GitHub: Open an issue with "Privacy" label

Last updated: 2024-11-15
