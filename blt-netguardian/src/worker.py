"""
BLT-NetGuardian Cloudflare Python Worker
Serves the frontend (public/) as static assets and handles the backend API.
"""
import json
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import parse_qs
try:
    from workers import Response
except ImportError:
    class Response:  # type: ignore[no-redef]
        """Local fallback used outside the Cloudflare Workers runtime."""

        def __init__(self, body: str = '', status: int = 200,
                     headers: Optional[Dict[str, str]] = None):
            self.body = body
            self.status = status
            self.headers = dict(headers or {})

from models.task import Task, TaskStatus
from models.target import Target
from models.result import ScanResult
from utils.deduplication import TaskDeduplicator
from utils.storage import JobStateStore, TaskQueueStore, TargetRegistryStore, VulnerabilityDatabase
from scanners.coordinator import ScannerCoordinator
from scanners.autonomous_discovery import AutonomousDiscovery
from scanners.contact_notifier import ContactNotifier


class BLTWorker:
    """Main BLT-NetGuardian Worker class - API only."""

    MAX_LIMIT = 100
    DEFAULT_ALLOWED_ORIGIN = 'https://owasp-blt.github.io'
    MUTATING_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
    
    def __init__(self, env):
        """Initialize the worker with Cloudflare environment bindings."""
        self.env = env
        db = getattr(env, 'DB', None)
        self.job_store = JobStateStore(db)
        self.task_queue = TaskQueueStore(db)
        self.vuln_db = VulnerabilityDatabase(db)
        self.target_registry = TargetRegistryStore(db)
        self.deduplicator = TaskDeduplicator()
        self.coordinator = ScannerCoordinator()
        self.discovery = AutonomousDiscovery()
        self.notifier = ContactNotifier()
    
    async def handle_request(self, request):
        """Route incoming requests to appropriate handlers."""
        url = request.url
        path = url.split('?')[0].split('/', 3)[-1] if '/' in url else ''
        method = request.method

        cors_headers = self.get_cors_headers(request)

        # Handle CORS preflight
        if method == 'OPTIONS':
            if not self.is_allowed_origin(request):
                return Response('', status=403, headers=cors_headers)
            return Response('', status=200, headers=cors_headers)

        if not self.is_allowed_origin(request):
            return self.json_response({'error': 'Origin not allowed'}, status=403, headers=cors_headers)

        if self.requires_authentication(path, method):
            authenticated, reason = self.authenticate_request(request)
            if not authenticated:
                if reason == 'misconfigured':
                    return self.json_response({
                        'error': 'API authentication is not configured'
                    }, status=503, headers=cors_headers)
                return self.json_response({'error': 'Unauthorized'}, status=401, headers=cors_headers)

        try:
            # Route to appropriate handler - API routes only
            if path == 'api/discovery/suggest':
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
            return self.internal_error_response('Internal server error', e, headers=cors_headers)
    
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
                registered_at=datetime.now(timezone.utc).isoformat()
            )
            
            await self.target_registry.save_target(target_obj.to_dict())
            
            # Queue scan tasks
            job_id = self.generate_id(f"job-{target_id}-{datetime.now(timezone.utc).isoformat()}")
            
            task = Task(
                task_id=self.generate_id(f"{job_id}-crawler"),
                job_id=job_id,
                target_id=target_id,
                task_type='crawler',
                priority='high' if priority else 'medium',
                status=TaskStatus.QUEUED,
                created_at=datetime.now(timezone.utc).isoformat()
            )
            
            await self.task_queue.save_task(task.to_dict())
            
            job_state = {
                'job_id': job_id,
                'target_id': target_id,
                'status': 'queued',
                'total_tasks': 1,
                'completed_tasks': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
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
            return self.internal_error_response('Failed to process suggestion', e)
    
    async def handle_discovery_status(self, request):
        """Get current status of autonomous discovery system."""
        try:
            # Get statistics
            stats = await self.discovery.get_discovery_stats()

            # Get current scanning target
            current_target = await self.discovery.get_current_scanning_target()

            scanned_today = await self.task_queue.count_completed_tasks_today()
            vulnerability_stats = await self.vuln_db.get_stats()
            vulnerabilities_found = vulnerability_stats.get('total', 0)
            current_target_name = current_target.get('target') if isinstance(current_target, dict) else None

            return self.json_response({
                'status': 'active',
                'current_target': current_target_name,
                'scanned_today': scanned_today,
                'vulnerabilities_found': vulnerabilities_found,
                'stats': stats
            })

        except Exception as e:
            return self.internal_error_response('Failed to get discovery status', e)
    
    async def handle_discovery_recent(self, request):
        """Get recently discovered targets."""
        limit = self.parse_limit_param(request, default=20)
        if limit is None:
            return self.json_response({'error': 'Invalid limit parameter'}, status=400)

        try:
            # Get recent discoveries (in production, query from D1 database)
            discoveries = await self.discovery.discover_targets(limit)

            return self.json_response({
                'success': True,
                'count': len(discoveries),
                'discoveries': discoveries
            })

        except Exception as e:
            return self.internal_error_response('Failed to get recent discoveries', e)
    
    async def handle_task_queue(self, request):
        """Queue new security scanning tasks."""
        if request.method != 'POST':
            return self.json_response({'error': 'Method not allowed'}, status=405)
        
        try:
            data = await request.json()
            target_id = data.get('target_id')
            task_types = data.get('task_types', [])
            priority = data.get('priority', 'medium')
            
            missing_fields = []
            if not target_id:
                missing_fields.append('target_id')
            if not task_types:
                missing_fields.append('task_types')

            if missing_fields:
                return self.json_response({
                    'error': f"Missing required fields: {', '.join(missing_fields)}"
                }, status=400)
            
            # Generate job ID
            job_id = self.generate_id(f"job-{target_id}-{datetime.now(timezone.utc).isoformat()}")
            
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
                    created_at=datetime.now(timezone.utc).isoformat()
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
                'created_at': datetime.now(timezone.utc).isoformat(),
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
            return self.internal_error_response('Failed to queue tasks', e)
    
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
                registered_at=datetime.now(timezone.utc).isoformat()
            )
            
            # Store in target registry
            await self.target_registry.save_target(target_obj.to_dict())
            
            return self.json_response({
                'success': True,
                'target_id': target_id,
                'message': 'Target registered successfully'
            })

        except Exception as e:
            return self.internal_error_response('Failed to register target', e)
    
    async def handle_result_ingestion(self, request):
        """Ingest scan results from agents."""
        if request.method != 'POST':
            return self.json_response({'error': 'Method not allowed'}, status=405)
        
        try:
            data = await request.json()
            task_id = data.get('task_id')
            agent_type = data.get('agent_type')

            if 'results' not in data and any(key in data for key in ('findings', 'vulnerabilities', 'metadata')):
                return self.json_response({
                    'error': 'Legacy payload format is not supported; use results.{findings,vulnerabilities,metadata}'
                }, status=400)

            results = data.get('results', {})

            if (
                not isinstance(task_id, str) or not task_id.strip()
                or not isinstance(agent_type, str) or not agent_type.strip()
            ):
                return self.json_response({
                    'error': 'Missing required fields: task_id, agent_type'
                }, status=400)

            task_id = task_id.strip()
            agent_type = agent_type.strip()

            if results is None:
                results = {}
            if not isinstance(results, dict):
                return self.json_response({'error': 'Invalid results payload'}, status=400)

            findings = results.get('findings', [])
            vulnerabilities = results.get('vulnerabilities', [])
            metadata = results.get('metadata', {})

            if not isinstance(findings, list) or not isinstance(vulnerabilities, list) or not isinstance(metadata, dict):
                return self.json_response({'error': 'Invalid results structure'}, status=400)
            if any(not isinstance(vuln, dict) for vuln in vulnerabilities):
                return self.json_response({'error': 'Invalid vulnerability entry'}, status=400)

            task = await self.task_queue.get_task(task_id)
            if not task:
                return self.json_response({'error': 'Unknown task_id'}, status=400)

            # Create scan result object
            result = ScanResult(
                result_id=self.generate_id(f"result-{task_id}-{agent_type}"),
                task_id=task_id,
                agent_type=agent_type,
                findings=results.get('findings', []),
                vulnerabilities=results.get('vulnerabilities', []),
                metadata=results.get('metadata', {}),
                timestamp=datetime.now(timezone.utc).isoformat()
            )

            # Process and store vulnerabilities
            for index, vuln in enumerate(result.vulnerabilities):
                vuln_id = self.build_vulnerability_id(task_id, vuln, index)
                await self.vuln_db.store_vulnerability(vuln_id, {
                    **vuln,
                    'result_id': result.result_id,
                    'task_id': task_id,
                    'discovered_at': datetime.now(timezone.utc).isoformat()
                })

            # Update task status
            completed_at = datetime.now(timezone.utc).isoformat()
            await self.task_queue.update_task(task_id, {
                'status': TaskStatus.COMPLETED,
                'completed_at': completed_at,
                'result_id': result.result_id
            })

            # Update job progress
            await self.job_store.update_job_progress(task['job_id'])

            # Automatically contact stakeholders if vulnerabilities found
            contact_result = None
            contact_attempted = False
            if result.vulnerabilities:
                # Get target info
                target_id = task.get('target_id')
                target_info = None
                if target_id:
                    target_info = await self.target_registry.get_target(target_id)
                if target_info:
                    target_url = target_info.get('target_url', 'unknown')

                    # Attempt to notify
                    contact_attempted = True
                    try:
                        contact_result = await self.notifier.notify_vulnerability(
                            target=target_url,
                            vulnerabilities=result.vulnerabilities
                        )
                    except Exception as notify_error:
                        self.log_exception('Failed to notify stakeholders', notify_error)

            return self.json_response({
                'success': True,
                'result_id': result.result_id,
                'vulnerabilities_found': len(result.vulnerabilities),
                'triage_ready': False,
                'contact_attempted': contact_attempted,
                'contact_successful': contact_result.get('successful_contacts', 0) if contact_result else 0,
                'message': 'Results ingested successfully'
            })

        except Exception as e:
            return self.internal_error_response('Failed to ingest results', e)
    
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
            return self.internal_error_response('Failed to get job status', e)
    
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
            return self.internal_error_response('Failed to list tasks', e)
    
    async def handle_vulnerabilities(self, request):
        """Get vulnerabilities from the database."""
        limit = self.parse_limit_param(request, default=50)
        if limit is None:
            return self.json_response({'error': 'Invalid limit parameter'}, status=400)
        severity = self.get_query_param(request, 'severity')

        try:
            vulnerabilities = await self.vuln_db.get_vulnerabilities(limit, severity)

            return self.json_response({
                'count': len(vulnerabilities),
                'vulnerabilities': vulnerabilities
            })

        except Exception as e:
            return self.internal_error_response('Failed to get vulnerabilities', e)
    
    def generate_id(self, data: str) -> str:
        """Generate a unique ID using SHA256 hash."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def build_vulnerability_id(self, task_id: str, vulnerability: Dict[str, Any], index: int) -> str:
        """Generate stable IDs that do not collide for repeated vulnerability types."""
        vuln_payload = json.dumps(vulnerability, sort_keys=True, default=str)
        return self.generate_id(f"vuln-{task_id}-{index}-{vuln_payload}")

    def parse_limit_param(self, request, default: int) -> Optional[int]:
        """Parse and bound integer limit parameters."""
        raw_limit = self.get_query_param(request, 'limit', str(default))
        if raw_limit is None:
            return None
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return None
        if limit < 1:
            return None
        return min(limit, self.MAX_LIMIT)

    def get_request_header(self, request, key: str) -> Optional[str]:
        """Safely read a request header from test doubles and worker requests."""
        headers = getattr(request, 'headers', None)
        if headers is None:
            return None
        return headers.get(key)

    def get_cors_headers(self, request) -> Dict[str, str]:
        """Build CORS headers using an explicit origin allowlist."""
        allowed_origins = self.get_allowed_origins()
        origin = self.get_request_header(request, 'Origin')

        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
            'Access-Control-Max-Age': '86400',
            'Vary': 'Origin'
        }

        if origin and origin in allowed_origins:
            headers['Access-Control-Allow-Origin'] = origin
        return headers

    def get_allowed_origins(self) -> List[str]:
        """Resolve allowed frontend origins from env configuration."""
        configured = getattr(self.env, 'CORS_ALLOWED_ORIGINS', None) or getattr(
            self.env, 'CORS_ALLOWED_ORIGIN', None
        )
        if not configured:
            return [self.DEFAULT_ALLOWED_ORIGIN]

        origins = [origin.strip() for origin in str(configured).split(',') if origin.strip()]
        return origins or [self.DEFAULT_ALLOWED_ORIGIN]

    def is_allowed_origin(self, request) -> bool:
        """Allow same-origin/server calls and whitelisted browser origins."""
        origin = self.get_request_header(request, 'Origin')
        if not origin:
            return True
        return origin in self.get_allowed_origins()

    def requires_authentication(self, path: str, method: str) -> bool:
        """Protect API routes; reads can be toggled with AUTHENTICATE_READ_ENDPOINTS."""
        if not path.startswith('api/'):
            return False
        if method in self.MUTATING_METHODS:
            return True
        return self.get_boolean_env('AUTHENTICATE_READ_ENDPOINTS', default=True)

    def get_boolean_env(self, key: str, default: bool = False) -> bool:
        """Read boolean flags from environment variables."""
        value = getattr(self.env, key, None)
        if value is None:
            return default
        return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

    def extract_auth_token(self, request) -> Optional[str]:
        """Read API key from X-API-Key or Authorization Bearer header."""
        api_key = self.get_request_header(request, 'X-API-Key') or self.get_request_header(request, 'x-api-key')
        if api_key:
            return api_key

        authorization = self.get_request_header(request, 'Authorization') or self.get_request_header(request, 'authorization')
        if not authorization:
            return None

        scheme, _, token = authorization.partition(' ')
        if scheme.lower() != 'bearer' or not token:
            return None
        return token.strip()

    def authenticate_request(self, request) -> Tuple[bool, str]:
        """Validate request credentials against API_SECRET."""
        expected_secret = getattr(self.env, 'API_SECRET', None)
        if not expected_secret:
            return False, 'misconfigured'

        provided_secret = self.extract_auth_token(request)
        if not provided_secret:
            return False, 'missing'

        if not hmac.compare_digest(str(provided_secret), str(expected_secret)):
            return False, 'invalid'
        return True, 'ok'

    def log_exception(self, context: str, error: Exception):
        """Log errors server-side without exposing internals to clients."""
        print(f"[ERROR] {context}: {type(error).__name__}: {error}")

    def internal_error_response(self, error_message: str, error: Exception,
                                headers: Optional[Dict[str, str]] = None) -> 'Response':
        """Return a generic 500 response and log exception details server-side."""
        self.log_exception(error_message, error)
        return self.json_response({
              'error': error_message
        }, status=500, headers=headers)
    
    def get_query_param(self, request, key: str, default: Optional[str] = None) -> Optional[str]:
        """Extract query parameter from request."""
        query_string = request.url.split('?')[1] if '?' in request.url else ''
        params = parse_qs(query_string, keep_blank_values=True)
        return params.get(key, [default])[0]
    
    def json_response(self, data: Dict[str, Any], status: int = 200,
                     headers: Optional[Dict[str, str]] = None) -> 'Response':
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
    url = request.url
    path = url.split('?')[0].split('/', 3)[-1] if '/' in url else ''

    # Delegate non-API requests to the static assets binding (serves index.html, etc.)
    assets = getattr(env, 'ASSETS', None)
    if assets is not None and not path.startswith('api/'):
        return await assets.fetch(request)

    worker = BLTWorker(env)
    return await worker.handle_request(request)
