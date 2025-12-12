"""
BLT-NetGuardian Cloudflare Python Worker
Main entry point for the security pipeline worker.
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import parse_qs

from models.task import Task, TaskStatus, TaskType
from models.target import Target, TargetType
from models.result import ScanResult, VulnerabilityLevel
from utils.deduplication import TaskDeduplicator
from utils.storage import JobStateStore, VulnerabilityDatabase
from scanners.coordinator import ScannerCoordinator


class BLTWorker:
    """Main BLT-NetGuardian Worker class."""
    
    def __init__(self, env):
        """Initialize the worker with Cloudflare environment bindings."""
        self.env = env
        self.job_store = JobStateStore(env.JOB_STATE)
        self.task_queue = env.TASK_QUEUE
        self.vuln_db = VulnerabilityDatabase(env.VULN_DB)
        self.target_registry = env.TARGET_REGISTRY
        self.deduplicator = TaskDeduplicator()
        self.coordinator = ScannerCoordinator(env)
    
    async def handle_request(self, request):
        """Route incoming requests to appropriate handlers."""
        url = request.url
        path = url.split('?')[0].split('/', 3)[-1] if '/' in url else ''
        method = request.method
        
        # CORS headers for all responses
        cors_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        }
        
        # Handle CORS preflight
        if method == 'OPTIONS':
            return Response('', headers=cors_headers)
        
        try:
            # Route to appropriate handler
            if path == '' or path == '/':
                response = await self.handle_home(request)
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
            elif path == 'dashboard':
                response = await self.handle_dashboard(request)
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
    
    async def handle_home(self, request):
        """Serve the main web interface."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BLT-NetGuardian Security Pipeline</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        .content {
            padding: 40px;
        }
        .section {
            margin-bottom: 40px;
        }
        .section h2 {
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
        }
        input[type="text"], input[type="url"], select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus, input[type="url"]:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        .message {
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            display: none;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .stat-card h3 {
            color: #667eea;
            font-size: 2em;
            margin-bottom: 5px;
        }
        .stat-card p {
            color: #666;
            font-size: 0.9em;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .feature {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .feature h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .feature p {
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛡️ BLT-NetGuardian</h1>
            <p>Comprehensive Security Pipeline & Vulnerability Scanner</p>
        </header>
        
        <div class="content">
            <div class="section">
                <h2>Submit Scan Target</h2>
                <form id="scanForm">
                    <div class="form-group">
                        <label for="targetType">Target Type:</label>
                        <select id="targetType" name="targetType" required>
                            <option value="web2">Web2 (Website/Web App)</option>
                            <option value="web3">Web3 (Smart Contract)</option>
                            <option value="api">API Endpoint</option>
                            <option value="repo">Code Repository</option>
                            <option value="contract">Smart Contract</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="target">Target URL/Address:</label>
                        <input type="text" id="target" name="target" 
                               placeholder="e.g., https://example.com or 0x123..." required>
                    </div>
                    
                    <div class="form-group">
                        <label for="scanTypes">Scan Types:</label>
                        <select id="scanTypes" name="scanTypes" multiple size="5">
                            <option value="crawler" selected>Web Crawler</option>
                            <option value="static_analysis">Static Analysis</option>
                            <option value="contract_audit">Contract Audit</option>
                            <option value="vulnerability_scan">Vulnerability Scan</option>
                            <option value="penetration_test">Penetration Test</option>
                        </select>
                        <small style="color: #666;">Hold Ctrl/Cmd to select multiple</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="notes">Additional Notes (Optional):</label>
                        <textarea id="notes" name="notes" 
                                  placeholder="Any specific areas to focus on or context..."></textarea>
                    </div>
                    
                    <button type="submit">🚀 Start Security Scan</button>
                </form>
                
                <div id="message" class="message"></div>
            </div>
            
            <div class="section">
                <h2>Security Pipeline Features</h2>
                <div class="features">
                    <div class="feature">
                        <h3>🕷️ Web2 Crawlers</h3>
                        <p>Automated crawling and vulnerability detection for web applications</p>
                    </div>
                    <div class="feature">
                        <h3>⛓️ Web3 Monitors</h3>
                        <p>Blockchain and smart contract security monitoring</p>
                    </div>
                    <div class="feature">
                        <h3>🔍 Static Analysis</h3>
                        <p>Code analysis for security vulnerabilities and best practices</p>
                    </div>
                    <div class="feature">
                        <h3>📜 Contract Scanners</h3>
                        <p>Comprehensive smart contract auditing and analysis</p>
                    </div>
                    <div class="feature">
                        <h3>👥 Volunteer Agents</h3>
                        <p>Community-driven security testing and validation</p>
                    </div>
                    <div class="feature">
                        <h3>🤖 LLM Triage</h3>
                        <p>AI-powered vulnerability classification and prioritization</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>Quick Actions</h2>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button onclick="window.location.href='/dashboard'">📊 View Dashboard</button>
                    <button onclick="checkStatus()">🔄 Check Job Status</button>
                    <button onclick="viewVulnerabilities()">🐛 View Vulnerabilities</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('scanForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const messageDiv = document.getElementById('message');
            messageDiv.style.display = 'none';
            
            const formData = {
                target_type: document.getElementById('targetType').value,
                target: document.getElementById('target').value,
                scan_types: Array.from(document.getElementById('scanTypes').selectedOptions)
                    .map(opt => opt.value),
                notes: document.getElementById('notes').value,
                priority: 'medium'
            };
            
            try {
                // First register the target
                const registerResponse = await fetch('/api/targets/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                if (!registerResponse.ok) {
                    throw new Error('Failed to register target');
                }
                
                const registerData = await registerResponse.json();
                
                // Then queue the tasks
                const queueResponse = await fetch('/api/tasks/queue', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        target_id: registerData.target_id,
                        task_types: formData.scan_types,
                        priority: formData.priority
                    })
                });
                
                if (!queueResponse.ok) {
                    throw new Error('Failed to queue tasks');
                }
                
                const queueData = await queueResponse.json();
                
                messageDiv.className = 'message success';
                messageDiv.textContent = `✅ Success! Job ID: ${queueData.job_id}. ${queueData.tasks_queued} tasks queued for scanning.`;
                messageDiv.style.display = 'block';
                
                // Reset form
                document.getElementById('scanForm').reset();
                
            } catch (error) {
                messageDiv.className = 'message error';
                messageDiv.textContent = `❌ Error: ${error.message}`;
                messageDiv.style.display = 'block';
            }
        });
        
        async function checkStatus() {
            const jobId = prompt('Enter Job ID:');
            if (!jobId) return;
            
            try {
                const response = await fetch(`/api/jobs/status?job_id=${jobId}`);
                const data = await response.json();
                
                alert(`Job Status: ${data.status}\\nCompleted: ${data.completed}/${data.total} tasks\\nProgress: ${data.progress}%`);
            } catch (error) {
                alert('Error checking status: ' + error.message);
            }
        }
        
        function viewVulnerabilities() {
            window.location.href = '/api/vulnerabilities';
        }
    </script>
