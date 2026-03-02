"""
BLT-NetGuardian Cloudflare Python Worker
Backend API for the security pipeline - Frontend hosted on GitHub Pages
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import parse_qs
from workers import Response
from models.task import Task, TaskStatus, TaskType
from models.target import Target, TargetType
from models.result import ScanResult, VulnerabilityLevel
from utils.deduplication import TaskDeduplicator
from utils.storage import JobStateStore, TaskQueueStore, TargetRegistryStore, VulnerabilityDatabase
from scanners.coordinator import ScannerCoordinator
from scanners.autonomous_discovery import AutonomousDiscovery
from scanners.contact_notifier import ContactNotifier


class BLTWorker:
    """Main BLT-NetGuardian Worker class - API only."""
    
    def __init__(self, env):
        """Initialize the worker with Cloudflare environment bindings."""
        self.env = env
        db = getattr(env, 'DB', None)
        self.job_store = JobStateStore(db)
        self.task_queue = TaskQueueStore(db)
        self.vuln_db = VulnerabilityDatabase(db)
        self.target_registry = TargetRegistryStore(db)
        self.deduplicator = TaskDeduplicator()
        self.coordinator = ScannerCoordinator(env)
        self.discovery = AutonomousDiscovery()
        self.notifier = ContactNotifier()
    
    async def handle_request(self, request):
        """Route incoming requests to appropriate handlers."""
        url = request.url
        path = url.split('?')[0].split('/', 3)[-1] if '/' in url else ''
        method = request.method
        
        # CORS headers for all responses
        # TODO: Restrict to specific domain in production for security
        # For production, use: 'Access-Control-Allow-Origin': 'https://owasp-blt.github.io'
        cors_headers = {
            'Access-Control-Allow-Origin': '*',  # Allow all origins for development
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        }
        
        # Handle CORS preflight
        if method == 'OPTIONS':
            return Response('', headers=cors_headers)
        
        try:
            # Route to appropriate handler - API only, no HTML
            if path == '' or path == '/':
                response = self.json_response({
                    'name': 'BLT-NetGuardian API',
                    'version': '1.0.0',
                    'status': 'operational',
                    'message': 'Backend API for BLT-NetGuardian security pipeline',
                    'frontend': 'https://owasp-blt.github.io/BLT-NetGuardian/',
                    'endpoints': {
                        'queue_tasks': '/api/tasks/queue',
                        'register_target': '/api/targets/register',
                        'ingest_results': '/api/results/ingest',
                        'job_status': '/api/jobs/status',
                        'list_tasks': '/api/tasks/list',
                        'vulnerabilities': '/api/vulnerabilities',
                        'discovery_suggest': '/api/discovery/suggest',
                        'discovery_status': '/api/discovery/status',
                        'discovery_recent': '/api/discovery/recent'
                    }
                })
            elif path == 'api/discovery/suggest':
                response = await self.handle_discovery_suggest(request)
            elif path == 'api/discovery/status':
                response = await self.handle_discovery_status(request)
            elif path == 'api/discovery/recent':
                response = await self.handle_discovery_recent(request)
            elif path == 'api/tasks/queue':
                response = await self.handle_task_queue(request)
            elif path == 'api/targets/register':
                response = await self.handle_target_registration(request)
            elif path == 'api/results/ingest':
                response = await self.handle_result_ingestion(request)
            elif path == 'api/jobs/status':
                response = await self.handle_job_status(request)
            elif path == 'api/tasks/list':
                response = await self.handle_task_list(request)
            elif path == 'api/vulnerabilities':
                response = await self.handle_vulnerabilities(request)
            else:
                response = self.json_response({'error': 'Not found'}, status=404)
            
            # Add CORS headers to response
            for key, value in cors_headers.items():
                response.headers[key] = value
            
            return response
            
        except Exception as e:
            return self.json_response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=500, headers=cors_headers)
    
    async def handle_discovery_suggest(self, request):
        """Handle user-suggested targets for autonomous scanning."""
        if request.method != 'POST':
            return self.json_response({'error': 'Method not allowed'}, status=405)
        
        try:
            data = await request.json()
            suggestion = data.get('suggestion')
            priority = data.get('priority', False)
            
            if not suggestion:
                return self.json_response({
                    'error': 'Missing required field: suggestion'
                }, status=400)
            
            # Process the suggestion through autonomous discovery
            discovery_record = await self.discovery.process_user_suggestion(
                suggestion, priority
            )
            
            # Automatically queue for scanning
            target_type = discovery_record['type']
            
            # Register the target
            target_id = discovery_record['discovery_id']
            target_obj = Target(
                target_id=target_id,
                target_type=target_type,
                target_url=suggestion,
                scan_types=['crawler', 'vulnerability_scan'],
                notes='User suggested target',
                registered_at=datetime.utcnow().isoformat()
            )
            
            await self.target_registry.save_target(target_obj.to_dict())
            
            # Queue scan tasks
            job_id = self.generate_id(f"job-{target_id}-{datetime.utcnow().isoformat()}")
            
            task = Task(
                task_id=self.generate_id(f"{job_id}-crawler"),
                job_id=job_id,
                target_id=target_id,
                task_type='crawler',
                priority='high' if priority else 'medium',
                status=TaskStatus.QUEUED,
                created_at=datetime.utcnow().isoformat()
            )
            
            await self.task_queue.save_task(task.to_dict())
            
            job_state = {
                'job_id': job_id,
                'target_id': target_id,
                'status': 'queued',
                'total_tasks': 1,
                'completed_tasks': 0,
                'created_at': datetime.utcnow().isoformat(),
                'task_ids': [task.task_id],
                'source': 'user_suggestion'
            }
            
            await self.job_store.save_job(job_id, job_state)
            
            return self.json_response({
                'success': True,
                'discovery_id': discovery_record['discovery_id'],
                'job_id': job_id,
                'message': f'Target "{suggestion}" queued for scanning'
            })
            
        except Exception as e:
            return self.json_response({
                'error': 'Failed to process suggestion',
                'message': str(e)
            }, status=500)
    
    async def handle_discovery_status(self, request):
        """Get current status of autonomous discovery system."""
        try:
            # Get statistics
            stats = await self.discovery.get_discovery_stats()
            
            # Get current scanning target
            current_target = await self.discovery.get_current_scanning_target()
            
            # TODO: Replace with actual data from D1 database in production
            # For demo/development, using placeholder values
            scanned_today = 1247
            vulnerabilities_found = 23
            
            return self.json_response({
                'status': 'active',
                'current_target': current_target['target'],
                'scanned_today': scanned_today,
                'vulnerabilities_found': vulnerabilities_found,
                'stats': stats
            })
            
        except Exception as e:
            return self.json_response({
                'error': 'Failed to get discovery status',
                'message': str(e)
            }, status=500)
    
    async def handle_discovery_recent(self, request):
        """Get recently discovered targets."""
        limit = int(self.get_query_param(request, 'limit', '20'))
        
        try:
            # Get recent discoveries (in production, query from D1 database)
            discoveries = await self.discovery.discover_targets(limit)
            
            return self.json_response({
                'success': True,
                'count': len(discoveries),
                'discoveries': discoveries
            })
            
        except Exception as e:
            return self.json_response({
                'error': 'Failed to get recent discoveries',
                'message': str(e)
            }, status=500)
    
    async def handle_task_queue(self, request):
        """Queue new security scanning tasks."""
        if request.method != 'POST':
            return self.json_response({'error': 'Method not allowed'}, status=405)
        
        try:
            data = await request.json()
            target_id = data.get('target_id')
            task_types = data.get('task_types', [])
            priority = data.get('priority', 'medium')
            
            if not target_id or not task_types:
                return self.json_response({
                    'error': 'Missing required fields: target_id, task_types'
                }, status=400)
            
            # Generate job ID
            job_id = self.generate_id(f"job-{target_id}-{datetime.utcnow().isoformat()}")
            
            # Create tasks and check for duplicates
            tasks = []
            deduplicated_count = 0
            
            for task_type in task_types:
                task = Task(
                    task_id=self.generate_id(f"{job_id}-{task_type}"),
                    job_id=job_id,
                    target_id=target_id,
                    task_type=task_type,
                    priority=priority,
                    status=TaskStatus.QUEUED,
                    created_at=datetime.utcnow().isoformat()
                )
                
                # Check for duplicate
                if not await self.deduplicator.is_duplicate(task, self.task_queue):
                    tasks.append(task)
                    # Store in task queue
                    await self.task_queue.save_task(task.to_dict())
                else:
                    deduplicated_count += 1
            
            # Store job state
            job_state = {
                'job_id': job_id,
                'target_id': target_id,
                'status': 'queued',
                'total_tasks': len(tasks),
                'completed_tasks': 0,
                'created_at': datetime.utcnow().isoformat(),
                'task_ids': [t.task_id for t in tasks]
            }
            
            await self.job_store.save_job(job_id, job_state)
            
            # Notify coordinator to start processing
            await self.coordinator.process_job(job_id, tasks)
            
            return self.json_response({
                'success': True,
                'job_id': job_id,
                'tasks_queued': len(tasks),
                'tasks_deduplicated': deduplicated_count,
                'message': f'Successfully queued {len(tasks)} tasks for processing'
            })
            
        except Exception as e:
            return self.json_response({
                'error': 'Failed to queue tasks',
                'message': str(e)
            }, status=500)
    
    async def handle_target_registration(self, request):
        """Register a new scan target."""
        if request.method != 'POST':
            return self.json_response({'error': 'Method not allowed'}, status=405)
        
        try:
            data = await request.json()
            target_type = data.get('target_type')
            target = data.get('target')
            
            if not target_type or not target:
                return self.json_response({
                    'error': 'Missing required fields: target_type, target'
                }, status=400)
            
            # Generate target ID
            target_id = self.generate_id(f"{target_type}-{target}")
            
            # Create target object
            target_obj = Target(
                target_id=target_id,
                target_type=target_type,
                target_url=target,
                scan_types=data.get('scan_types', []),
                notes=data.get('notes', ''),
                registered_at=datetime.utcnow().isoformat()
            )
            
            # Store in target registry
            await self.target_registry.save_target(target_obj.to_dict())
            
            return self.json_response({
                'success': True,
                'target_id': target_id,
                'message': 'Target registered successfully'
            })
            
        except Exception as e:
            return self.json_response({
                'error': 'Failed to register target',
                'message': str(e)
            }, status=500)
    
    async def handle_result_ingestion(self, request):
        """Ingest scan results from agents."""
        if request.method != 'POST':
            return self.json_response({'error': 'Method not allowed'}, status=405)
        
        try:
            data = await request.json()
            task_id = data.get('task_id')
            agent_type = data.get('agent_type')
            results = data.get('results', {})
            
            if not task_id or not agent_type:
                return self.json_response({
                    'error': 'Missing required fields: task_id, agent_type'
                }, status=400)
            
            # Create scan result object
            result = ScanResult(
                result_id=self.generate_id(f"result-{task_id}-{agent_type}"),
                task_id=task_id,
                agent_type=agent_type,
                findings=results.get('findings', []),
                vulnerabilities=results.get('vulnerabilities', []),
                metadata=results.get('metadata', {}),
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Process and store vulnerabilities
            for vuln in result.vulnerabilities:
                vuln_id = self.generate_id(f"vuln-{task_id}-{vuln.get('type')}")
                await self.vuln_db.store_vulnerability(vuln_id, {
                    **vuln,
                    'result_id': result.result_id,
                    'task_id': task_id,
                    'discovered_at': datetime.utcnow().isoformat()
                })
            
            # Update task status
            task = await self.task_queue.get_task(task_id)
            if task:
                await self.task_queue.update_task(task_id, {
                    'status': TaskStatus.COMPLETED,
                    'completed_at': datetime.utcnow().isoformat(),
                    'result_id': result.result_id
                })
                
                # Update job progress
                job_id = task['job_id']
                await self.job_store.update_job_progress(job_id)
            
            # Prepare data for LLM triage
            triage_data = self.prepare_for_llm_triage(result)
            
            # Automatically contact stakeholders if vulnerabilities found
            contact_result = None
            if result.vulnerabilities:
                # Get target info
                target_info = await self.target_registry.get_target(
                    task.get('target_id') if task else None
                )
                if target_info:
                    target_url = target_info.get('target_url', 'unknown')
                    
                    # Attempt to notify
                    contact_result = await self.notifier.notify_vulnerability(
                        target=target_url,
                        vulnerabilities=result.vulnerabilities
                    )
            
            return self.json_response({
                'success': True,
                'result_id': result.result_id,
                'vulnerabilities_found': len(result.vulnerabilities),
                'triage_ready': True,
                'contact_attempted': contact_result is not None,
                'contact_successful': contact_result.get('successful_contacts', 0) if contact_result else 0,
                'message': 'Results ingested successfully'
            })
            
        except Exception as e:
            return self.json_response({
                'error': 'Failed to ingest results',
                'message': str(e)
            }, status=500)
    
    async def handle_job_status(self, request):
        """Get status of a job."""
        job_id = self.get_query_param(request, 'job_id')
        
        if not job_id:
            return self.json_response({'error': 'Missing job_id parameter'}, status=400)
        
        try:
            job_state = await self.job_store.get_job(job_id)
            
            if not job_state:
                return self.json_response({'error': 'Job not found'}, status=404)
            
            # Calculate progress
            total = job_state.get('total_tasks', 0)
            completed = job_state.get('completed_tasks', 0)
            progress = int((completed / total * 100)) if total > 0 else 0
            
            return self.json_response({
                'job_id': job_id,
                'status': job_state.get('status'),
                'total': total,
                'completed': completed,
                'progress': progress,
                'created_at': job_state.get('created_at'),
                'updated_at': job_state.get('updated_at')
            })
            
        except Exception as e:
            return self.json_response({
                'error': 'Failed to get job status',
                'message': str(e)
            }, status=500)
    
    async def handle_task_list(self, request):
        """List all tasks for a job."""
        job_id = self.get_query_param(request, 'job_id')
        
        if not job_id:
            return self.json_response({'error': 'Missing job_id parameter'}, status=400)
        
        try:
            job_state = await self.job_store.get_job(job_id)
            
            if not job_state:
                return self.json_response({'error': 'Job not found'}, status=404)
            
            # Get all tasks for this job
            task_ids = job_state.get('task_ids', [])
            tasks = []
            
            for task_id in task_ids:
                task = await self.task_queue.get_task(task_id)
                if task:
                    tasks.append(task)
            
            return self.json_response({
                'job_id': job_id,
                'tasks': tasks
            })
            
        except Exception as e:
            return self.json_response({
                'error': 'Failed to list tasks',
                'message': str(e)
            }, status=500)
    
    async def handle_vulnerabilities(self, request):
        """Get vulnerabilities from the database."""
        limit = int(self.get_query_param(request, 'limit', '50'))
        severity = self.get_query_param(request, 'severity')
        
        try:
            vulnerabilities = await self.vuln_db.get_vulnerabilities(limit, severity)
            
            return self.json_response({
                'count': len(vulnerabilities),
                'vulnerabilities': vulnerabilities
            })
            
        except Exception as e:
            return self.json_response({
                'error': 'Failed to get vulnerabilities',
                'message': str(e)
            }, status=500)
    
    def prepare_for_llm_triage(self, result: ScanResult) -> Dict[str, Any]:
        """Prepare scan results for LLM triage engine."""
        return {
            'result_id': result.result_id,
            'task_id': result.task_id,
            'agent_type': result.agent_type,
            'summary': {
                'total_findings': len(result.findings),
                'total_vulnerabilities': len(result.vulnerabilities),
                'critical_count': len([v for v in result.vulnerabilities 
                                      if v.get('severity') == 'critical']),
                'high_count': len([v for v in result.vulnerabilities 
                                  if v.get('severity') == 'high']),
            },
            'vulnerabilities': result.vulnerabilities,
            'findings': result.findings,
            'metadata': result.metadata,
            'timestamp': result.timestamp
        }
    
    def generate_id(self, data: str) -> str:
        """Generate a unique ID using SHA256 hash."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def get_query_param(self, request, key: str, default: str = None) -> Optional[str]:
        """Extract query parameter from request."""
        query_string = request.url.split('?')[1] if '?' in request.url else ''
        params = parse_qs(query_string)
        return params.get(key, [default])[0]
    
    def json_response(self, data: Dict[str, Any], status: int = 200, 
                     headers: Dict[str, str] = None) -> 'Response':
        """Create a JSON response."""
        response_headers = {'Content-Type': 'application/json'}
        if headers:
            response_headers.update(headers)
        
        return Response(
            json.dumps(data),
            status=status,
            headers=response_headers
        )


# Main worker entry point
async def on_fetch(request, env, ctx):
    """Cloudflare Workers fetch handler."""
    worker = BLTWorker(env)
    return await worker.handle_request(request)
