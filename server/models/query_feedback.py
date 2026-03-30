"""Query Feedback model"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from server.db.base import Base


class QueryFeedback(Base):
    """User feedback on generated SQL.

    Records user corrections and ratings for improving SQL generation.
    """

    __tablename__ = "query_feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_log_id = Column(Integer, ForeignKey("query_logs.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    is_correct = Column(Integer, nullable=False, default=1)  # 1: correct, 0: incorrect
    corrected_sql = Column(Text, nullable=True)  # User's corrected SQL if incorrect
    feedback_text = Column(Text, nullable=True)  # Optional text feedback
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<QueryFeedback(id={self.id}, query_log_id={self.query_log_id}, rating={self.rating})>"
