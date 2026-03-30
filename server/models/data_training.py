"""Data Training model for SQL examples management"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from server.db.base import Base


class DataTraining(Base):
    """SQL training data model.

    Stores question-SQL pairs for improving SQL generation.
    """

    __tablename__ = "data_training"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    question = Column(String(500), nullable=False)  # Natural language question
    sql = Column(Text, nullable=False)  # Corresponding SQL
    datasource_id = Column(Integer, nullable=True)  # NULL means global
    description = Column(Text, nullable=True)  # Optional description
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DataTraining(id={self.id}, question='{self.question[:50]}...')>"
