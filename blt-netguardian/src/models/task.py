"""Task model for security scanning tasks."""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Task type enumeration."""
    CRAWLER = "crawler"
    STATIC_ANALYSIS = "static_analysis"
    CONTRACT_AUDIT = "contract_audit"
    VULNERABILITY_SCAN = "vulnerability_scan"
    PENETRATION_TEST = "penetration_test"
    WEB3_MONITOR = "web3_monitor"


@dataclass
class Task:
    """Security scanning task."""
    task_id: str
    job_id: str
    target_id: str
    task_type: str
    priority: str
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_id: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            'task_id': self.task_id,
            'job_id': self.job_id,
            'target_id': self.target_id,
            'task_type': self.task_type,
            'priority': self.priority,
            'status': self.status.value if isinstance(self.status, TaskStatus) else self.status,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'result_id': self.result_id,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary."""
        return cls(
            task_id=data['task_id'],
            job_id=data['job_id'],
            target_id=data['target_id'],
            task_type=data['task_type'],
            priority=data['priority'],
            status=TaskStatus(data['status']),
            created_at=data['created_at'],
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            result_id=data.get('result_id'),
            error=data.get('error')
        )
