"""
BLT-OSSH Main Entry Point
A magical hat that reads your GitHub profile and suggests blogs or projects you might like
"""

from cloudflare.workers import WorkerEntrypoint, Response
from routers.api_router import APIRouter


class Default(WorkerEntrypoint):
    """Main application entry point"""
    
    def __init__(self, env=None):
        """Initialize the worker with environment"""
        super().__init__(env)
        self.api_router = APIRouter(env)
    
    async def fetch(self, request):
        """
        Main request handler
        
        Args:
            request: The incoming HTTP request
            
        Returns:
            Response object
        """
        url = request.url
        path = url.split('/')[-1] if '/' in url else ''
        
        # API routes
        if path == 'api' or url.endswith('/api'):
            return await self.handle_api_routes(request)
        
        # Health check endpoint
        if path == 'health' or url.endswith('/health'):
            return await self.api_router.handle_health_check(request)
        
        # Serve index page for root route
        return self.serve_html()
    
    async def handle_api_routes(self, request):
        """
        Handle API endpoint routing
        
        Args:
            request: The incoming HTTP request
            
        Returns:
            Response from appropriate API handler
        """
        if request.method == 'POST':
            return await self.api_router.handle_github_analysis(request)
        else:
            return self.api_router.handle_method_not_allowed(['POST'])
    
    def serve_html(self):
        """
        Serve the main index.html page
        
        Returns:
            Response with HTML content
        """
        try:
            # Read the file using the correct path for Workers
            with open('pages/index.html', 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            return Response(
                html_content,
                headers={
                    'Content-Type': 'text/html; charset=utf-8',
                    'Cache-Control': 'public, max-age=300'
                }
            )
        except Exception as e:
            return Response(
                f"Error loading page: {str(e)}",
                status=500,
                headers={'Content-Type': 'text/plain'}
            )