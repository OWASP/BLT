"""Scanner coordinator that manages all scanning agents."""
from typing import List, Dict, Any
from scanners.web2_crawler import Web2Crawler
from scanners.web3_monitor import Web3Monitor
from scanners.static_analyzer import StaticAnalyzer
from scanners.contract_scanner import ContractScanner
from scanners.volunteer_agent import VolunteerAgentManager

# Global scanner registry
_SCANNER_REGISTRY: Dict[str, type] = {}


def register_scanner(task_type: str, scanner_class: type) -> None:
    """Register a scanner class for a given task type."""
    if not task_type:
        raise ValueError("task_type must be a non-empty string")
    if task_type in _SCANNER_REGISTRY:
        raise ValueError(
            f"Scanner already registered for task type: '{task_type}'. "
            f"Existing: {_SCANNER_REGISTRY[task_type].__name__}, "
            f"New: {scanner_class.__name__}"
        )
    for required_method in ("scan", "get_status"):
        if not hasattr(scanner_class, required_method):
            raise TypeError(
                f"{scanner_class.__name__} must define `{required_method}`"
            )
    _SCANNER_REGISTRY[task_type] = scanner_class


register_scanner('crawler', Web2Crawler)
register_scanner('web3_monitor', Web3Monitor)
register_scanner('static_analysis', StaticAnalyzer)
register_scanner('contract_audit', ContractScanner)
register_scanner('vulnerability_scan', Web2Crawler)  # intentionally reuses Web2Crawler
register_scanner('penetration_test', VolunteerAgentManager)


class ScannerCoordinator:
    """Coordinates all security scanning agents."""

    def __init__(self):
        """Initialize coordinator from registry."""
        # TODO: Accept env parameter when scanners need environment config
        self.scanner_map = {
            task_type: scanner_class()
            for task_type, scanner_class in _SCANNER_REGISTRY.items()
        }

    async def process_job(self, job_id: str, tasks: List[Any]) -> List[Dict[str, Any]]:
        """Process all tasks in a job and return results."""
        results = []
        for task in tasks:
            result = await self.process_task(task)
            results.append(result)
        return results

    async def process_task(self, task) -> Dict[str, Any]:
        """Process a single task by dispatching to appropriate scanner."""
        task_type = task.task_type
        scanner = self.scanner_map.get(task_type)

        if not scanner:
            return {
                'success': False,
                'error': f'No scanner available for task type: {task_type}'
            }

        try:
            result = await scanner.scan(task)
            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def get_scanner_status(self, scanner_type: str) -> Dict[str, Any]:
        """Get status of a specific scanner."""
        scanner = self.scanner_map.get(scanner_type)
        if scanner:
            return await scanner.get_status()
        return {'available': False}

    async def get_all_scanner_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all scanners."""
        status = {}
        for scanner_type, scanner in self.scanner_map.items():
            status[scanner_type] = await scanner.get_status()
        return status
