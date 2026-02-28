from workers import WorkerEntrypoint, Response
import json
from pathlib import Path
import logging


class Default(WorkerEntrypoint):
    logger  = logging.getLogger(__name__)
    async def fetch(self, request):
        url = str(request.url)
        
        # Handle CORS preflight for API
        if request.method == "OPTIONS":
            return self.handle_cors()
        
        # API endpoint for chat (POST requests)
        if request.method == "POST":
            return await self.handle_chat(request)
        
        # For GET requests to root, serve the HTML interface
        if request.method == "GET":
            return self.serve_html()
        
        # Default response for unsupported methods
        return Response.json(
            {"error": "Method not allowed"},
            status=405,
            headers=self.get_cors_headers()
        )
    
    async def handle_chat(self, request):
        """Handle chat API requests"""
        try:
            # Parse request body
            body = await request.json()
            user_message = body.get("message", "")
            
            if not user_message:
                return Response.json(
                    {"error": "Message field is required"},
                    status=400,
                    headers=self.get_cors_headers()
                )
            
            # System instructions for BLT chatbot
            system_instructions = """You are a helpful assistant for BLT Byte (BLT - Bug Logging Tool).
BLT Byte is a bug bounty platform where security researchers can report vulnerabilities and earn rewards.

Your role is to:
- Help users understand how to report bugs
- Explain the bug bounty process
- Answer questions about security vulnerabilities
- Guide users on how to earn rewards
- Provide information about responsible disclosure
- Help with technical security questions

Be concise, helpful, and professional in your responses."""
            
            # Call Cloudflare AI
            try:
                ai_response = await self.env.AI.run(
                    "@cf/openai/gpt-oss-120b",
                    {
                        "instructions": system_instructions,
                        "input": user_message,
                    },
                )
                
                self.logger.info(f"AI response type: {type(ai_response)}")
                
                # Extract the response using the output attribute
                response_output = ai_response.output if hasattr(ai_response, 'output') else ai_response
                
                # The output is a list with reasoning and assistant message
                # Find the assistant message (last item with role="assistant")
                assistant_message = "I'm having trouble generating a response."
                
                if isinstance(response_output, list):
                    for item in response_output:
                        if isinstance(item, dict) and item.get('role') == 'assistant':
                            content = item.get('content', [])
                            if content and isinstance(content, list):
                                for content_item in content:
                                    if isinstance(content_item, dict) and content_item.get('type') == 'output_text':
                                        assistant_message = content_item.get('text', '')
                                        break
                
                self.logger.info(f"Successfully extracted AI response: {assistant_message[:100]}...")
                
            except Exception as ai_error:
                self.logger.error(f"AI call error: {str(ai_error)}", exc_info=True)
                assistant_message = "I'm having trouble connecting to the AI service. Please try again."
            
            return Response.json(
                {
                    "success": True,
                    "message": assistant_message,
                    "user_message": user_message
                },
                headers=self.get_cors_headers()
            )
            
        except json.JSONDecodeError:
            return Response.json(
                {"error": "Invalid JSON in request body"},
                status=400,
                headers=self.get_cors_headers()
            )
        except Exception as e:
            self.logger.error(f"Error handling chat request: {str(e)}")
            return Response.json(
                {"error": f"An error occurred: {str(e)}"},
                status=500,
                headers=self.get_cors_headers()
            )
    
    def get_cors_headers(self):
        """Return CORS headers for responses"""
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Content-Type": "application/json"
        }
    
    def handle_cors(self):
        """Handle CORS preflight requests"""
        return Response(
            "",
            status=204,
            headers=self.get_cors_headers()
        )
    
    def serve_html(self):
        """Serve the HTML interface"""
        try:
            # Path(__file__).parent is src/, go up one level to get to project root
            html_file = Path(__file__).parent / 'pages' / "index.html"
            self.logger.info(f"Serving HTML file from path: {html_file}")
            html_content = html_file.read_text()
            return Response(
                html_content,
                status=200,
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "Cache-Control": "public, max-age=300"
                }
            )
        except FileNotFoundError as e:
            self.logger.error(f"HTML file not found at expected path: {e}")
            return Response.json(
                {"error": "HTML file not found"},
                status=404,
                headers=self.get_cors_headers()
            )
