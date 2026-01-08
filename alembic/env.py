import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine  # sync engine for Alembic migrations
from dotenv import load_dotenv

# Add project root to path (to find api.models)
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Import your models
from api.models import Base

# Alembic Config
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    db_url_var = config.get_main_option('db_url_env_var')
    database_url = os.getenv(db_url_var)

    if not database_url:
        raise ValueError(f"Environment variable {db_url_var} not set.")

    context.configure(
        url=database_url.replace("postgresql+asyncpg", "postgresql"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    db_url_var = config.get_main_option('db_url_env_var')
    if not db_url_var:
        raise ValueError("db_url_env_var not set in alembic.ini")

    database_url = os.getenv(db_url_var)
    if not database_url:
        raise ValueError(f"Environment variable {db_url_var} not set.")

    connectable = create_engine(
        database_url.replace("postgresql+asyncpg", "postgresql"),
        pool_pre_ping=True
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