</body>
</html>
        """
        return Response(html, headers={'Content-Type': 'text/html'})
    
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
                    await self.task_queue.put(
                        task.task_id,
                        json.dumps(task.to_dict()),
                        expiration_ttl=86400  # 24 hours
                    )
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
            await self.target_registry.put(
                target_id,
                json.dumps(target_obj.to_dict())
            )
            
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
            task_data = await self.task_queue.get(task_id)
            if task_data:
                task = json.loads(task_data.value)
                task['status'] = TaskStatus.COMPLETED
                task['completed_at'] = datetime.utcnow().isoformat()
                task['result_id'] = result.result_id
                await self.task_queue.put(task_id, json.dumps(task))
                
                # Update job progress
                job_id = task['job_id']
                await self.job_store.update_job_progress(job_id)
            
            # Prepare data for LLM triage
            triage_data = self.prepare_for_llm_triage(result)
            
            return self.json_response({
                'success': True,
                'result_id': result.result_id,
                'vulnerabilities_found': len(result.vulnerabilities),
                'triage_ready': True,
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
                task_data = await self.task_queue.get(task_id)
                if task_data:
                    tasks.append(json.loads(task_data.value))
            
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
    
    async def handle_dashboard(self, request):
        """Serve the monitoring dashboard."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BLT-NetGuardian Dashboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f7fa;
            margin: 0;
            padding: 20px;
        }
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            color: #667eea;
            font-size: 2.5em;
            margin: 0 0 10px 0;
        }
        .stat-card p {
            color: #666;
            margin: 0;
        }
        .table-container {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        .status {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .status.queued { background: #fff3cd; color: #856404; }
        .status.running { background: #cfe2ff; color: #084298; }
        .status.completed { background: #d1e7dd; color: #0f5132; }
        .status.failed { background: #f8d7da; color: #842029; }
    </style>
</head>
<body>
    <div class="dashboard">
        <h1>📊 BLT-NetGuardian Dashboard</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3 id="totalJobs">0</h3>
                <p>Total Jobs</p>
            </div>
            <div class="stat-card">
                <h3 id="activeJobs">0</h3>
                <p>Active Jobs</p>
            </div>
            <div class="stat-card">
                <h3 id="totalVulnerabilities">0</h3>
                <p>Vulnerabilities Found</p>
            </div>
            <div class="stat-card">
                <h3 id="criticalVulns">0</h3>
                <p>Critical Issues</p>
            </div>
        </div>
        
        <div class="table-container">
            <h2>Recent Jobs</h2>
            <table id="jobsTable">
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Target</th>
                        <th>Status</th>
                        <th>Progress</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td colspan="5" style="text-align: center; color: #999;">
                            Loading jobs...
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // In a real implementation, this would fetch from actual API endpoints
        // For now, showing placeholder data
        document.getElementById('totalJobs').textContent = '42';
        document.getElementById('activeJobs').textContent = '7';
        document.getElementById('totalVulnerabilities').textContent = '128';
        document.getElementById('criticalVulns').textContent = '3';
    </script>
</body>
</html>
        """
        return Response(html, headers={'Content-Type': 'text/html'})
    
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


# Mock Response class for Cloudflare Workers
class Response:
    """Simple Response class compatible with Cloudflare Workers."""
    
    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}


# Main worker entry point
async def on_fetch(request, env, ctx):
    """Cloudflare Workers fetch handler."""
    worker = BLTWorker(env)
    return await worker.handle_request(request)
