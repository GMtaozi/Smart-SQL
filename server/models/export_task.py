"""Export Task model"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from server.db.base import Base


class ExportTask(Base):
    """Export task model.

    Stores async CSV export tasks.
    """

    __tablename__ = "export_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False, index=True)
    datasource_id = Column(Integer, nullable=False, index=True)
    sql_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    total_rows = Column(Integer, nullable=True)
    csv_content = Column(Text, nullable=True)  # Complete CSV data stored after completion
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ExportTask(id={self.id}, status='{self.status}', user_id={self.user_id})>"
