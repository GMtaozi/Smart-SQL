"""Terminology model for business terms management"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from server.db.base import Base


class Terminology(Base):
    """Business terminology model.

    Stores business term synonyms for better SQL generation.
    """

    __tablename__ = "terminologies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)  # Term name
    term_type = Column(String(50), nullable=True)  # GENERATE_SQL, ANALYSIS, etc.
    datasource_id = Column(Integer, nullable=True)  # NULL means global
    synonyms = Column(Text, nullable=True)  # Comma-separated synonyms
    description = Column(Text, nullable=True)  # Description or definition
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Terminology(id={self.id}, name='{self.name}')>"
