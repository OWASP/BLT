from fastapi import FastAPI

from app.config import settings
from app.api.routes.health import router as health_router


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered security reviews for GitLab Merge Requests.",
)


app.include_router(
    health_router,
    prefix="/api/v1",
)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.version,
        "status": "running",
    }