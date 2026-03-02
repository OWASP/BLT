"""Storage utilities for job states and vulnerabilities."""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class JobStateStore:
    """Manages job state storage using Cloudflare D1."""

    def __init__(self, db):
        self.db = db

    async def save_job(self, job_id: str, job_state: Dict[str, Any]):
        """Save job state to D1 database."""
        if self.db is None:
            return
        task_ids_json = json.dumps(job_state.get('task_ids', []))
        await self.db.prepare(
            """INSERT INTO jobs (job_id, target_id, status, total_tasks, completed_tasks,
               created_at, updated_at, task_ids, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(job_id) DO UPDATE SET
               status=excluded.status, total_tasks=excluded.total_tasks,
               completed_tasks=excluded.completed_tasks, updated_at=excluded.updated_at,
               task_ids=excluded.task_ids"""
        ).bind(
            job_id,
            job_state.get('target_id', ''),
            job_state.get('status', 'queued'),
            job_state.get('total_tasks', 0),
            job_state.get('completed_tasks', 0),
            job_state.get('created_at', datetime.utcnow().isoformat()),
            job_state.get('updated_at'),
            task_ids_json,
            job_state.get('source')
        ).run()

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job state from D1 database."""
        if self.db is None:
            return None
        row = await self.db.prepare(
            "SELECT * FROM jobs WHERE job_id = ?"
        ).bind(job_id).first()
        if row is None:
            return None
        return {
            'job_id': row['job_id'],
            'target_id': row['target_id'],
            'status': row['status'],
            'total_tasks': row['total_tasks'],
            'completed_tasks': row['completed_tasks'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'task_ids': json.loads(row['task_ids']) if row['task_ids'] else [],
            'source': row['source']
        }

    async def update_job_progress(self, job_id: str):
        """Update job progress after a task completes."""
        if self.db is None:
            return
        job_state = await self.get_job(job_id)
        if job_state:
            completed = job_state.get('completed_tasks', 0) + 1
            total = job_state.get('total_tasks', 0)
            status = 'completed' if completed >= total else 'running'
            updated_at = datetime.utcnow().isoformat()
            await self.db.prepare(
                """UPDATE jobs SET completed_tasks = ?, status = ?, updated_at = ?
                   WHERE job_id = ?"""
            ).bind(completed, status, updated_at, job_id).run()

    async def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all jobs."""
        if self.db is None:
            return []
        result = await self.db.prepare(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?"
        ).bind(limit).all()
        jobs = []
        for row in (result.results if result else []):
            jobs.append({
                'job_id': row['job_id'],
                'target_id': row['target_id'],
                'status': row['status'],
                'total_tasks': row['total_tasks'],
                'completed_tasks': row['completed_tasks'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'task_ids': json.loads(row['task_ids']) if row['task_ids'] else [],
                'source': row['source']
            })
        return jobs


class TaskQueueStore:
    """Manages task queue storage using Cloudflare D1."""

    def __init__(self, db):
        self.db = db

    async def save_task(self, task_dict: Dict[str, Any]):
        """Save a task to D1 database."""
        if self.db is None:
            return
        await self.db.prepare(
            """INSERT INTO tasks (task_id, job_id, target_id, task_type, priority, status,
               created_at, started_at, completed_at, result_id, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(task_id) DO UPDATE SET
               status=excluded.status, started_at=excluded.started_at,
               completed_at=excluded.completed_at, result_id=excluded.result_id,
               error=excluded.error"""
        ).bind(
            task_dict.get('task_id'),
            task_dict.get('job_id'),
            task_dict.get('target_id'),
            task_dict.get('task_type'),
            task_dict.get('priority'),
            task_dict.get('status', 'queued'),
            task_dict.get('created_at', datetime.utcnow().isoformat()),
            task_dict.get('started_at'),
            task_dict.get('completed_at'),
            task_dict.get('result_id'),
            task_dict.get('error')
        ).run()

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task from D1 database."""
        if self.db is None:
            return None
        row = await self.db.prepare(
            "SELECT * FROM tasks WHERE task_id = ?"
        ).bind(task_id).first()
        if row is None:
            return None
        return {
            'task_id': row['task_id'],
            'job_id': row['job_id'],
            'target_id': row['target_id'],
            'task_type': row['task_type'],
            'priority': row['priority'],
            'status': row['status'],
            'created_at': row['created_at'],
            'started_at': row['started_at'],
            'completed_at': row['completed_at'],
            'result_id': row['result_id'],
            'error': row['error']
        }

    async def update_task(self, task_id: str, updates: Dict[str, Any]):
        """Update a task in D1 database."""
        if self.db is None:
            return
        allowed = ('status', 'started_at', 'completed_at', 'result_id', 'error')
        fields = {k: v for k, v in updates.items() if k in allowed}
        if not fields:
            return
        set_clause = ', '.join(f"{col} = ?" for col in fields)
        values = list(fields.values()) + [task_id]
        await self.db.prepare(
            f"UPDATE tasks SET {set_clause} WHERE task_id = ?"
        ).bind(*values).run()


class TargetRegistryStore:
    """Manages target registry storage using Cloudflare D1."""

    def __init__(self, db):
        self.db = db

    async def save_target(self, target_dict: Dict[str, Any]):
        """Save a target to D1 database."""
        if self.db is None:
            return
        scan_types_json = json.dumps(target_dict.get('scan_types', []))
        await self.db.prepare(
            """INSERT INTO targets (target_id, target_type, target_url, scan_types, notes, registered_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(target_id) DO UPDATE SET
               target_type=excluded.target_type, target_url=excluded.target_url,
               scan_types=excluded.scan_types, notes=excluded.notes"""
        ).bind(
            target_dict.get('target_id'),
            target_dict.get('target_type'),
            target_dict.get('target_url'),
            scan_types_json,
            target_dict.get('notes', ''),
            target_dict.get('registered_at', datetime.utcnow().isoformat())
        ).run()

    async def get_target(self, target_id: str) -> Optional[Dict[str, Any]]:
        """Get a target from D1 database."""
        if self.db is None:
            return None
        if target_id is None:
            return None
        row = await self.db.prepare(
            "SELECT * FROM targets WHERE target_id = ?"
        ).bind(target_id).first()
        if row is None:
            return None
        return {
            'target_id': row['target_id'],
            'target_type': row['target_type'],
            'target_url': row['target_url'],
            'scan_types': json.loads(row['scan_types']) if row['scan_types'] else [],
            'notes': row['notes'],
            'registered_at': row['registered_at']
        }


class VulnerabilityDatabase:
    """Manages vulnerability storage using Cloudflare D1."""

    def __init__(self, db):
        self.db = db

    async def store_vulnerability(self, vuln_id: str, vulnerability: Dict[str, Any]):
        """Store a vulnerability in the database."""
        if self.db is None:
            return
        await self.db.prepare(
            """INSERT INTO vulnerabilities (vuln_id, result_id, task_id, type, severity,
               data, discovered_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(vuln_id) DO UPDATE SET
               data=excluded.data, status=excluded.status"""
        ).bind(
            vuln_id,
            vulnerability.get('result_id'),
            vulnerability.get('task_id'),
            vulnerability.get('type'),
            vulnerability.get('severity'),
            json.dumps(vulnerability),
            vulnerability.get('discovered_at', datetime.utcnow().isoformat()),
            vulnerability.get('status', 'open')
        ).run()

    async def get_vulnerability(self, vuln_id: str) -> Optional[Dict[str, Any]]:
        """Get a vulnerability from the database."""
        if self.db is None:
            return None
        row = await self.db.prepare(
            "SELECT data FROM vulnerabilities WHERE vuln_id = ?"
        ).bind(vuln_id).first()
        if row is None:
            return None
        return json.loads(row['data'])

    async def get_vulnerabilities(self, limit: int = 50,
                                  severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get vulnerabilities from the database."""
        if self.db is None:
            return []
        if severity:
            result = await self.db.prepare(
                "SELECT data FROM vulnerabilities WHERE severity = ? ORDER BY discovered_at DESC LIMIT ?"
            ).bind(severity, limit).all()
        else:
            result = await self.db.prepare(
                "SELECT data FROM vulnerabilities ORDER BY discovered_at DESC LIMIT ?"
            ).bind(limit).all()
        vulns = []
        for row in (result.results if result else []):
            vulns.append(json.loads(row['data']))
        return vulns

    async def update_vulnerability_status(self, vuln_id: str, status: str):
        """Update vulnerability status (e.g., fixed, ignored, false_positive)."""
        if self.db is None:
            return
        updated_at = datetime.utcnow().isoformat()
        vuln = await self.get_vulnerability(vuln_id)
        if vuln:
            vuln['status'] = status
            vuln['updated_at'] = updated_at
            await self.db.prepare(
                "UPDATE vulnerabilities SET status = ?, updated_at = ?, data = ? WHERE vuln_id = ?"
            ).bind(status, updated_at, json.dumps(vuln), vuln_id).run()

    async def get_stats(self) -> Dict[str, int]:
        """Get vulnerability statistics."""
        if self.db is None:
            return {'total': 0, 'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        result = await self.db.prepare(
            "SELECT severity, COUNT(*) as count FROM vulnerabilities GROUP BY severity"
        ).all()
        stats = {'total': 0, 'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        for row in (result.results if result else []):
            severity = row['severity'] or 'info'
            count = row['count']
            stats[severity] = count
            stats['total'] += count
        return stats
