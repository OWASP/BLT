"""
Discovery view for BLT-NetGuardian, backed by the D1 domain queue.

Targets come from researchers' clients and the operator's self-scan allowlist
(see ``self_scan.py``); this module reports on them and never invents targets.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import hashlib

from d1_compat import d1_row, d1_rows, row_get


def _iso(unix: Any) -> Optional[str]:
    try:
        return datetime.fromtimestamp(int(unix), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


class AutonomousDiscovery:
    """Autonomous target discovery engine."""
    
    def __init__(self, db=None, org_id: str = 'org-demo'):
        self.name = "Autonomous Discovery"
        self.version = "2.0.0"
        self.db = db
        self.org_id = org_id
        # Sources that actually feed the queue today.
        self.discovery_methods = ['client_crawl', 'self_scan_allowlist']
    
    async def discover_targets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Most recently discovered hosts from the shared domain queue (D1).

        Hosts arrive from researchers' clients (``POST /api/domains``) and from
        the operator's self-scan allowlist. No third-party discovery runs on
        this Worker, so there are no sample or invented targets here.
        """
        if self.db is None:
            return []
        limit = max(1, min(int(limit), 100))
        rows = d1_rows(await self.db.prepare(
            """
            SELECT host_key, status, discovered_at, last_scan_at, source_url, result_json
            FROM domain_jobs WHERE org_id = ?
            ORDER BY discovered_at DESC LIMIT ?
            """
        ).bind(self.org_id, limit).all())
        discoveries = []
        for row in rows:
            source_url = str(row_get(row, 'source_url') or '')
            discoveries.append({
                'target': row_get(row, 'host_key'),
                'type': 'domain',
                'source': 'self_scan' if source_url.startswith('netguardian:self-scan') else 'client',
                'status': row_get(row, 'status'),
                'discovered_at': _iso(row_get(row, 'discovered_at')),
                'last_scan_at': _iso(row_get(row, 'last_scan_at')),
            })
        return discoveries

    async def process_user_suggestion(self, suggestion: str, priority: bool = False) -> Dict[str, Any]:
        """
        Process a user-submitted target suggestion.
        
        Args:
            suggestion: Domain, URL, or repository suggested by user
            priority: Whether this should be scanned immediately
        
        Returns:
            Discovery record with queued status
        """
        # Parse the suggestion to determine type
        target_type = self.determine_target_type(suggestion)
        
        # Generate discovery ID
        discovery_id = hashlib.sha256(
            f"{suggestion}-{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        return {
            'discovery_id': discovery_id,
            'target': suggestion,
            'type': target_type,
            'source': 'user_suggestion',
            'discovered_at': datetime.now(timezone.utc).isoformat(),
            'priority': 'high' if priority else 'normal',
            'status': 'queued',
            'metadata': {
                'user_submitted': True
            }
        }
    
    def determine_target_type(self, suggestion: str) -> str:
        """Determine the type of target from the suggestion."""
        suggestion_lower = suggestion.lower()
        
        # Ethereum address length constant
        ETHEREUM_ADDRESS_LENGTH = 42
        
        # Check for GitHub URL - must start with github.com (after protocol removal)
        # Note: Using startswith() to ensure github.com is at URL beginning (not arbitrary position)
        normalized = suggestion_lower.replace('https://', '').replace('http://', '')
        if normalized.startswith('github.com/'):
            return 'repository'
        elif suggestion_lower.startswith('0x') and len(suggestion) == ETHEREUM_ADDRESS_LENGTH:
            return 'smart_contract'
        elif any(ext in suggestion_lower for ext in ['.com', '.io', '.org', '.net', '.dev']):
            return 'domain'
        elif 'api' in suggestion_lower:
            return 'api'
        else:
            return 'domain'  # Default to domain
    
    async def get_discovery_stats(self) -> Dict[str, int]:
        """Counts from D1: queued hosts by status and open findings."""
        stats = {
            'domains_discovered': 0,
            'repos_found': 0,
            'smart_contracts': 0,
            'active_scans': 0,
            'scanned': 0,
            'findings_open': 0,
            'contacts_made': 0,
            'total_discoveries': 0,
        }
        if self.db is None:
            return stats
        rows = d1_rows(await self.db.prepare(
            "SELECT status, COUNT(*) AS n FROM domain_jobs WHERE org_id = ? GROUP BY status"
        ).bind(self.org_id).all())
        for row in rows:
            n = int(row_get(row, 'n') or 0)
            stats['domains_discovered'] += n
            if row_get(row, 'status') == 'in_progress':
                stats['active_scans'] = n
            elif row_get(row, 'status') == 'scanned':
                stats['scanned'] = n
        stats['total_discoveries'] = stats['domains_discovered']
        row = d1_row(await self.db.prepare(
            "SELECT COUNT(*) AS n FROM findings WHERE org_id = ? AND status = 'open'"
        ).bind(self.org_id).first())
        stats['findings_open'] = int(row_get(row, 'n') or 0) if row else 0
        return stats

    async def count_scanned_since(self, since_unix: int) -> int:
        """Hosts whose last completed scan is at or after ``since_unix``."""
        if self.db is None:
            return 0
        row = d1_row(await self.db.prepare(
            """
            SELECT COUNT(*) AS n FROM domain_jobs
            WHERE org_id = ? AND status = 'scanned' AND last_scan_at >= ?
            """
        ).bind(self.org_id, int(since_unix)).first())
        return int(row_get(row, 'n') or 0) if row else 0

    async def get_current_scanning_target(self) -> Optional[Dict[str, Any]]:
        """The most recently claimed in-progress host, or None when idle."""
        if self.db is None:
            return None
        row = d1_row(await self.db.prepare(
            """
            SELECT host_key, claimed_by, claim_until FROM domain_jobs
            WHERE org_id = ? AND status = 'in_progress'
            ORDER BY claim_until DESC LIMIT 1
            """
        ).bind(self.org_id).first())
        if not row:
            return None
        return {
            'target': row_get(row, 'host_key'),
            'type': 'domain',
            'claimed_by': row_get(row, 'claimed_by'),
            'lease_until': _iso(row_get(row, 'claim_until')),
        }
