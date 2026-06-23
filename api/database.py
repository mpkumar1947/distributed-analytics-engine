import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Defensively ensure we use asyncpg even if the user copied a standard Neon connection string
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Connection settings optimized for Neon PostgreSQL free tier:
# - pool_size=3: Small pool to stay within Neon's connection limits
# - pool_timeout=15: Allows time for Neon cold start (~300-800ms)
# - pool_recycle=280: Recycle connections before Neon's 5-min auto-suspend
# - pool_pre_ping=True: Detect stale connections from Neon suspending
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=3,
    max_overflow=2,
    pool_timeout=15,
    pool_recycle=280,
    pool_pre_ping=True,
)

AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing async database sessions."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise