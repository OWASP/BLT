from workers import WorkerEntrypoint, Response
import json


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # Handle CORS preflight
        if request.method == "OPTIONS":
            return self.handle_cors()
        
        # Only accept POST requests for chat
        if request.method != "POST":
            return Response.json(
                {"error": "Method not allowed. Use POST to send messages."},
                status=405,
                headers=self.get_cors_headers()
            )
        
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
            system_instructions = """You are a helpful assistant for BugHeist (BLT - Bug Logging Tool).
BugHeist is a bug bounty platform where security researchers can report vulnerabilities and earn rewards.

Your role is to:
- Help users understand how to report bugs
- Explain the bug bounty process
- Answer questions about security vulnerabilities
- Guide users on how to earn rewards
- Provide information about responsible disclosure
- Help with technical security questions

Be concise, helpful, and professional in your responses."""
            
            # Call Cloudflare AI
            response = await self.env.AI.run(
                "@cf/meta/llama-3.1-8b-instruct",
                {
                    "messages": [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": user_message}
                    ]
                }
            )
            
            # Extract the response
            assistant_message = response.response if hasattr(response, 'response') else str(response)
            
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
