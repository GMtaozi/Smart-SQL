"""Datasource model"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from server.db.base import Base


class Datasource(Base):
    """Database datasource configuration model.

    Stores connection info for target databases that users can query.
    """

    __tablename__ = "datasources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=True)  # Auto-filled based on db_type if not provided
    database_name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    password_encrypted = Column(String(255), nullable=False)  # Encrypted storage
    db_type = Column(String(20), nullable=False, default="pg")  # mysql, pg, oracle, etc.
    db_schema = Column(String(100), nullable=True)  # For databases that need schema (sqlserver, oracle, etc.)
    extra_params = Column(Text, nullable=True)  # Extra connection parameters
    timeout = Column(Integer, default=30)  # Connection timeout in seconds
    ssl = Column(Boolean, default=False)  # For MySQL SSL connection
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Datasource(id={self.id}, name='{self.name}', type='{self.db_type}')>"
