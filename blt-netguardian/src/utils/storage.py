"""Storage utilities for job states and vulnerabilities."""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class JobStateStore:
    """Manages job state storage using Cloudflare KV."""
    
    def __init__(self, kv_namespace):
        self.kv = kv_namespace
    
    async def save_job(self, job_id: str, job_state: Dict[str, Any]):
        """Save job state to KV store."""
        await self.kv.put(
            f"job:{job_id}",
            json.dumps(job_state)
        )
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job state from KV store."""
        result = await self.kv.get(f"job:{job_id}")
        if result:
            return json.loads(result.value if hasattr(result, 'value') else result)
        return None
    
    async def update_job_progress(self, job_id: str):
        """Update job progress after a task completes."""
        job_state = await self.get_job(job_id)
        if job_state:
            job_state['completed_tasks'] = job_state.get('completed_tasks', 0) + 1
            job_state['updated_at'] = datetime.utcnow().isoformat()
            
            # Update status if all tasks are complete
            if job_state['completed_tasks'] >= job_state['total_tasks']:
                job_state['status'] = 'completed'
            else:
                job_state['status'] = 'running'
            
            await self.save_job(job_id, job_state)
    
    async def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all jobs."""
        # In production, this would use KV list() method
        # For now, return empty list as placeholder
        return []


class VulnerabilityDatabase:
    """Manages vulnerability storage using Cloudflare KV."""
    
    def __init__(self, kv_namespace):
        self.kv = kv_namespace
    
    async def store_vulnerability(self, vuln_id: str, vulnerability: Dict[str, Any]):
        """Store a vulnerability in the database."""
        await self.kv.put(
            f"vuln:{vuln_id}",
            json.dumps(vulnerability),
            expiration_ttl=2592000  # 30 days
        )
    
    async def get_vulnerability(self, vuln_id: str) -> Optional[Dict[str, Any]]:
        """Get a vulnerability from the database."""
        result = await self.kv.get(f"vuln:{vuln_id}")
        if result:
            return json.loads(result.value if hasattr(result, 'value') else result)
        return None
    
    async def get_vulnerabilities(self, limit: int = 50, 
                                  severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get vulnerabilities from the database."""
        # In production, this would use KV list() method with filtering
        # For now, return placeholder data
        return []
    
    async def update_vulnerability_status(self, vuln_id: str, status: str):
        """Update vulnerability status (e.g., fixed, ignored, false_positive)."""
        vuln = await self.get_vulnerability(vuln_id)
        if vuln:
            vuln['status'] = status
            vuln['updated_at'] = datetime.utcnow().isoformat()
            await self.store_vulnerability(vuln_id, vuln)
    
    async def get_stats(self) -> Dict[str, int]:
        """Get vulnerability statistics."""
        # In production, this would aggregate from KV store
        return {
            'total': 0,
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0
        }
