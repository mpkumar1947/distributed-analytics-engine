from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

# Local Imports
from .utils.limiter import limiter, _rate_limit_exceeded_handler
from .routers import (
    search,
    grades,
    users,
    feedback,
    admin_users,
    professors,
    admin_dashboard
)

# Application Metadata
app = FastAPI(
    title="IITK Grade Explorer API",
    description="API backend for fetching IITK course grade distributions.",
    version="2.0.0",
)

# Rate Limiter Setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register Routers
# Note: The bot now talks directly to the database (api_client.py → crud.py).
# These routers are kept for potential future web dashboard / public API use.
app.include_router(search.router)
app.include_router(grades.router)
app.include_router(professors.router)
app.include_router(users.router)
app.include_router(feedback.router)
app.include_router(admin_users.router)
app.include_router(admin_dashboard.router)
# admin_broadcast router removed — broadcast is now handled directly in bot/api_client.py

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint to verify API status."""
    return {"status": "ok"}