import json

from workers import Response


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def json_response(data, status=200):
    return Response(
        json.dumps(data, indent=2),
        status=status,
        headers={"Content-Type": "application/json"},
    )


def add_default_headers(response):
    for name, value in {**CORS_HEADERS, **SECURITY_HEADERS}.items():
        response.headers[name] = value
    return response
