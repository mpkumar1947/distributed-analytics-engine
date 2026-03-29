from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware 
# Local Imports
# from .celery_app import app as celery_application
from .utils.limiter import limiter, _rate_limit_exceeded_handler
from .routers import (
    search,
    grades,   
    professors
)

# Application Metadata
app = FastAPI(
    title="IITK Grade Explorer API",
    description="API backend for fetching IITK course grade distributions.",
    version="0.1.0",
)
origins = [
    "http://localhost:5173",       # For our local React development
    "http://localhost:3000",       # Just in case to use port 3000
    "http://gradiator.tech",       # our new production domain
    "https://gradiator.tech",
    "http://www.gradiator.tech",
    "https://www.gradiator.tech",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
# Rate Limiter Setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register Routers
app.include_router(search.router)
app.include_router(grades.router)
app.include_router(professors.router)

# app.include_router(admin_broadcast.router)

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint to verify API status."""
    return {"status": "ok"}