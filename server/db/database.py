"""PostgreSQL database connection"""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Database configuration from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sqlbot:sqlbot123@localhost:5432/sqlbot"
)

# SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Session:
    """Get a new database session. Caller must close it."""
    return SessionLocal()


def get_db():
    """Generator for FastAPI Depends - yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions (for non-FastAPI use)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    # Import all models to register them with the shared Base
    from server.models.user import User
    from server.models.datasource import Datasource
    from server.models.schema_table import SchemaTable
    from server.models.schema_column import SchemaColumn
    from server.models.query_log import QueryLog
    from server.models.query_feedback import QueryFeedback
    from server.models.ai_model import AIModel
    from server.models.terminology import Terminology
    from server.models.data_training import DataTraining
    from server.models.export_task import ExportTask
    from server.db.base import Base

    # Create all tables using the shared Base
    Base.metadata.create_all(bind=engine)
