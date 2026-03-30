"""Query Log model"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.orm import declarative_base
from server.db.base import Base


class QueryLog(Base):
    """Query execution log model.

    Records all SQL queries executed through the system.
    """

    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    datasource_id = Column(Integer, nullable=False, index=True)
    user_query = Column(Text, nullable=False)  # Original natural language query
    generated_sql = Column(Text, nullable=False)  # LLM generated SQL
    executed_sql = Column(Text, nullable=True)  # Actually executed SQL (with limits)
    status = Column(String(20), nullable=False, default="pending")  # pending, success, failed, rejected
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    row_count = Column(Integer, nullable=True)
    used_tables = Column(Text, nullable=True)  # JSON array of table names
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<QueryLog(id={self.id}, status='{self.status}', user_id={self.user_id})>"
