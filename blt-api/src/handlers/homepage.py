"""
Homepage handler that returns HTML with API documentation.
"""

from typing import Any, Dict

try:
    from js import Response, Headers
    _WORKERS_RUNTIME = True
except ImportError:
    _WORKERS_RUNTIME = False
    from utils import Response, Headers


async def handle_homepage(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle homepage requests.
    
    Returns an HTML page listing all API endpoints and their descriptions.
    """
    
    # Get request URL to construct API base URL
    url = str(request.url)
    # Extract base URL (protocol + host)
    if "://" in url:
        protocol_and_host = url.split("://", 1)[1].split("/", 1)[0]
        base_url = f"{url.split('://')[0]}://{protocol_and_host}"
    else:
        base_url = "https://blt-api.workers.dev"
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BLT API - OWASP Bug Logging Tool API</title>
    <meta name="description" content="OWASP BLT API - Full-featured REST API for bug logging and security issue tracking">
    
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
    
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}
    </style>
</head>
<body class="bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center">
                    <img src="/logo.png" alt="BLT-Sammich Logo" class="h-8 w-8 mr-2" />
                    <h1 class="text-xl font-bold text-gray-900">BLT API</h1>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="{base_url}/health" class="text-gray-600 hover:text-red-600 font-medium">
                        <i class="fas fa-heartbeat mr-1"></i> Health
                    </a>
                    <a class="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors" 
                       href="https://github.com/OWASP-BLT/BLT-API" target="_blank" rel="noopener noreferrer">
                        <i class="fab fa-github mr-2"></i> GitHub
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Hero Section -->
        <section class="bg-white rounded-lg shadow p-8 mb-8 text-center">
            <div class="max-w-3xl mx-auto">
                <h1 class="text-4xl font-bold text-gray-900 mb-4"><i class="fas fa-shield-alt text-red-600 text-4xl mr-2"></i> BLT API</h1>
                <p class="text-xl text-gray-600 mb-6">
                    OWASP Bug Logging Tool - Full-Featured REST API running on Cloudflare Workers for global low-latency access
                </p>
                <div class="flex justify-center items-center space-x-4 mb-6">
                    <span class="inline-flex items-center px-4 py-2 bg-green-50 text-green-600 rounded-lg font-medium">
                        <i class="fas fa-check-circle mr-2"></i>
                        API Healthy
                    </span>
                    <span class="inline-flex items-center px-4 py-2 bg-red-50 text-red-600 rounded-lg font-medium">
                        <i class="fas fa-globe mr-2"></i>
                        Edge-Deployed
                    </span>
                </div>
                <div class="flex justify-center space-x-3">
                    <a href="https://blt.owasp.org" 
                       class="inline-flex items-center px-5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                       target="_blank" rel="noopener noreferrer">
                        <i class="fas fa-external-link-alt mr-2"></i>
                        BLT Website
                    </a>
                    <a href="https://github.com/OWASP-BLT/BLT" 
                       class="inline-flex items-center px-5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                       target="_blank" rel="noopener noreferrer">
                        <i class="fab fa-github mr-2"></i>
                        Main Repository
                    </a>
                </div>
            </div>
        </section>

        <!-- Overview Section -->
        <section class="bg-white rounded-lg shadow p-6 mb-8">
            <h2 class="text-3xl font-bold text-gray-900 mb-6 text-center">Features</h2>
            <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-rocket text-xl"></i>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">Edge-Deployed</h3>
                    <p class="text-gray-600 text-sm">Running on Cloudflare's global network for minimal latency</p>
                </div>
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                        <i class="fab fa-python text-xl"></i>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">Python-Powered</h3>
                    <p class="text-gray-600 text-sm">Built with Python for Cloudflare Workers</p>
                </div>
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-lock text-xl"></i>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">Secure</h3>
                    <p class="text-gray-600 text-sm">CORS enabled with authentication support</p>
                </div>
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-chart-line text-xl"></i>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">Comprehensive</h3>
                    <p class="text-gray-600 text-sm">Full API coverage for all BLT resources</p>
                </div>
            </div>
        </section>

        <!-- API Endpoints Section -->
        <section class="bg-white rounded-lg shadow p-6 mb-8">
            <h2 class="text-3xl font-bold text-gray-900 mb-6 text-center">API Endpoints</h2>
            
            <!-- Health & Status -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-heartbeat text-red-600 mr-2"></i>
                    Health & Status
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/</code>
                                <p class="text-gray-600 text-sm mt-1">API homepage (this page)</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start flex-1">
                                <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                                <div class="flex-1">
                                    <code class="text-sm font-mono text-gray-800">/health</code>
                                    <p class="text-gray-600 text-sm mt-1">Health check endpoint (JSON response)</p>
                                </div>
                            </div>
                            <button onclick="testEndpoint('GET', '/health')" 
                                    class="ml-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors flex items-center">
                                <i class="fas fa-play mr-2"></i>Try it
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Issues -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-bug text-red-600 mr-2"></i>
                    Issues
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start flex-1">
                                <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                                <div class="flex-1">
                                    <code class="text-sm font-mono text-gray-800">/issues</code>
                                    <p class="text-gray-600 text-sm mt-1">List all issues (paginated)</p>
                                    <div class="mt-2 bg-gray-50 p-2 rounded text-xs">
                                        <span class="font-semibold text-red-600">Query params:</span> 
                                        <code class="bg-white px-1 py-0.5 rounded">page</code>, 
                                        <code class="bg-white px-1 py-0.5 rounded">per_page</code>, 
                                        <code class="bg-white px-1 py-0.5 rounded">status</code>, 
                                        <code class="bg-white px-1 py-0.5 rounded">domain</code>
                                    </div>
                                </div>
                            </div>
                            <button onclick="testEndpoint('GET', '/issues', {{page: 1, per_page: 10}})" 
                                    class="ml-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors flex items-center">
                                <i class="fas fa-play mr-2"></i>Try it
                            </button>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start flex-1">
                                <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                                <div class="flex-1">
                                    <code class="text-sm font-mono text-gray-800">/issues/{{id}}</code>
                                    <p class="text-gray-600 text-sm mt-1">Get a specific issue by ID</p>
                                </div>
                            </div>
                            <button onclick="testEndpointWithParams('GET', '/issues/{{id}}', 'Enter issue ID:', '1')" 
                                    class="ml-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors flex items-center">
                                <i class="fas fa-play mr-2"></i>Try it
                            </button>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start flex-1">
                                <span class="inline-block px-3 py-1 bg-green-500 text-white text-xs font-bold rounded mr-3">POST</span>
                                <div class="flex-1">
                                    <code class="text-sm font-mono text-gray-800">/issues</code>
                                    <p class="text-gray-600 text-sm mt-1">Create a new issue</p>
                                </div>
                            </div>
                            <button onclick="alert('POST endpoint requires authentication and a valid request body')" 
                                    class="ml-4 px-4 py-2 bg-gray-400 text-white text-sm font-semibold rounded-lg cursor-not-allowed flex items-center">
                                <i class="fas fa-lock mr-2"></i>Auth Required
                            </button>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start flex-1">
                                <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                                <div class="flex-1">
                                    <code class="text-sm font-mono text-gray-800">/issues/search</code>
                                    <p class="text-gray-600 text-sm mt-1">Search issues</p>
                                    <div class="mt-2 bg-gray-50 p-2 rounded text-xs">
                                        <span class="font-semibold text-red-600">Query params:</span> 
                                        <code class="bg-white px-1 py-0.5 rounded">q</code>
                                    </div>
                                </div>
                            </div>
                            <button onclick="testEndpointWithQuery('GET', '/issues/search', 'Enter search query:', 'xss')" 
                                    class="ml-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors flex items-center">
                                <i class="fas fa-play mr-2"></i>Try it
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Users -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-users text-red-600 mr-2"></i>
                    Users
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start flex-1">
                                <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                                <div class="flex-1">
                                    <code class="text-sm font-mono text-gray-800">/users</code>
                                    <p class="text-gray-600 text-sm mt-1">List all users (paginated)</p>
                                    <div class="mt-2 bg-gray-50 p-2 rounded text-xs">
                                        <span class="font-semibold text-red-600">Query params:</span> 
                                        <code class="bg-white px-1 py-0.5 rounded">page</code>, 
                                        <code class="bg-white px-1 py-0.5 rounded">per_page</code>
                                    </div>
                                </div>
                            </div>
                            <button onclick="testEndpoint('GET', '/users', {{page: 1, per_page: 10}})" 
                                    class="ml-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors flex items-center">
                                <i class="fas fa-play mr-2"></i>Try it
                            </button>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/users/{{id}}</code>
                                <p class="text-gray-600 text-sm mt-1">Get a specific user by ID</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/users/{{id}}/profile</code>
                                <p class="text-gray-600 text-sm mt-1">Get detailed user profile</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Domains -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-globe text-red-600 mr-2"></i>
                    Domains
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/domains</code>
                                <p class="text-gray-600 text-sm mt-1">List all domains (paginated)</p>
                                <div class="mt-2 bg-gray-50 p-2 rounded text-xs">
                                    <span class="font-semibold text-red-600">Query params:</span> 
                                    <code class="bg-white px-1 py-0.5 rounded">page</code>, 
                                    <code class="bg-white px-1 py-0.5 rounded">per_page</code>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/domains/{{id}}</code>
                                <p class="text-gray-600 text-sm mt-1">Get a specific domain by ID</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/domains/{{id}}/issues</code>
                                <p class="text-gray-600 text-sm mt-1">Get all issues for a domain</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Organizations -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-building text-red-600 mr-2"></i>
                    Organizations
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/organizations</code>
                                <p class="text-gray-600 text-sm mt-1">List all organizations (paginated)</p>
                                <div class="mt-2 bg-gray-50 p-2 rounded text-xs">
                                    <span class="font-semibold text-red-600">Query params:</span> 
                                    <code class="bg-white px-1 py-0.5 rounded">page</code>, 
                                    <code class="bg-white px-1 py-0.5 rounded">per_page</code>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/organizations/{{id}}</code>
                                <p class="text-gray-600 text-sm mt-1">Get a specific organization by ID</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/organizations/{{id}}/repos</code>
                                <p class="text-gray-600 text-sm mt-1">Get repositories for an organization</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/organizations/{{id}}/projects</code>
                                <p class="text-gray-600 text-sm mt-1">Get projects for an organization</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Projects -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-folder-open text-red-600 mr-2"></i>
                    Projects
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/projects</code>
                                <p class="text-gray-600 text-sm mt-1">List all projects (paginated)</p>
                                <div class="mt-2 bg-gray-50 p-2 rounded text-xs">
                                    <span class="font-semibold text-red-600">Query params:</span> 
                                    <code class="bg-white px-1 py-0.5 rounded">page</code>, 
                                    <code class="bg-white px-1 py-0.5 rounded">per_page</code>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/projects/{{id}}</code>
                                <p class="text-gray-600 text-sm mt-1">Get a specific project by ID</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/projects/{{id}}/contributors</code>
                                <p class="text-gray-600 text-sm mt-1">Get contributors for a project</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Bug Hunts -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-crosshairs text-red-600 mr-2"></i>
                    Bug Hunts
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/hunts</code>
                                <p class="text-gray-600 text-sm mt-1">List all bug hunts</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/hunts/{{id}}</code>
                                <p class="text-gray-600 text-sm mt-1">Get a specific hunt by ID</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/hunts/active</code>
                                <p class="text-gray-600 text-sm mt-1">Get currently active hunts</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/hunts/previous</code>
                                <p class="text-gray-600 text-sm mt-1">Get past hunts</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/hunts/upcoming</code>
                                <p class="text-gray-600 text-sm mt-1">Get upcoming hunts</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Statistics -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-chart-bar text-red-600 mr-2"></i>
                    Statistics
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start flex-1">
                                <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                                <div class="flex-1">
                                    <code class="text-sm font-mono text-gray-800">/stats</code>
                                    <p class="text-gray-600 text-sm mt-1">Get platform statistics</p>
                                </div>
                            </div>
                            <button onclick="testEndpoint('GET', '/stats')" 
                                    class="ml-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors flex items-center">
                                <i class="fas fa-play mr-2"></i>Try it
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Leaderboard -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-trophy text-red-600 mr-2"></i>
                    Leaderboard
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start flex-1">
                                <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                                <div class="flex-1">
                                    <code class="text-sm font-mono text-gray-800">/leaderboard</code>
                                    <p class="text-gray-600 text-sm mt-1">Get global leaderboard</p>
                                </div>
                            </div>
                            <button onclick="testEndpoint('GET', '/leaderboard')" 
                                    class="ml-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors flex items-center">
                                <i class="fas fa-play mr-2"></i>Try it
                            </button>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/leaderboard/monthly</code>
                                <p class="text-gray-600 text-sm mt-1">Get monthly leaderboard</p>
                                <div class="mt-2 bg-gray-50 p-2 rounded text-xs">
                                    <span class="font-semibold text-red-600">Query params:</span> 
                                    <code class="bg-white px-1 py-0.5 rounded">month</code>, 
                                    <code class="bg-white px-1 py-0.5 rounded">year</code>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/leaderboard/organizations</code>
                                <p class="text-gray-600 text-sm mt-1">Get organization leaderboard</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Contributors -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-user-friends text-red-600 mr-2"></i>
                    Contributors
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/contributors</code>
                                <p class="text-gray-600 text-sm mt-1">List all contributors</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/contributors/{{id}}</code>
                                <p class="text-gray-600 text-sm mt-1">Get a specific contributor by ID</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Repositories -->
            <div class="mb-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                    <i class="fas fa-code-branch text-red-600 mr-2"></i>
                    Repositories
                </h3>
                <div class="space-y-3">
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/repos</code>
                                <p class="text-gray-600 text-sm mt-1">List repositories</p>
                            </div>
                        </div>
                    </div>
                    <div class="border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
                        <div class="flex items-start">
                            <span class="inline-block px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded mr-3">GET</span>
                            <div class="flex-1">
                                <code class="text-sm font-mono text-gray-800">/repos/{{id}}</code>
                                <p class="text-gray-600 text-sm mt-1">Get a specific repository by ID</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Response Format -->
        <section class="bg-white rounded-lg shadow p-6 mb-8">
            <h2 class="text-3xl font-bold text-gray-900 mb-6 text-center">Response Format</h2>
            <p class="text-gray-600 text-center mb-6">All API endpoints return JSON responses in a consistent format</p>
            
            <div class="grid md:grid-cols-2 gap-6">
                <div class="border border-gray-200 rounded-lg p-4">
                    <h4 class="font-semibold text-green-600 mb-3 flex items-center">
                        <i class="fas fa-check-circle mr-2"></i>
                        Success Response
                    </h4>
                    <pre class="bg-gray-50 p-3 rounded text-xs overflow-x-auto"><code>{{
  "success": true,
  "data": {{ ... }},
  "pagination": {{
    "page": 1,
    "per_page": 20,
    "count": 10,
    "total": 100
  }}
}}</code></pre>
                </div>
                
                <div class="border border-gray-200 rounded-lg p-4">
                    <h4 class="font-semibold text-red-600 mb-3 flex items-center">
                        <i class="fas fa-exclamation-circle mr-2"></i>
                        Error Response
                    </h4>
                    <pre class="bg-gray-50 p-3 rounded text-xs overflow-x-auto"><code>{{
  "error": true,
  "message": "Error description",
  "status": 400
}}</code></pre>
                </div>
            </div>
        </section>

        <!-- Authentication -->
        <section class="bg-white rounded-lg shadow p-6 mb-8">
            <h2 class="text-3xl font-bold text-gray-900 mb-6 text-center">Authentication</h2>
            <div class="max-w-3xl mx-auto">
                <p class="text-gray-600 text-center mb-4">Some endpoints require authentication. Include your API token in the Authorization header:</p>
                <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                    <pre class="text-sm"><code class="text-gray-800">Authorization: Token YOUR_API_TOKEN</code></pre>
                </div>
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t mt-12">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div class="text-center">
                <p class="text-gray-600 mb-2">BLT API v1.0.0 | Made with ❤️ by the OWASP BLT Community</p>
                <div class="flex justify-center space-x-4 text-sm">
                    <a href="https://github.com/OWASP-BLT/BLT-API" class="text-red-600 hover:underline" target="_blank">
                        <i class="fab fa-github mr-1"></i> Documentation
                    </a>
                    <span class="text-gray-400">•</span>
                    <a href="https://blt.owasp.org" class="text-red-600 hover:underline" target="_blank">
                        <i class="fas fa-external-link-alt mr-1"></i> Website
                    </a>
                    <span class="text-gray-400">•</span>
                    <a href="https://github.com/OWASP-BLT/BLT" class="text-red-600 hover:underline" target="_blank">
                        <i class="fab fa-github mr-1"></i> GitHub
                    </a>
                </div>
            </div>
        </div>
    </footer>

    <!-- API Test Modal -->
    <div id="apiTestModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden overflow-y-auto h-full w-full z-50">
        <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-lg bg-white">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-2xl font-bold text-gray-900">
                    <i class="fas fa-flask text-red-600 mr-2"></i>API Test Console
                </h3>
                <button onclick="closeModal()" class="text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times text-2xl"></i>
                </button>
            </div>
            
            <div class="mb-4">
                <div class="flex items-center space-x-2 mb-2">
                    <span id="modalMethod" class="px-3 py-1 bg-blue-500 text-white text-sm font-bold rounded"></span>
                    <code id="modalEndpoint" class="text-sm font-mono text-gray-800"></code>
                </div>
                <div id="modalLoading" class="hidden">
                    <div class="flex items-center justify-center py-8">
                        <i class="fas fa-spinner fa-spin text-4xl text-red-600"></i>
                        <span class="ml-3 text-gray-600">Loading...</span>
                    </div>
                </div>
            </div>
            
            <div id="modalContent" class="space-y-4">
                <!-- Request section -->
                <div class="border border-gray-200 rounded-lg p-4">
                    <h4 class="font-semibold text-gray-900 mb-2 flex items-center">
                        <i class="fas fa-arrow-up text-blue-600 mr-2"></i>Request
                    </h4>
                    <div class="bg-gray-50 rounded p-3">
                        <div class="mb-2">
                            <span class="text-sm font-semibold text-gray-700">URL:</span>
                            <code id="requestUrl" class="text-sm text-gray-800 ml-2"></code>
                        </div>
                        <div id="requestHeaders" class="text-xs text-gray-600"></div>
                    </div>
                </div>
                
                <!-- Response section -->
                <div class="border border-gray-200 rounded-lg p-4">
                    <h4 class="font-semibold text-gray-900 mb-2 flex items-center">
                        <i class="fas fa-arrow-down text-green-600 mr-2"></i>Response
                        <span id="responseStatus" class="ml-2 px-2 py-1 text-xs rounded"></span>
                        <span id="responseTime" class="ml-2 text-sm text-gray-600"></span>
                    </h4>
                    <div class="bg-gray-50 rounded p-3 overflow-x-auto">
                        <pre id="responseBody" class="text-xs"><code></code></pre>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- JavaScript for API Testing -->
    <script>
        const baseUrl = '{base_url}';
        
        function closeModal() {{
            document.getElementById('apiTestModal').classList.add('hidden');
        }}
        
        function showModal() {{
            document.getElementById('apiTestModal').classList.remove('hidden');
        }}
        
        function testEndpoint(method, endpoint, queryParams = null) {{
            showModal();
            
                    // Update modal header
                    document.getElementById('modalMethod').textContent = method;
                    document.getElementById('modalMethod').className = `px-3 py-1 ${{method === 'GET' ? 'bg-blue-500' : 'bg-green-500'}} text-white text-sm font-bold rounded`;
                    document.getElementById('modalEndpoint').textContent = endpoint;
            
            // Show loading
            document.getElementById('modalLoading').classList.remove('hidden');
            document.getElementById('modalContent').classList.add('hidden');
            
            // Build URL with query params
            let url = baseUrl + endpoint;
            if (queryParams) {{
                const params = new URLSearchParams(queryParams);
                url += '?' + params.toString();
            }}
            
            document.getElementById('requestUrl').textContent = url;
            
            // Make request
            const startTime = performance.now();
            fetch(url)
                .then(response => {{
                    const endTime = performance.now();
                    const duration = Math.round(endTime - startTime);
                    
                    // Hide loading, show content
                    document.getElementById('modalLoading').classList.add('hidden');
                    document.getElementById('modalContent').classList.remove('hidden');
                    
                    // Update status
                    const statusEl = document.getElementById('responseStatus');
                    statusEl.textContent = `${{response.status}} ${{response.statusText}}`;
                    statusEl.className = `ml-2 px-2 py-1 text-xs rounded ${{response.ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}}`;
                    
                    // Update time
                    document.getElementById('responseTime').textContent = `(${{duration}}ms)`;
                    
                    return response.json();
                }})
                .then(data => {{
                    // Display formatted JSON
                    document.getElementById('responseBody').innerHTML = 
                        '<code>' + JSON.stringify(data, null, 2) + '</code>';
                }})
                .catch(error => {{
                    document.getElementById('modalLoading').classList.add('hidden');
                    document.getElementById('modalContent').classList.remove('hidden');
                    
                    const statusEl = document.getElementById('responseStatus');
                    statusEl.textContent = 'Error';
                    statusEl.className = 'ml-2 px-2 py-1 text-xs rounded bg-red-100 text-red-800';
                    
                    document.getElementById('responseBody').innerHTML = 
                        '<code style="color: red;">Error: ' + error.message + '</code>';
                }});
        }}
        
        function testEndpointWithParams(method, endpointTemplate, promptText, defaultValue) {{
            const value = prompt(promptText, defaultValue);
            if (value) {{
                const endpoint = endpointTemplate.replace('{{id}}', value);
                testEndpoint(method, endpoint);
            }}
        }}
        
        function testEndpointWithQuery(method, endpoint, promptText, defaultValue) {{
            const value = prompt(promptText, defaultValue);
            if (value) {{
                testEndpoint(method, endpoint, {{ q: value }});
            }}
        }}
        
        // Close modal when clicking outside
        document.getElementById('apiTestModal').addEventListener('click', function(e) {{
            if (e.target === this) {{
                closeModal();
            }}
        }});
    </script>
</body>
</html>"""
    
    # Create HTML response with proper headers
    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    
    # Convert dict to list of tuples for Headers.new
    js_headers = Headers.new(list(headers.items()))
    
    return Response.new(html_content, status=200, headers=js_headers)
