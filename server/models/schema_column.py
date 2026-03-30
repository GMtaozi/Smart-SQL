"""Schema Column model"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from server.db.base import Base


class SchemaColumn(Base):
    """Database column metadata model.

    Stores column information for NL2SQL context.
    """

    __tablename__ = "schema_columns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey("schema_tables.id"), nullable=False, index=True)
    column_name = Column(String(255), nullable=False)
    data_type = Column(String(50), nullable=False)
    column_comment = Column(Text, nullable=True)
    is_primary_key = Column(Integer, default=0)  # 0: no, 1: primary key
    is_nullable = Column(Integer, default=1)  # 0: not null, 1: nullable
    column_id = Column(Integer, nullable=False)  # Ordinal position in table
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    table = relationship("SchemaTable", back_populates="columns")

    def __repr__(self):
        return f"<SchemaColumn(id={self.id}, name='{self.column_name}', type='{self.data_type}')>"
