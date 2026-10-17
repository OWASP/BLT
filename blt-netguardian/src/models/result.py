"""Result model for scan results."""
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class VulnerabilityLevel(str, Enum):
    """Vulnerability severity level."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ScanResult:
    """Security scan result."""
    result_id: str
    task_id: str
    agent_type: str
    findings: List[Dict[str, Any]]
    vulnerabilities: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'result_id': self.result_id,
            'task_id': self.task_id,
            'agent_type': self.agent_type,
            'findings': self.findings,
            'vulnerabilities': self.vulnerabilities,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanResult':
        """Create result from dictionary."""
        return cls(
            result_id=data['result_id'],
            task_id=data['task_id'],
            agent_type=data['agent_type'],
            findings=data.get('findings', []),
            vulnerabilities=data.get('vulnerabilities', []),
            metadata=data.get('metadata', {}),
            timestamp=data['timestamp']
        )


@dataclass
class Vulnerability:
    """Security vulnerability."""
    vulnerability_id: str
    type: str
    severity: VulnerabilityLevel
    title: str
    description: str
    affected_component: str
    cve_id: str = None
    cvss_score: float = None
    remediation: str = None
    references: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert vulnerability to dictionary."""
        return {
            'vulnerability_id': self.vulnerability_id,
            'type': self.type,
            'severity': self.severity.value if isinstance(self.severity, VulnerabilityLevel) else self.severity,
            'title': self.title,
            'description': self.description,
            'affected_component': self.affected_component,
            'cve_id': self.cve_id,
            'cvss_score': self.cvss_score,
            'remediation': self.remediation,
            'references': self.references or []
        }
