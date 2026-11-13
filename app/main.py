from fastapi import FastAPI

from app.config import settings
from app.api.routes.dashboard import router as dashboard_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="School transportation operations and attendance management API.",
)

app.include_router(
    dashboard_router,
    prefix="/api/v1",
)


@app.get("/", tags=["Health"])
def root():
    return {
        "success": True,
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "SchoolRoute AI API is running.",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "database": "full-scale",
    }
