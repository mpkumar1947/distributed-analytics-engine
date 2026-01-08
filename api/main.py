from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

# Local Imports
from .celery_app import app as celery_application
from .utils.limiter import limiter, _rate_limit_exceeded_handler
from .routers import (
    search,
    grades,
    users,
    feedback,
    admin_users,
    admin_broadcast,
    professors
)

# Application Metadata
app = FastAPI(
    title="IITK Grade Explorer API",
    description="API backend for fetching IITK course grade distributions.",
    version="0.1.0",
)

# Rate Limiter Setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register Routers
app.include_router(search.router)
app.include_router(grades.router)
app.include_router(professors.router)
app.include_router(users.router)
app.include_router(feedback.router)
app.include_router(admin_users.router)
app.include_router(admin_broadcast.router)

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint to verify API status."""
    return {"status": "ok"}