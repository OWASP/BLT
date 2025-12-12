"""Scanner coordinator that manages all scanning agents."""
from typing import List, Dict, Any
from datetime import datetime

from scanners.web2_crawler import Web2Crawler
from scanners.web3_monitor import Web3Monitor
from scanners.static_analyzer import StaticAnalyzer
from scanners.contract_scanner import ContractScanner
from scanners.volunteer_agent import VolunteerAgentManager


class ScannerCoordinator:
    """Coordinates all security scanning agents."""
    
    def __init__(self, env):
        """Initialize coordinator with all scanner agents."""
        self.env = env
        self.web2_crawler = Web2Crawler()
        self.web3_monitor = Web3Monitor()
        self.static_analyzer = StaticAnalyzer()
        self.contract_scanner = ContractScanner()
        self.volunteer_manager = VolunteerAgentManager()
        
        # Map task types to scanners
        self.scanner_map = {
            'crawler': self.web2_crawler,
            'web3_monitor': self.web3_monitor,
            'static_analysis': self.static_analyzer,
            'contract_audit': self.contract_scanner,
            'vulnerability_scan': self.web2_crawler,  # Reuse web2 crawler
            'penetration_test': self.volunteer_manager,
        }
    
    async def process_job(self, job_id: str, tasks: List[Any]):
        """Process all tasks in a job."""
        for task in tasks:
            await self.process_task(task)
    
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
            # Execute the scan
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
