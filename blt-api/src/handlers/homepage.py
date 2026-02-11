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
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .status {{
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-top: 15px;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }}
        
        .endpoint-group {{
            margin-bottom: 30px;
        }}
        
        .endpoint-group h3 {{
            color: #374151;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .endpoint {{
            background: #f9fafb;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            transition: all 0.3s ease;
        }}
        
        .endpoint:hover {{
            background: #f3f4f6;
            transform: translateX(5px);
        }}
        
        .method {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 3px;
            font-weight: bold;
            font-size: 0.85em;
            margin-right: 10px;
            min-width: 60px;
            text-align: center;
        }}
        
        .method-get {{
            background: #3b82f6;
            color: white;
        }}
        
        .method-post {{
            background: #10b981;
            color: white;
        }}
        
        .path {{
            font-family: 'Courier New', monospace;
            color: #1f2937;
            font-weight: 500;
        }}
        
        .description {{
            color: #6b7280;
            margin-top: 8px;
            font-size: 0.95em;
        }}
        
        .params {{
            margin-top: 10px;
            padding: 10px;
            background: white;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        
        .params strong {{
            color: #667eea;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .info-card {{
            background: #f9fafb;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }}
        
        .info-card h4 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .info-card p {{
            color: #6b7280;
            font-size: 0.95em;
        }}
        
        .links {{
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 20px;
        }}
        
        .link-button {{
            display: inline-block;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s ease;
        }}
        
        .link-button:hover {{
            background: #5568d3;
        }}
        
        .footer {{
            background: #f9fafb;
            padding: 20px;
            text-align: center;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
        
        code {{
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ BLT API</h1>
            <p>OWASP Bug Logging Tool - Full-Featured REST API</p>
            <span class="status">✓ Healthy</span>
            <div class="links">
                <a href="https://github.com/OWASP-BLT/BLT" class="link-button">GitHub</a>
                <a href="https://blt.owasp.org" class="link-button">BLT Website</a>
                <a href="{base_url}/health" class="link-button">Health Check (JSON)</a>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>Overview</h2>
                <p>Welcome to the BLT API! This API provides comprehensive access to the OWASP BLT (Bug Logging Tool) platform, running on Cloudflare Workers for global low-latency access. All endpoints return JSON responses and support CORS.</p>
                
                <div class="info-grid">
                    <div class="info-card">
                        <h4>🚀 Edge-Deployed</h4>
                        <p>Running on Cloudflare's global network for minimal latency</p>
                    </div>
                    <div class="info-card">
                        <h4>🐍 Python-Powered</h4>
                        <p>Built with Python for Cloudflare Workers</p>
                    </div>
                    <div class="info-card">
                        <h4>🔒 Secure</h4>
                        <p>CORS enabled with authentication support</p>
                    </div>
                    <div class="info-card">
                        <h4>📊 Comprehensive</h4>
                        <p>Full API coverage for all BLT resources</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>API Endpoints</h2>
                
                <div class="endpoint-group">
                    <h3>Health & Status</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/</span>
                        <div class="description">API homepage (this page)</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/health</span>
                        <div class="description">Health check endpoint (JSON response)</div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Issues</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/issues</span>
                        <div class="description">List all issues (paginated)</div>
                        <div class="params">
                            <strong>Query params:</strong> <code>page</code>, <code>per_page</code>, <code>status</code> (open/closed), <code>domain</code>
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/issues/{{id}}</span>
                        <div class="description">Get a specific issue by ID</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-post">POST</span>
                        <span class="path">/issues</span>
                        <div class="description">Create a new issue</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/issues/search</span>
                        <div class="description">Search issues</div>
                        <div class="params">
                            <strong>Query params:</strong> <code>q</code> (search query)
                        </div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Users</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/users</span>
                        <div class="description">List all users (paginated)</div>
                        <div class="params">
                            <strong>Query params:</strong> <code>page</code>, <code>per_page</code>
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/users/{{id}}</span>
                        <div class="description">Get a specific user by ID</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/users/{{id}}/profile</span>
                        <div class="description">Get detailed user profile</div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Domains</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/domains</span>
                        <div class="description">List all domains (paginated)</div>
                        <div class="params">
                            <strong>Query params:</strong> <code>page</code>, <code>per_page</code>
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/domains/{{id}}</span>
                        <div class="description">Get a specific domain by ID</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/domains/{{id}}/issues</span>
                        <div class="description">Get all issues for a domain</div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Organizations</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/organizations</span>
                        <div class="description">List all organizations (paginated)</div>
                        <div class="params">
                            <strong>Query params:</strong> <code>page</code>, <code>per_page</code>
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/organizations/{{id}}</span>
                        <div class="description">Get a specific organization by ID</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/organizations/{{id}}/repos</span>
                        <div class="description">Get repositories for an organization</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/organizations/{{id}}/projects</span>
                        <div class="description">Get projects for an organization</div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Projects</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/projects</span>
                        <div class="description">List all projects (paginated)</div>
                        <div class="params">
                            <strong>Query params:</strong> <code>page</code>, <code>per_page</code>
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/projects/{{id}}</span>
                        <div class="description">Get a specific project by ID</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/projects/{{id}}/contributors</span>
                        <div class="description">Get contributors for a project</div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Bug Hunts</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/hunts</span>
                        <div class="description">List all bug hunts</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/hunts/{{id}}</span>
                        <div class="description">Get a specific hunt by ID</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/hunts/active</span>
                        <div class="description">Get currently active hunts</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/hunts/previous</span>
                        <div class="description">Get past hunts</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/hunts/upcoming</span>
                        <div class="description">Get upcoming hunts</div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Statistics</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/stats</span>
                        <div class="description">Get platform statistics</div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Leaderboard</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/leaderboard</span>
                        <div class="description">Get global leaderboard</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/leaderboard/monthly</span>
                        <div class="description">Get monthly leaderboard</div>
                        <div class="params">
                            <strong>Query params:</strong> <code>month</code> (1-12), <code>year</code> (e.g., 2024)
                        </div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/leaderboard/organizations</span>
                        <div class="description">Get organization leaderboard</div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Contributors</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/contributors</span>
                        <div class="description">List all contributors</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/contributors/{{id}}</span>
                        <div class="description">Get a specific contributor by ID</div>
                    </div>
                </div>
                
                <div class="endpoint-group">
                    <h3>Repositories</h3>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/repos</span>
                        <div class="description">List repositories</div>
                    </div>
                    <div class="endpoint">
                        <span class="method method-get">GET</span>
                        <span class="path">/repos/{{id}}</span>
                        <div class="description">Get a specific repository by ID</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>Response Format</h2>
                <p>All API endpoints return JSON responses in a consistent format:</p>
                
                <div class="info-card" style="margin-top: 15px;">
                    <h4>Success Response</h4>
                    <pre><code>{{
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
                
                <div class="info-card" style="margin-top: 15px;">
                    <h4>Error Response</h4>
                    <pre><code>{{
  "error": true,
  "message": "Error description",
  "status": 400
}}</code></pre>
                </div>
            </div>
            
            <div class="section">
                <h2>Authentication</h2>
                <p>Some endpoints require authentication. Include your API token in the Authorization header:</p>
                <div class="info-card" style="margin-top: 15px;">
                    <pre><code>Authorization: Token YOUR_API_TOKEN</code></pre>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>BLT API v1.0.0 | Made with ❤️ by the OWASP BLT Community</p>
            <p style="margin-top: 10px;">
                <a href="https://github.com/OWASP-BLT/BLT-API" style="color: #667eea; text-decoration: none;">Documentation</a> •
                <a href="https://blt.owasp.org" style="color: #667eea; text-decoration: none;">Website</a> •
                <a href="https://github.com/OWASP-BLT/BLT" style="color: #667eea; text-decoration: none;">GitHub</a>
            </p>
        </div>
    </div>
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
