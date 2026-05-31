from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from brokers import handle_brokers_request
from health import handle_health_check
from responses import CORS_HEADERS, add_default_headers, json_response
from templates import handle_templates_request


CATEGORIES = [
    "People Search",
    "Data Broker",
    "Background Check",
    "Public Records",
    "Social Media",
    "Marketing",
]


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(request.url).path

        if request.method == "OPTIONS":
            return Response("", headers=CORS_HEADERS)

        try:
            if path == "/api/brokers" or path.startswith("/api/brokers/"):
                response = handle_brokers_request(path)
            elif path.startswith("/api/health/"):
                response = await handle_health_check(path)
            elif path.startswith("/api/templates/"):
                response = handle_templates_request(path)
            elif path == "/api/categories":
                response = json_response(CATEGORIES)
            elif path == "/" or path == "/api":
                response = handle_root_request()
            else:
                response = Response("Not Found", status=404)

            return add_default_headers(response)
        except Exception as error:
            print(f"Worker error: {error}")
            return add_default_headers(
                json_response({"error": "Internal server error"}, status=500)
            )


def handle_root_request():
    return json_response(
        {
            "name": "BLT-Vanish Workers API",
            "version": "1.0.0",
            "description": "Stateless edge functions for public broker data",
            "privacy": "NO USER PII IS PROCESSED OR STORED",
            "endpoints": {
                "brokers": "/api/brokers",
                "broker_detail": "/api/brokers/:id",
                "health_check": "/api/health/:id",
                "template": "/api/templates/:id",
                "categories": "/api/categories",
            },
            "documentation": "https://github.com/OWASP-BLT/BLT-Vanish-Web",
        }
    )
