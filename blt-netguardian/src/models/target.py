"""Target model for scan targets."""
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class TargetType(str, Enum):
    """Target type enumeration."""
    WEB2 = "web2"
    WEB3 = "web3"
    API = "api"
    REPO = "repo"
    CONTRACT = "contract"


@dataclass
class Target:
    """Scan target."""
    target_id: str
    target_type: str
    target_url: str
    scan_types: List[str]
    notes: str
    registered_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert target to dictionary."""
        return {
            'target_id': self.target_id,
            'target_type': self.target_type,
            'target_url': self.target_url,
            'scan_types': self.scan_types,
            'notes': self.notes,
            'registered_at': self.registered_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Target':
        """Create target from dictionary."""
        return cls(
            target_id=data['target_id'],
            target_type=data['target_type'],
            target_url=data['target_url'],
            scan_types=data.get('scan_types', []),
            notes=data.get('notes', ''),
            registered_at=data['registered_at']
        )
