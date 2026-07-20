"""FastAPI application factory — pure FastAPI, no Worker imports.

The Worker entrypoint (worker.py) calls ``asgi.fetch(app, request, env)``.
All routes receive the D1 binding via ``request.scope["env"]``.
"""

from fastapi import FastAPI

from api.routes import router


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(
        title="BLT-Hackerhouse",
        version="0.1.0",
        description="Real-time contributor visualization for OWASP BLT",
    )
    app.include_router(router)
    return app


app = create_app()
